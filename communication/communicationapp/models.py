from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.db import router
from django.conf import settings

class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class DeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=True)

class SoftDeleteModel(models.Model):
    created_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.IntegerField(blank=True, null=True)

    objects = ActiveManager()
    deleted_objects = DeletedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, user_id=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user_id:
            self.deleted_by = user_id
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

# Existing Broadcast Models
class Broadcast(SoftDeleteModel):
    PRIORITY_CHOICES = [("Important", "Important"), ("Normal", "Normal")]
    AUDIENCE_CHOICES = [("All", "All"), ("Groups", "Groups"), ("Users", "Users")]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Normal")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    send_email = models.BooleanField(default=False)
    audience_type = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default="All")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_broadcasts_created')

    def __str__(self):
        return self.title

class BroadcastAttachment(SoftDeleteModel):
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="communications/broadcasts/")
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.broadcast.title} - {self.file_name}"

class BroadcastAcknowledgment(SoftDeleteModel):
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name="acknowledgments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_broadcast_acknowledgments')
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    viewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ['broadcast', 'user']

# Groups Models
class Group(SoftDeleteModel):
    TYPE_CHOICES = [("Public", "Public"), ("Private", "Private")]
    POSTING_PERMISSION_CHOICES = [("All", "All"), ("Owner_Only", "Owner Only")]
    
    name = models.CharField(max_length=200)
    group_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    department = models.CharField(max_length=100, blank=True, null=True)
    posting_permission = models.CharField(max_length=20, choices=POSTING_PERMISSION_CHOICES, default="All")
    allow_external_members = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_groups_created')

    def __str__(self):
        return self.name

class GroupMember(SoftDeleteModel):
    ROLE_CHOICES = [("Owner", "Owner"), ("Member", "Member")]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="Member")
    notifications_enabled = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['group', 'user']

class SurveyTemplate(SoftDeleteModel):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_survey_templates_created')

    def __str__(self):
        return self.name

class Survey(SoftDeleteModel):
    CREATION_TYPE_CHOICES = [
        ("Scratch", "From Scratch"),
        ("Template", "Use Template"),
        ("Copy", "Copy Existing")
    ]
    STATUS_CHOICES = [("Draft", "Draft"), ("Published", "Published"), ("Closed", "Closed")]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    creation_type = models.CharField(max_length=20, choices=CREATION_TYPE_CHOICES, default="Scratch")
    template = models.ForeignKey(SurveyTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
    theme = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="communications/surveys/logos/", blank=True, null=True)
    send_email_notification = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_surveys_created')

    def __str__(self):
        return self.title

class SurveyQuestion(SoftDeleteModel):
    QUESTION_TYPE_CHOICES = [
        ("Multiple_Choice", "Multiple Choice"),
        ("Checkbox", "Checkbox"),
        ("Dropdown", "Dropdown"),
        ("Star_Rating", "Star Rating"),
        ("NPS", "NPS"),
        ("Short_Text", "Short Text"),
        ("Long_Text", "Long Text"),
        ("Slider", "Slider"),
        ("File_Upload", "File Upload")
    ]
    
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(blank=True, null=True)  # For multiple choice, dropdown, etc.
    min_value = models.IntegerField(blank=True, null=True)  # For slider, rating
    max_value = models.IntegerField(blank=True, null=True)  # For slider, rating

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.survey.title} - {self.question_text[:50]}"

class SurveyResponse(SoftDeleteModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_survey_responses')
    submitted_at = models.DateTimeField(auto_now_add=True)
    time_taken = models.DurationField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['survey', 'user']

    def __str__(self):
        return f"{self.survey.title} - {self.user.username}"

class SurveyAnswer(SoftDeleteModel):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    answer_file = models.FileField(upload_to="communications/surveys/answers/", blank=True, null=True)
    answer_number = models.FloatField(blank=True, null=True)
    answer_json = models.JSONField(blank=True, null=True)  # For complex answers

    def __str__(self):
        return f"{self.response.survey.title} - Q{self.question.id}"

class ForumTag(SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#007bff")  # Hex color code
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Forum(SoftDeleteModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    tags = models.ManyToManyField(ForumTag, blank=True, related_name="forums")
    image = models.ImageField(upload_to="communications/forums/", blank=True, null=True)
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_forums_created')
    views_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class ForumComment(SoftDeleteModel):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_forum_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.forum.title} - {self.user.username} - {self.content[:50]}"

class ForumLike(SoftDeleteModel):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_forum_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['forum', 'user']

class ForumView(SoftDeleteModel):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="forum_views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_forum_views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['forum', 'user']

class EventTheme(SoftDeleteModel):
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=7)  # Hex color
    secondary_color = models.CharField(max_length=7)  # Hex color
    template_css = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Event(SoftDeleteModel):
    TYPE_CHOICES = [("Internal", "Internal"), ("External", "External")]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    venue = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="Internal")
    is_important = models.BooleanField(default=False)
    theme = models.ForeignKey(EventTheme, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_events_created')

    def __str__(self):
        return self.title

class EventAttachment(SoftDeleteModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="communications/events/")
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.title} - {self.file_name}"

class EventRSVP(models.Model):
    RSVP_CHOICES = [("Yes", "Yes"), ("No", "No"), ("Maybe", "Maybe")]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_event_rsvps')
    rsvp_status = models.CharField(max_length=10, choices=RSVP_CHOICES)
    responded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return f"{self.event.title} - {self.user.username} - {self.rsvp_status}"

class BroadcastTemplate(SoftDeleteModel):
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Broadcast.PRIORITY_CHOICES, default="Normal")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_broadcast_templates_created')

    def __str__(self):
        return self.name

class EventTemplate(SoftDeleteModel):
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=Event.TYPE_CHOICES, default="Internal")
    theme = models.ForeignKey(EventTheme, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.IntegerField(null=True)

    def __str__(self):
        return self.name

class GroupInviteTemplate(SoftDeleteModel):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comm_group_invite_templates_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class BroadcastGroup(SoftDeleteModel):
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name="shared_groups")
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

class BroadcastUser(SoftDeleteModel):
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name="shared_users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_broadcast_shared_users')

class EventGroup(SoftDeleteModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="shared_groups")
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

class EventUser(SoftDeleteModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="shared_users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comm_event_shared_users')

class ForumGroup(SoftDeleteModel):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="shared_groups")
    group = models.ForeignKey(Group, on_delete=models.CASCADE)