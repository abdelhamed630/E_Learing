from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExamViewSet, InstructorExamViewSet

app_name = 'exams'

# instructor الأول عشان ما يتعارضش
instructor_router = DefaultRouter()
instructor_router.register(r'', InstructorExamViewSet, basename='instructor-exam')

student_router = DefaultRouter()
student_router.register(r'', ExamViewSet, basename='exam')

urlpatterns = [
    path('instructor/', include(instructor_router.urls)),
    path('', include(student_router.urls)),
]
