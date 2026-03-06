"""
Views للتسجيلات
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from students.permissions import IsStudent
from courses.models import Course, Video
from .models import Enrollment, VideoProgress, CourseNote, Certificate, LearningStreak
from .serializers import (
    EnrollmentSerializer, EnrollmentDetailSerializer,
    VideoProgressSerializer, UpdateVideoProgressSerializer,
    CourseNoteSerializer, CreateCourseNoteSerializer,
    CertificateSerializer, LearningStreakSerializer,
    EnrollmentStatsSerializer
)
from .tasks import (
    calculate_enrollment_progress,
    generate_certificate,
    update_learning_streak
)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet للتسجيلات
    - الطالب يشوف تسجيلاته فقط
    """
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EnrollmentDetailSerializer
        return EnrollmentSerializer
    
    def get_queryset(self):
        """الطالب يشوف تسجيلاته فقط"""
        student = self.request.user.student_profile
        return Enrollment.objects.filter(student=student).select_related(
            'course', 'course__instructor', 'course__category'
        )
    
    @action(detail=False, methods=['post'])
    def enroll(self, request):
        """التسجيل في كورس جديد"""
        course_id = request.data.get('course_id')
        
        if not course_id:
            return Response(
                {'error': 'يجب تحديد الكورس'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {'error': 'الكورس غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        student = request.user.student_profile
        
        # التحقق من التسجيل السابق - لو مسجل يرجع success
        existing = Enrollment.objects.filter(student=student, course=course).first()
        if existing:
            return Response({
                'message': 'أنت مسجل بالفعل في هذا الكورس',
                'enrollment': EnrollmentSerializer(existing).data,
                'already_enrolled': True
            }, status=status.HTTP_200_OK)
        
        # إنشاء التسجيل
        enrollment = Enrollment.objects.create(
            student=student,
            course=course,
            status='active'
        )
        
        serializer = EnrollmentSerializer(enrollment)
        return Response({
            'message': 'تم التسجيل في الكورس بنجاح',
            'enrollment': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """بدء الكورس"""
        enrollment = self.get_object()
        enrollment.mark_as_started()
        
        return Response({
            'message': 'تم بدء الكورس بنجاح',
            'started_at': enrollment.started_at
        })
    
    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        """الانسحاب من الكورس"""
        enrollment = self.get_object()
        
        if enrollment.status == 'completed':
            return Response(
                {'error': 'لا يمكن الانسحاب من كورس مكتمل'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollment.status = 'dropped'
        enrollment.save()
        
        return Response({
            'message': 'تم الانسحاب من الكورس'
        })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """الكورسات النشطة"""
        student = request.user.student_profile
        enrollments = Enrollment.objects.filter(
            student=student,
            status='active'
        ).select_related('course')
        
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """الكورسات المكتملة"""
        student = request.user.student_profile
        enrollments = Enrollment.objects.filter(
            student=student,
            status='completed'
        ).select_related('course')
        
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات التسجيلات"""
        student = request.user.student_profile
        
        enrollments = Enrollment.objects.filter(student=student)
        
        stats = {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='active').count(),
            'completed_enrollments': enrollments.filter(status='completed').count(),
            'average_progress': enrollments.aggregate(Avg('progress'))['progress__avg'] or 0,
            'total_time_spent': enrollments.aggregate(Sum('total_time_spent'))['total_time_spent__sum'] or 0,
            'certificates_earned': Certificate.objects.filter(
                enrollment__student=student
            ).count(),
            'current_streak': self._get_current_streak(student),
            'longest_streak': self._get_longest_streak(student),
        }
        
        serializer = EnrollmentStatsSerializer(stats)
        return Response(serializer.data)
    
    def _get_current_streak(self, student):
        """حساب السلسلة الحالية"""
        today = timezone.now().date()
        streak = 0
        
        while True:
            date = today - timedelta(days=streak)
            if LearningStreak.objects.filter(student=student, date=date).exists():
                streak += 1
            else:
                break
        
        return streak
    
    def _get_longest_streak(self, student):
        """حساب أطول سلسلة"""
        streaks = LearningStreak.objects.filter(student=student).order_by('date')
        
        if not streaks.exists():
            return 0
        
        max_streak = 0
        current_streak = 1
        prev_date = streaks.first().date
        
        for streak in streaks[1:]:
            if (streak.date - prev_date).days == 1:
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 1
            prev_date = streak.date
        
        return max(max_streak, current_streak)


class VideoProgressViewSet(viewsets.ModelViewSet):
    """ViewSet لتقدم الفيديوهات"""
    serializer_class = VideoProgressSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_queryset(self):
        student = self.request.user.student_profile
        return VideoProgress.objects.filter(student=student).select_related('video')
    
    @action(detail=False, methods=['post'])
    def update_progress(self, request):
        """تحديث تقدم فيديو"""
        video_id = request.data.get('video_id')
        
        if not video_id:
            return Response(
                {'error': 'يجب تحديد الفيديو'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            return Response(
                {'error': 'الفيديو غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        student = request.user.student_profile
        
        # التحقق من التسجيل في الكورس
        try:
            enrollment = Enrollment.objects.get(
                student=student,
                course=video.course,
                status='active'
            )
        except Enrollment.DoesNotExist:
            return Response(
                {'error': 'يجب التسجيل في الكورس أولاً'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # بدء الكورس تلقائياً
        enrollment.mark_as_started()
        
        serializer = UpdateVideoProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # تحديث أو إنشاء التقدم
        progress, created = VideoProgress.objects.get_or_create(
            student=student,
            video=video,
            enrollment=enrollment,
            defaults={
                'watched_duration': serializer.validated_data['watched_duration'],
                'last_position': serializer.validated_data['last_position'],
                'completed': serializer.validated_data.get('completed', False),
                'view_count': 1
            }
        )
        
        if not created:
            progress.watched_duration = max(
                progress.watched_duration,
                serializer.validated_data['watched_duration']
            )
            progress.last_position = serializer.validated_data['last_position']
            progress.view_count += 1
            
            if serializer.validated_data.get('completed') and not progress.completed:
                progress.mark_as_completed()
            
            progress.save()
        
        # تحديث التقدم في الخلفية
        calculate_enrollment_progress.delay(enrollment.id)
        
        # تحديث سلسلة التعلم
        update_learning_streak.delay(student.id)
        
        return Response(VideoProgressSerializer(progress).data)


class CourseNoteViewSet(viewsets.ModelViewSet):
    """ViewSet للملاحظات"""
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateCourseNoteSerializer
        return CourseNoteSerializer
    
    def get_queryset(self):
        student = self.request.user.student_profile
        return CourseNote.objects.filter(student=student).select_related('video')
    
    def perform_create(self, serializer):
        student = self.request.user.student_profile
        video = serializer.validated_data.get('video')
        
        # الحصول على التسجيل
        enrollment = Enrollment.objects.get(
            student=student,
            course=video.course if video else serializer.validated_data.get('course')
        )
        
        serializer.save(student=student, enrollment=enrollment)
    
    @action(detail=False, methods=['get'])
    def by_course(self, request):
        """ملاحظات كورس معين"""
        course_id = request.query_params.get('course_id')
        
        if not course_id:
            return Response(
                {'error': 'يجب تحديد الكورس'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        student = request.user.student_profile
        notes = CourseNote.objects.filter(
            student=student,
            enrollment__course_id=course_id
        )
        
        serializer = CourseNoteSerializer(notes, many=True)
        return Response(serializer.data)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للشهادات (Read-Only)"""
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_queryset(self):
        student = self.request.user.student_profile
        return Certificate.objects.filter(
            enrollment__student=student
        ).select_related('enrollment__course')
    
    @action(detail=False, methods=['get'])
    def verify(self, request):
        """التحقق من شهادة"""
        cert_number = request.query_params.get('certificate_number')
        
        if not cert_number:
            return Response(
                {'error': 'يجب إدخال رقم الشهادة'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            certificate = Certificate.objects.get(certificate_number=cert_number)
            serializer = CertificateSerializer(certificate)
            return Response({
                'valid': True,
                'certificate': serializer.data
            })
        except Certificate.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'شهادة غير صالحة'
            }, status=status.HTTP_404_NOT_FOUND)


class InstructorEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    المدرب يشوف تسجيلات طلابه في كورساته
    """
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get_serializer_class(self):
        return EnrollmentSerializer

    def get_queryset(self):
        return Enrollment.objects.filter(
            course__instructor=self.request.user
        ).select_related(
            'course', 'student__user'
        ).order_by('-enrolled_at')

    @action(detail=False, methods=['get'], url_path='by-course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        qs = self.get_queryset().filter(course_id=course_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
