"""
URLs للمدربين
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InstructorViewSet

app_name = 'instructors'

router = DefaultRouter()
router.register(r'', InstructorViewSet, basename='instructor')

urlpatterns = [
    path('', include(router.urls)),
]
