from django.urls import path, include
from api.views import RegisterDBAPIView

urlpatterns = [
    path('register-db/', RegisterDBAPIView.as_view(), name='register-db'),
    path('', include('api.urls')),  # 🚀 all endpoints come from api/urls.py
]
#communicationapp/urls.py