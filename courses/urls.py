"""
URLs للكورسات
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, CourseViewSet, VideoViewSet, InstructorCourseViewSet, InstructorContentViewSet

app_name = 'courses'

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'videos', VideoViewSet, basename='video')
router.register(r'instructor-courses', InstructorCourseViewSet, basename='instructor-course')
router.register(r'instructor-content', InstructorContentViewSet, basename='instructor-content')

urlpatterns = [
    path('', include(router.urls)),
]
