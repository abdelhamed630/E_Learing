"""
URLs لتطبيق الطلاب
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentPublicViewSet

app_name = 'student'

router = DefaultRouter()
router.register(r'', StudentViewSet, basename='student')
router.register(r'public', StudentPublicViewSet, basename='student-public')

urlpatterns = [
    path('', include(router.urls)),
]
