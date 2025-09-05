from django.contrib import admin
from .models import *

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_color', 'secondary_color', 'created_at']
    search_fields = ['name']

class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'group_type', 'department', 'created_by', 'created_at']
    list_filter = ['group_type', 'department', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['owners']
    inlines = [GroupMembershipInline]

class BroadcastAttachmentInline(admin.TabularInline):
    model = BroadcastAttachment
    extra = 0

@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'created_by', 'start_date', 'end_date', 'created_at']
    list_filter = ['priority', 'require_acknowledgment', 'send_email', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['target_groups', 'target_users']
    inlines = [BroadcastAttachmentInline]
    date_hierarchy = 'created_at'

@admin.register(BroadcastAcknowledgment)
class BroadcastAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = ['broadcast', 'user', 'acknowledged_at']
    list_filter = ['acknowledged_at']
    search_fields = ['broadcast__title', 'user__username']

class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 0
    ordering = ['order']

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'start_date', 'end_date', 'created_by', 'created_at']
    list_filter = ['status', 'is_anonymous', 'created_at']
    search_fields = ['title', 'description']
    inlines = [SurveyQuestionInline]
    date_hierarchy = 'created_at'

class SurveyAnswerInline(admin.TabularInline):
    model = SurveyAnswer
    extra = 0

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ['survey', 'user', 'submitted_at', 'completion_time']
    list_filter = ['submitted_at', 'survey']
    search_fields = ['survey__title', 'user__username']
    inlines = [SurveyAnswerInline]

class ForumCommentInline(admin.TabularInline):
    model = ForumComment
    extra = 0

@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'views', 'is_hidden', 'created_at']
    list_filter = ['is_hidden', 'created_at']
    search_fields = ['title', 'description', 'tags']
    inlines = [ForumCommentInline]

@admin.register(ForumComment)
class ForumCommentAdmin(admin.ModelAdmin):
    list_display = ['forum', 'user', 'content_preview', 'is_hidden', 'created_at']
    list_filter = ['is_hidden', 'created_at']
    search_fields = ['forum__title', 'user__username', 'content']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

class EventMediaInline(admin.TabularInline):
    model = EventMedia
    extra = 0

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'venue', 'event_type', 'is_important', 'created_by', 'created_at']
    list_filter = ['event_type', 'is_important', 'date', 'created_at']
    search_fields = ['title', 'description', 'venue']
    filter_horizontal = ['target_groups', 'target_users']
    inlines = [EventMediaInline]
    date_hierarchy = 'date'

@admin.register(EventRSVP)
class EventRSVPAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'response', 'responded_at']
    list_filter = ['response', 'responded_at']
    search_fields = ['event__title', 'user__username']

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'category', 'is_system_template', 'created_by', 'created_at']
    list_filter = ['template_type', 'category', 'is_system_template', 'created_at']
    search_fields = ['name', 'category']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']