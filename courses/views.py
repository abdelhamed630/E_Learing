from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.core.cache import cache
from django.db.models import F, Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from students.permissions import IsStudent
from enrollments.models import Enrollment, VideoProgress

from .models import Category, Course, Video, CourseReview, Section
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    VideoSerializer, CourseReviewSerializer, CreateCourseReviewSerializer,
    InstructorCourseSerializer
)
from .tasks import update_course_rating, increment_video_views


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def list(self, request, *args, **kwargs):
        cache_key = "categories_list"
        data = cache.get(cache_key)
        if data:
            return Response(data)

        serializer = self.get_serializer(self.get_queryset(), many=True)
        cache.set(cache_key, serializer.data, timeout=600)
        return Response(serializer.data)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'level', 'language', 'is_featured']
    search_fields = ['title', 'description', 'instructor__username']
    ordering_fields = ['created_at', 'price', 'rating', 'students_count']
    ordering = ['-created_at']
    lookup_field = 'slug'
    permission_classes = [AllowAny]

    def get_queryset(self):
        # ✅ إصلاح: شيلنا annotate(total_videos=...) لأنه بيتعارض مع @property في الـ model
        return (
            Course.objects
            .filter(is_published=True)
            .select_related('category', 'instructor')
            .prefetch_related(
                Prefetch(
                    'sections',
                    queryset=Section.objects.prefetch_related('videos__attachments').order_by('order')
                )
            )
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user

        if user.is_authenticated and hasattr(user, "student_profile"):
            enrolled_ids = set(
                Enrollment.objects.filter(
                    student=user.student_profile
                ).values_list("course_id", flat=True)
            )
            watched_ids = set(
                VideoProgress.objects.filter(
                    student=user.student_profile,
                    completed=True
                ).values_list("video_id", flat=True)
            )
            context["enrolled_courses"] = enrolled_ids
            context["watched_videos"] = watched_ids

        return context

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        Course.objects.filter(pk=course.pk).update(views_count=F('views_count') + 1)
        serializer = self.get_serializer(course)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsStudent])
    def reviews(self, request, slug=None):
        course = self.get_object()
        reviews = course.reviews.select_related('student').order_by('-created_at')
        page = self.paginate_queryset(reviews)
        serializer = CourseReviewSerializer(page or reviews, many=True)
        if page:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStudent])
    def add_review(self, request, slug=None):
        course = self.get_object()
        student = request.user.student_profile

        if not Enrollment.objects.filter(student=student, course=course).exists():
            return Response(
                {'error': 'يجب أن تكون مسجلاً في الكورس لتقييمه'},
                status=status.HTTP_403_FORBIDDEN
            )

        if CourseReview.objects.filter(course=course, student=student).exists():
            return Response(
                {'error': 'لقد قيمت هذا الكورس مسبقاً'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CreateCourseReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = CourseReview.objects.create(
            course=course,
            student=student,
            **serializer.validated_data
        )

        update_course_rating.delay(course.id)

        return Response(
            CourseReviewSerializer(review).data,
            status=status.HTTP_201_CREATED
        )


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    queryset = Video.objects.select_related('course', 'section').prefetch_related('attachments')

    def retrieve(self, request, *args, **kwargs):
        video = self.get_object()
        student = request.user.student_profile

        is_enrolled = Enrollment.objects.filter(
            student=student,
            course=video.course
        ).exists()

        if not video.is_free and not is_enrolled:
            return Response(
                {'error': 'يجب التسجيل في الكورس لمشاهدة هذا الفيديو'},
                status=status.HTTP_403_FORBIDDEN
            )

        increment_video_views.delay(video.id)
        serializer = self.get_serializer(video)
        return Response(serializer.data)


class InstructorCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet للمدرب - إنشاء وتعديل وحذف كورساته فقط
    """
    serializer_class = None
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_published', 'level', 'language', 'category']
    search_fields = ['title', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        from .serializers import InstructorCourseSerializer
        return InstructorCourseSerializer

    def get_queryset(self):
        # المدرب يشوف كورساته بس (منشورة ومسودة)
        return Course.objects.filter(
            instructor=self.request.user
        ).select_related('category', 'instructor').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if course.students_count > 0:
            return Response(
                {'error': 'لا يمكن حذف كورس فيه طلاب مسجلين'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)
