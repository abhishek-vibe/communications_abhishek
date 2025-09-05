from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Theme(BaseModel):
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=7, default='#007bff')
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    background_color = models.CharField(max_length=7, default='#ffffff')
    logo = models.ImageField(upload_to='themes/', null=True, blank=True)
    
    def __str__(self):
        return self.name

class Group(BaseModel):
    GROUP_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    group_type = models.CharField(max_length=10, choices=GROUP_TYPES, default='public')
    department = models.CharField(max_length=100, blank=True)
    members = models.ManyToManyField(User, through='GroupMembership')
    owners = models.ManyToManyField(User, related_name='owned_groups', blank=True)
    can_all_post = models.BooleanField(default=True)
    can_external_members = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    
    def __str__(self):
        return self.name

class GroupMembership(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    can_post = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'group']

class Broadcast(BaseModel):
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('important', 'Important'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    require_acknowledgment = models.BooleanField(default=False)
    send_email = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    target_all = models.BooleanField(default=True)
    target_groups = models.ManyToManyField(Group, blank=True)
    target_users = models.ManyToManyField(User, related_name='targeted_broadcasts', blank=True)
    
    def __str__(self):
        return self.title

class BroadcastAttachment(BaseModel):
    broadcast = models.ForeignKey(Broadcast, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='broadcasts/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    
    def __str__(self):
        return self.filename

class BroadcastAcknowledgment(BaseModel):
    broadcast = models.ForeignKey(Broadcast, related_name='acknowledgments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['broadcast', 'user']

class Survey(BaseModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    theme = models.ForeignKey(Theme, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_anonymous = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class SurveyQuestion(BaseModel):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('checkbox', 'Checkbox'),
        ('dropdown', 'Dropdown'),
        ('star_rating', 'Star Rating'),
        ('nps', 'NPS'),
        ('short_text', 'Short Text'),
        ('long_text', 'Long Text'),
        ('slider', 'Slider'),
        ('file_upload', 'File Upload'),
    ]
    
    survey = models.ForeignKey(Survey, related_name='questions', on_delete=models.CASCADE)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    is_required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    options = models.JSONField(default=list, blank=True)  # For multiple choice, dropdown, etc.
    min_value = models.IntegerField(null=True, blank=True)  # For slider, rating
    max_value = models.IntegerField(null=True, blank=True)  # For slider, rating
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.survey.title} - Q{self.order}"

class SurveyResponse(BaseModel):
    survey = models.ForeignKey(Survey, related_name='responses', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # null for anonymous
    submitted_at = models.DateTimeField(auto_now_add=True)
    completion_time = models.DurationField(null=True, blank=True)
    
    class Meta:
        unique_together = ['survey', 'user']

class SurveyAnswer(BaseModel):
    response = models.ForeignKey(SurveyResponse, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    answer_number = models.FloatField(null=True, blank=True)
    answer_file = models.FileField(upload_to='survey_files/', null=True, blank=True)
    selected_options = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Answer for {self.question}"

class Forum(BaseModel):
    title = models.CharField(max_length=300)
    description = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    image = models.ImageField(upload_to='forums/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.title

class ForumComment(BaseModel):
    forum = models.ForeignKey(Forum, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.forum.title}"

class ForumLike(BaseModel):
    forum = models.ForeignKey(Forum, related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['forum', 'user']

class Event(BaseModel):
    EVENT_TYPES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]
    
    RSVP_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe'),
    ]
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    date = models.DateTimeField()
    venue = models.CharField(max_length=300)
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES, default='internal')
    is_important = models.BooleanField(default=False)
    theme = models.ForeignKey(Theme, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    target_all = models.BooleanField(default=True)
    target_groups = models.ManyToManyField(Group, blank=True)
    target_users = models.ManyToManyField(User, related_name='targeted_events', blank=True)
    
    def __str__(self):
        return self.title

class EventMedia(BaseModel):
    event = models.ForeignKey(Event, related_name='media', on_delete=models.CASCADE)
    file = models.FileField(upload_to='events/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    
    def __str__(self):
        return self.filename

class EventRSVP(BaseModel):
    event = models.ForeignKey(Event, related_name='rsvps', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    response = models.CharField(max_length=10, choices=Event.RSVP_CHOICES)
    responded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['event', 'user']

class Template(BaseModel):
    TEMPLATE_TYPES = [
        ('survey', 'Survey'),
        ('broadcast', 'Broadcast'),
        ('event', 'Event'),
        ('group_invitation', 'Group Invitation'),
    ]
    
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    content = models.JSONField()  # Store template structure
    category = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_system_template = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"

class Notification(BaseModel):
    NOTIFICATION_TYPES = [
        ('broadcast', 'Broadcast'),
        ('survey', 'Survey'),
        ('event', 'Event'),
        ('forum', 'Forum'),
        ('group', 'Group'),
    ]
    
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    related_object_id = models.UUIDField(null=True, blank=True)
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
#API/MODELS.PY