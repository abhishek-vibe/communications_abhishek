from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *
from django.db import transaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    owners = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = '__all__'
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class BroadcastAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BroadcastAttachment
        fields = '__all__'

class BroadcastSerializer(serializers.ModelSerializer):
    attachments = BroadcastAttachmentSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    target_groups = GroupSerializer(many=True, read_only=True)
    target_users = UserSerializer(many=True, read_only=True)
    acknowledgment_count = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Broadcast
        fields = '__all__'
    
    def get_acknowledgment_count(self, obj):
        return obj.acknowledgments.count()
    
    def get_view_count(self, obj):
        # This would require tracking views - implement based on your needs
        return 0
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class BroadcastAcknowledgmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = BroadcastAcknowledgment
        fields = '__all__'

class SurveyQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestion
        fields = '__all__'

class SurveySerializer(serializers.ModelSerializer):
    questions = SurveyQuestionSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    response_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    theme = ThemeSerializer(read_only=True)
    
    class Meta:
        model = Survey
        fields = '__all__'
    
    def get_response_count(self, obj):
        return obj.responses.count()
    
    def get_completion_rate(self, obj):
        total_responses = obj.responses.count()
        if total_responses == 0:
            return 0
        # Calculate completion rate based on your logic
        return 100  # Placeholder
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class SurveyAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAnswer
        fields = '__all__'

class SurveyResponseSerializer(serializers.ModelSerializer):
    answers = SurveyAnswerSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = SurveyResponse
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ForumCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ForumComment
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ForumSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    comments = ForumCommentSerializer(many=True, read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Forum
        fields = '__all__'
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_comment_count(self, obj):
        return obj.comments.count()
    
    def get_is_liked(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.likes.filter(user=user).exists()
        return False
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class EventMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    media = EventMediaSerializer(many=True, read_only=True)
    target_groups = GroupSerializer(many=True, read_only=True)
    target_users = UserSerializer(many=True, read_only=True)
    theme = ThemeSerializer(read_only=True)
    rsvp_summary = serializers.SerializerMethodField()
    user_rsvp = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = '__all__'
    
    def get_rsvp_summary(self, obj):
        rsvps = obj.rsvps.all()
        summary = {'yes': 0, 'no': 0, 'maybe': 0}
        for rsvp in rsvps:
            summary[rsvp.response] += 1
        return summary
    
    def get_user_rsvp(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            rsvp = obj.rsvps.filter(user=user).first()
            return rsvp.response if rsvp else None
        return None
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class EventRSVPSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = EventRSVP
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class TemplateSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Template
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

# Specialized serializers for analytics
class BroadcastAnalyticsSerializer(serializers.ModelSerializer):
    acknowledgment_rate = serializers.SerializerMethodField()
    total_recipients = serializers.SerializerMethodField()
    acknowledgments = BroadcastAcknowledgmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Broadcast
        fields = '__all__'
    
    def get_acknowledgment_rate(self, obj):
        total = self.get_total_recipients(obj)
        if total == 0:
            return 0
        return (obj.acknowledgments.count() / total) * 100
    
    def get_total_recipients(self, obj):
        if obj.target_all:
            return User.objects.count()
        return obj.target_users.count() + sum([group.members.count() for group in obj.target_groups.all()])

class SurveyAnalyticsSerializer(serializers.ModelSerializer):
    questions = SurveyQuestionSerializer(many=True, read_only=True)
    responses = SurveyResponseSerializer(many=True, read_only=True)
    completion_rate = serializers.SerializerMethodField()
    average_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Survey
        fields = '__all__'
    
    def get_completion_rate(self, obj):
        # Implement completion rate logic
        return 85  # Placeholder
    
    def get_average_time(self, obj):
        responses = obj.responses.filter(completion_time__isnull=False)
        if responses.exists():
            total_time = sum([r.completion_time.total_seconds() for r in responses], 0)
            return total_time / responses.count()
        return 0
    
class UserDatabaseSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()  # Changed to IntegerField to match your model
    username = serializers.CharField(max_length=150, required=False)
    db_name = serializers.CharField(max_length=100)
    db_user = serializers.CharField(max_length=100)
    db_password = serializers.CharField(max_length=100)  # Match your model's max_length
    db_host = serializers.CharField(max_length=100, default="localhost")
    db_port = serializers.CharField(max_length=10, default="5432")  # CharField to match your model
    db_type = serializers.ChoiceField(
        choices=[
            ("self_hosted", "Self Hosted"),
            ("client_hosted", "Client Hosted"),
        ],
        default="self_hosted"
    )
    
    def validate_db_port(self, value):
        try:
            port_int = int(value)
            if not (1 <= port_int <= 65535):
                raise serializers.ValidationError("Port must be between 1 and 65535")
        except ValueError:
            raise serializers.ValidationError("Port must be a valid number")
        return value