#api/views.py

import socket
import logging
from io import StringIO
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.db import connections, models
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination

from config.models import UserDatabase

from .utils import decrypt_password, test_db_connection, add_db_alias

from .models import (
    Broadcast,
    BroadcastAttachment,
    BroadcastAcknowledgment,
    Group,
    GroupMembership,
    Survey,
    SurveyQuestion,
    SurveyResponse,
    SurveyAnswer,
    Forum,
    ForumLike,
    ForumComment,
    Event,
    EventMedia,
    EventRSVP,
    Template,
    Theme,
    Notification,
)

from .serializers import (
    UserSerializer,
    BroadcastSerializer,
    BroadcastAttachmentSerializer,
    BroadcastAnalyticsSerializer,
    GroupSerializer,
    UserDatabaseSerializer,
    SurveySerializer,
    SurveyAnalyticsSerializer,
    ForumSerializer,
    ForumCommentSerializer,
    EventSerializer,
    EventRSVPSerializer,
    TemplateSerializer,
    ThemeSerializer,
    NotificationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def debug_database_config(db_alias):
    """Debug function to check database configuration before migration"""
    print(f"\n=== DEBUG: Database Configuration for {db_alias} ===")
    
    # Check if database exists in DATABASES
    if db_alias in settings.DATABASES:
        db_config = settings.DATABASES[db_alias]
        print(f"Database config found: {db_config}")
        
        # Check specifically for CONN_HEALTH_CHECKS
        if 'CONN_HEALTH_CHECKS' in db_config:
            print(f"CONN_HEALTH_CHECKS: {db_config['CONN_HEALTH_CHECKS']}")
        else:
            print("ERROR: CONN_HEALTH_CHECKS key is missing!")
            
        # Check other critical keys
        critical_keys = ['ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT', 'TIME_ZONE', 'CONN_MAX_AGE']
        for key in critical_keys:
            if key in db_config:
                print(f"{key}: {db_config[key]}")
            else:
                print(f"WARNING: {key} is missing!")
    else:
        print(f"ERROR: Database {db_alias} not found in settings.DATABASES")
        print(f"Available databases: {list(settings.DATABASES.keys())}")
    
    # Check connection object
    try:
        connection = connections[db_alias]
        print(f"Connection object: {connection}")
        print(f"Connection settings_dict: {connection.settings_dict}")
    except Exception as e:
        print(f"Error accessing connection: {e}")
    
    print("=== END DEBUG ===\n")

# Replace your existing RegisterDBAPIView class with this one
class RegisterDBAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        logger.info("RegisterDBAPIView called")
        logger.debug("Incoming payload keys: %s", list(request.data.keys()))

        ser = UserDatabaseSerializer(data=request.data)
        if not ser.is_valid():
            logger.warning("Serializer invalid: %s", ser.errors)
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        d = ser.validated_data
        user_id = d['user_id']
        username = d.get('username')
        db_alias = f"client_{user_id}"

        logger.info("Validated for user_id=%s, username=%s, alias=%s",
                    user_id, username, db_alias)
        logger.debug("DB target: %s@%s:%s/%s (type=%s)",
                     d['db_user'], d['db_host'], d['db_port'], d['db_name'], d.get('db_type'))

        # Already registered?
        if UserDatabase.objects.filter(user_id=user_id).exists():
            logger.warning("DB entry already exists for user_id=%s", user_id)
            return Response(
                {'detail': f"DB entry already exists for user_id {user_id}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Host resolvable?
        try:
            ip = socket.gethostbyname(d['db_host'])
            logger.debug("Resolved host %s -> %s", d['db_host'], ip)
        except socket.error:
            logger.error("Host not resolvable: %s", d['db_host'])
            return Response({'detail': f"Host '{d['db_host']}' is not resolvable."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Decrypt password
        try:
            real_pw = decrypt_password(d['db_password'])
        except Exception as e:
            logger.exception("Password decryption failed")
            return Response({'detail': f"Failed to decrypt password: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Live connection test
        ok, err = test_db_connection(
            name=d['db_name'], user=d['db_user'], password=real_pw, host=d['db_host'], port=d['db_port']
        )
        if not ok:
            logger.error("Connection test failed: %s", err)
            return Response({'detail': f'Connect failed: {err}'}, status=status.HTTP_400_BAD_REQUEST)

        if db_alias in settings.DATABASES:
            logger.warning("DB alias already in settings: %s", db_alias)
            return Response({'detail': f"DB alias '{db_alias}' already exists in settings."},
                            status=status.HTTP_400_BAD_REQUEST)

        entry = UserDatabase.objects.create(
            user_id=user_id,
            username=username,
            db_name=d['db_name'],
            db_user=d['db_user'],
            db_password=d['db_password'],  # encrypted
            db_host=d['db_host'],
            db_port=d['db_port'],
            db_type=d.get('db_type') or 'self_hosted'
        )
        logger.info("UserDatabase row created id=%s", entry.id)

        try:
            # Register runtime DB alias
            add_db_alias(
                alias=db_alias,
                db_name=d['db_name'],
                db_user=d['db_user'],
                db_password=real_pw,
                db_host=d['db_host'],
                db_port=d['db_port'],
            )

            logger.info("Running migrations for app='api' on database='%s'", db_alias)
            out = StringIO()
            call_command('migrate', 'api', database=db_alias, interactive=False, verbosity=1, stdout=out)
            logger.info("Migrate output:\n%s", out.getvalue())

            try:
                out2 = StringIO()
                call_command('showmigrations', 'api', database=db_alias, stdout=out2, verbosity=1)
                logger.debug("Showmigrations:\n%s", out2.getvalue())
            except Exception:
                logger.debug("showmigrations failed (non-fatal)", exc_info=True)

        except Exception as e:
            logger.exception("Migration or alias setup failed for alias=%s", db_alias)
            # cleanup
            entry.delete()
            settings.DATABASES.pop(db_alias, None)
            try:
                connections.databases.pop(db_alias, None)
            except Exception:
                pass
            return Response({'detail': f"Migration failed: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                connections[db_alias].close()
                logger.debug("Closed connection for alias %s", db_alias)
            except Exception:
                logger.debug("No connection to close for alias %s", db_alias)

        logger.info("DB registered and API tables migrated for alias=%s", db_alias)
        return Response(
            {'detail': 'DB registered and API tables migrated.', 'alias': db_alias},
            status=status.HTTP_201_CREATED
        )

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BroadcastViewSet(viewsets.ModelViewSet):
    queryset = Broadcast.objects.all().order_by("-created_at")
    serializer_class = BroadcastSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        queryset = Broadcast.objects.all()

        # Filter broadcasts visible to user
        if not getattr(user, "is_staff", False):
            now = timezone.now()
            queryset = (
                queryset.filter(
                    Q(target_all=True)
                    | Q(target_users=user)
                    | Q(target_groups__members=user),
                    start_date__lte=now,
                    end_date__gte=now,
                )
                .distinct()
            )

        # Filter by priority
        priority = self.request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        broadcast = self.get_object()
        acknowledgment, created = BroadcastAcknowledgment.objects.get_or_create(
            broadcast=broadcast, user=request.user
        )
        return Response(
            {
                "acknowledged": True,
                "created": created,
                "acknowledged_at": acknowledgment.acknowledged_at,
            }
        )

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        broadcast = self.get_object()
        serializer = BroadcastAnalyticsSerializer(broadcast, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def upload_attachments(self, request):
        files = request.FILES.getlist("files")
        broadcast_id = request.data.get("broadcast_id")

        try:
            broadcast = Broadcast.objects.get(id=broadcast_id)
            attachments = []

            for file in files:
                attachment = BroadcastAttachment.objects.create(
                    broadcast=broadcast,
                    file=file,
                    filename=file.name,
                    file_type=file.content_type,
                )
                attachments.append(BroadcastAttachmentSerializer(attachment).data)

            return Response({"attachments": attachments})
        except Broadcast.DoesNotExist:
            return Response({"error": "Broadcast not found"}, status=404)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("-created_at")
    serializer_class = GroupSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Group.objects.all()

        if not getattr(user, "is_staff", False):
            queryset = (
                queryset.filter(
                    Q(group_type="public") | Q(members=user) | Q(created_by=user)
                )
                .distinct()
            )

        # Filter by department
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department__icontains=department)

        return queryset

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        group = self.get_object()
        membership, created = GroupMembership.objects.get_or_create(
            user=request.user, group=group
        )
        return Response({"joined": True, "created": created, "membership_id": membership.id})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        group = self.get_object()
        try:
            membership = GroupMembership.objects.get(user=request.user, group=group)
            membership.delete()
            return Response({"left": True})
        except GroupMembership.DoesNotExist:
            return Response({"error": "Not a member"}, status=400)

    @action(detail=True, methods=["post"])
    def add_members(self, request, pk=None):
        group = self.get_object()
        user_ids = request.data.get("user_ids", [])

        # Check if user is owner or admin
        if not (request.user in group.owners.all() or getattr(request.user, "is_staff", False)):
            return Response({"error": "Permission denied"}, status=403)

        added_members = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                membership, created = GroupMembership.objects.get_or_create(
                    user=user, group=group
                )
                if created:
                    added_members.append(UserSerializer(user).data)
            except User.DoesNotExist:
                continue

        return Response({"added_members": added_members})


class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all().order_by("-created_at")
    serializer_class = SurveySerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Survey.objects.all()

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter active surveys
        if self.request.query_params.get("active_only"):
            now = timezone.now()
            queryset = queryset.filter(
                status="active", start_date__lte=now, end_date__gte=now
            )

        return queryset

    @action(detail=True, methods=["post"])
    def submit_response(self, request, pk=None):
        survey = self.get_object()
        answers_data = request.data.get("answers", [])

        # Check if survey is active
        now = timezone.now()
        if survey.status != "active" or survey.start_date > now or survey.end_date < now:
            return Response({"error": "Survey is not active"}, status=400)

        # Check if user already responded
        if not survey.is_anonymous and SurveyResponse.objects.filter(
            survey=survey, user=request.user
        ).exists():
            return Response({"error": "Already responded"}, status=400)

        # Create response
        response_obj = SurveyResponse.objects.create(
            survey=survey, user=request.user if not survey.is_anonymous else None
        )

        # Create answers
        for answer_data in answers_data:
            question_id = answer_data.get("question_id")
            try:
                question = SurveyQuestion.objects.get(id=question_id, survey=survey)
                SurveyAnswer.objects.create(
                    response=response_obj,
                    question=question,
                    answer_text=answer_data.get("answer_text", ""),
                    answer_number=answer_data.get("answer_number"),
                    selected_options=answer_data.get("selected_options", []),
                )
            except SurveyQuestion.DoesNotExist:
                continue

        return Response({"success": True, "response_id": response_obj.id})

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        survey = self.get_object()
        serializer = SurveyAnalyticsSerializer(survey, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def copy_survey(self, request):
        source_survey_id = request.data.get("source_survey_id")
        new_title = request.data.get("title", "Copy of Survey")

        try:
            source_survey = Survey.objects.get(id=source_survey_id)
            new_survey = Survey.objects.create(
                title=new_title,
                description=source_survey.description,
                created_by=request.user,
                theme=source_survey.theme,
            )

            # Copy questions
            for question in source_survey.questions.all():
                SurveyQuestion.objects.create(
                    survey=new_survey,
                    question_text=question.question_text,
                    question_type=question.question_type,
                    is_required=question.is_required,
                    order=question.order,
                    options=question.options,
                    min_value=question.min_value,
                    max_value=question.max_value,
                )

            serializer = SurveySerializer(new_survey, context={"request": request})
            return Response(serializer.data)

        except Survey.DoesNotExist:
            return Response({"error": "Source survey not found"}, status=404)


class ForumViewSet(viewsets.ModelViewSet):
    queryset = Forum.objects.filter(is_hidden=False).order_by("-created_at")
    serializer_class = ForumSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Forum.objects.filter(is_hidden=False)

        # Filter by tags
        tags = self.request.query_params.get("tags")
        if tags:
            tag_list = tags.split(",")
            queryset = queryset.filter(tags__overlap=tag_list)

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset.order_by("-created_at")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        Forum.objects.filter(id=instance.id).update(views=models.F("views") + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        forum = self.get_object()
        like, created = ForumLike.objects.get_or_create(forum=forum, user=request.user)

        if not created:
            like.delete()
            return Response({"liked": False})

        return Response({"liked": True})

    @action(detail=True, methods=["post"])
    def add_comment(self, request, pk=None):
        forum = self.get_object()
        content = request.data.get("content")
        parent_id = request.data.get("parent_id")

        parent = None
        if parent_id:
            try:
                parent = ForumComment.objects.get(id=parent_id, forum=forum)
            except ForumComment.DoesNotExist:
                return Response({"error": "Parent comment not found"}, status=404)

        comment = ForumComment.objects.create(
            forum=forum, user=request.user, content=content, parent=parent
        )

        serializer = ForumCommentSerializer(comment, context={"request": request})
        return Response(serializer.data)


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by("-date")
    serializer_class = EventSerializer
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        queryset = Event.objects.all()

        # Filter events visible to user
        if not getattr(user, "is_staff", False):
            queryset = (
                queryset.filter(
                    Q(target_all=True)
                    | Q(target_users=user)
                    | Q(target_groups__members=user)
                )
                .distinct()
            )

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # Filter by event type
        event_type = self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        return queryset

    @action(detail=True, methods=["post"])
    def rsvp(self, request, pk=None):
        event = self.get_object()
        response = request.data.get("response")  # yes, no, maybe
        if response not in ["yes", "no", "maybe"]:
            return Response({"error": "Invalid response"}, status=400)

        rsvp, created = EventRSVP.objects.update_or_create(
            event=event, user=request.user, defaults={"response": response}
        )

        return Response({"rsvp": response, "created": created})

    @action(detail=True, methods=["get"])
    def rsvp_list(self, request, pk=None):
        event = self.get_object()

        # Check if user is event creator or admin
        if event.created_by != request.user and not getattr(request.user, "is_staff", False):
            return Response({"error": "Permission denied"}, status=403)

        rsvps = event.rsvps.all()
        serializer = EventRSVPSerializer(rsvps, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def upload_media(self, request):
        files = request.FILES.getlist("files")
        event_id = request.data.get("event_id")

        try:
            event = Event.objects.get(id=event_id)
            media_files = []

            for file in files:
                media = EventMedia.objects.create(
                    event=event,
                    file=file,
                    filename=file.name,
                    file_type=file.content_type,
                )
                media_files.append(EventMediaSerializer(media).data)

            return Response({"media": media_files})
        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=404)


class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all().order_by("-created_at")
    serializer_class = TemplateSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Template.objects.all()

        # Filter by template type
        template_type = self.request.query_params.get("template_type")
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__icontains=category)

        return queryset


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"marked_read": True})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"marked_read_count": count})


class ThemeViewSet(viewsets.ModelViewSet):
    queryset = Theme.objects.all().order_by("-created_at")
    serializer_class = ThemeSerializer


# Analytics Views
class AnalyticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Get overall analytics dashboard data"""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        data = {
            "total_broadcasts": Broadcast.objects.count(),
            "active_surveys": Survey.objects.filter(status="active").count(),
            "total_events": Event.objects.filter(date__gte=now).count(),
            "total_groups": Group.objects.count(),
            "recent_activity": {
                "broadcasts": Broadcast.objects.filter(created_at__gte=last_30_days).count(),
                "surveys": Survey.objects.filter(created_at__gte=last_30_days).count(),
                "events": Event.objects.filter(created_at__gte=last_30_days).count(),
                "forums": Forum.objects.filter(created_at__gte=last_30_days).count(),
            },
        }

        return Response(data)

    @action(detail=False, methods=["get"])
    def engagement(self, request):
        """Get engagement analytics"""
        last_30_days = timezone.now() - timedelta(days=30)

        data = {
            "forum_engagement": Forum.objects.filter(created_at__gte=last_30_days).aggregate(
                total_views=models.Sum("views"),
                total_likes=Count("likes"),
                total_comments=Count("comments"),
            ),
            "survey_responses": SurveyResponse.objects.filter(
                submitted_at__gte=last_30_days
            ).count(),
            "broadcast_acknowledgments": BroadcastAcknowledgment.objects.filter(
                acknowledged_at__gte=last_30_days
            ).count(),
            "event_rsvps": EventRSVP.objects.filter(
                responded_at__gte=last_30_days
            ).count(),
        }

        return Response(data)