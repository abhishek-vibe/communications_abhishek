# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'broadcasts', views.BroadcastViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'surveys', views.SurveyViewSet)
router.register(r'forums', views.ForumViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'templates', views.TemplateViewSet)
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'themes', views.ThemeViewSet)
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
    
    # ✅ ADD THIS LINE - Register Database endpoint
    path('register-db/', views.RegisterDBAPIView.as_view(), name='register-db'),
    
    # Additional custom endpoints
    path('broadcasts/<uuid:pk>/acknowledge/',
         views.BroadcastViewSet.as_view({'post': 'acknowledge'}),
         name='broadcast-acknowledge'),
    
    path('broadcasts/<uuid:pk>/analytics/',
         views.BroadcastViewSet.as_view({'get': 'analytics'}),
         name='broadcast-analytics'),
    
    path('broadcasts/upload-attachments/',
         views.BroadcastViewSet.as_view({'post': 'upload_attachments'}),
         name='broadcast-upload-attachments'),
    
    path('groups/<uuid:pk>/join/',
         views.GroupViewSet.as_view({'post': 'join'}),
         name='group-join'),
    
    path('groups/<uuid:pk>/leave/',
         views.GroupViewSet.as_view({'post': 'leave'}),
         name='group-leave'),
    
    path('groups/<uuid:pk>/add-members/',
         views.GroupViewSet.as_view({'post': 'add_members'}),
         name='group-add-members'),
    
    path('surveys/<uuid:pk>/submit-response/',
         views.SurveyViewSet.as_view({'post': 'submit_response'}),
         name='survey-submit-response'),
    
    path('surveys/<uuid:pk>/analytics/',
         views.SurveyViewSet.as_view({'get': 'analytics'}),
         name='survey-analytics'),
    
    path('surveys/copy-survey/',
         views.SurveyViewSet.as_view({'post': 'copy_survey'}),
         name='survey-copy'),
    
    path('forums/<uuid:pk>/like/',
         views.ForumViewSet.as_view({'post': 'like'}),
         name='forum-like'),
    
    path('forums/<uuid:pk>/add-comment/',
         views.ForumViewSet.as_view({'post': 'add_comment'}),
         name='forum-add-comment'),
    
    path('events/<uuid:pk>/rsvp/',
         views.EventViewSet.as_view({'post': 'rsvp'}),
         name='event-rsvp'),
    
    path('events/<uuid:pk>/rsvp-list/',
         views.EventViewSet.as_view({'get': 'rsvp_list'}),
         name='event-rsvp-list'),
    
    path('events/upload-media/',
         views.EventViewSet.as_view({'post': 'upload_media'}),
         name='event-upload-media'),
    
    path('notifications/<uuid:pk>/mark-read/',
         views.NotificationViewSet.as_view({'post': 'mark_read'}),
         name='notification-mark-read'),
    
    path('notifications/mark-all-read/',
         views.NotificationViewSet.as_view({'post': 'mark_all_read'}),
         name='notification-mark-all-read'),
    
    path('analytics/dashboard/',
         views.AnalyticsViewSet.as_view({'get': 'dashboard'}),
         name='analytics-dashboard'),
    
    path('analytics/engagement/',
         views.AnalyticsViewSet.as_view({'get': 'engagement'}),
         name='analytics-engagement'),
]