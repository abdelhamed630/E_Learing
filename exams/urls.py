"""
URLs للامتحانات
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExamViewSet, InstructorExamViewSet

app_name = 'exams'

router = DefaultRouter()
router.register(r'', ExamViewSet, basename='exam')
router.register(r'instructor', InstructorExamViewSet, basename='instructor-exam')

urlpatterns = [
    path('', include(router.urls)),
]
