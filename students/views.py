"""
Views لتطبيق الطلاب
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import Student
from .serializers import (
    StudentSerializer, 
    StudentCreateSerializer, 
    StudentUpdateSerializer
)
from .permissions import IsStudent, IsStudentOwner, IsActiveStudent


class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet للطلاب
    - الطالب يمكنه مشاهدة وتعديل بياناته الشخصية فقط
    """
    queryset = Student.objects.select_related('user').all()
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StudentUpdateSerializer
        return StudentSerializer
    
    def get_queryset(self):
        """كل طالب يرى بياناته فقط"""
        if self.request.user.is_staff:
            return Student.objects.select_related('user').all()
        return Student.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'], 
            permission_classes=[IsAuthenticated, IsStudent])
    def me(self, request):
        """
        GET: عرض بيانات الطالب الحالي
        PUT/PATCH: تحديث بيانات الطالب الحالي
        """
        student = request.user.student_profile
        
        if request.method == 'GET':
            # استخدام Cache
            cache_key = f'student_profile_{student.id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data)
            
            serializer = StudentSerializer(student)
            cache.set(cache_key, serializer.data, 300)  # 5 دقائق
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            serializer = StudentUpdateSerializer(
                student, 
                data=request.data, 
                partial=(request.method == 'PATCH')
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # مسح الـ Cache
            cache_key = f'student_profile_{student.id}'
            cache.delete(cache_key)
            
            return Response(
                StudentSerializer(student).data,
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'], 
            permission_classes=[IsAuthenticated, IsStudent])
    def dashboard(self, request):
        """
        Dashboard للطالب - إحصائيات سريعة
        """
        student = request.user.student_profile
        
        # يمكن إضافة إحصائيات من الـ apps الأخرى
        data = {
            'student': StudentSerializer(student).data,
            'stats': {
                'total_enrollments': 0,  # من enrollments app
                'completed_courses': 0,   # من courses app
                'exams_taken': 0,         # من exams app
            }
        }
        
        return Response(data)


class StudentPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet عام للطلاب (للمدرسين/الإداريين)
    """
    queryset = Student.objects.select_related('user').filter(is_active=True)
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فلترة حسب الـ query params
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                user__username__icontains=search
            ) | queryset.filter(
                user__email__icontains=search
            ) | queryset.filter(
                user__first_name__icontains=search
            ) | queryset.filter(
                user__last_name__icontains=search
            )
        
        return queryset
