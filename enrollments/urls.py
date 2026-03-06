"""
URLs للتسجيلات
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnrollmentViewSet,
    VideoProgressViewSet,
    CourseNoteViewSet,
    CertificateViewSet,
    instructor_enrollments
)

app_name = 'enrollments'

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'progress', VideoProgressViewSet, basename='video-progress')
router.register(r'notes', CourseNoteViewSet, basename='note')
router.register(r'certificates', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('', include(router.urls)),
    path('instructor-enrollments/', instructor_enrollments, name='instructor-enrollments'),
]
