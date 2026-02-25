"""
Views للمدربين
عرض للجميع - التعديل للأدمن فقط
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Instructor
from .serializers import InstructorSerializer


class InstructorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للمدربين (Read-Only للجميع)
    """
    queryset = Instructor.objects.filter(is_active=True).select_related('user')
    serializer_class = InstructorSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """المدربون المميزون"""
        featured = self.get_queryset().filter(is_featured=True)[:6]
        serializer = InstructorSerializer(featured, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """أعلى المدربين تقييماً"""
        top = self.get_queryset().order_by('-average_rating')[:6]
        serializer = InstructorSerializer(top, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        """كورسات مدرب معين"""
        instructor = self.get_object()
        courses = instructor.user.courses.filter(is_published=True)
        
        from courses.serializers import CourseListSerializer
        serializer = CourseListSerializer(
            courses,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
