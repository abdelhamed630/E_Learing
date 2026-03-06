from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.core.cache import cache
from django.db.models import F, Prefetch, Sum
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

    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field)
        base_qs = self.get_queryset()
        if str(lookup).isdigit():
            obj = base_qs.filter(id=int(lookup)).first()
        else:
            obj = base_qs.filter(slug=lookup).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound('الكورس غير موجود')
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
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

        if user.is_authenticated:
            if hasattr(user, 'student_profile') and user.student_profile:
                enrolled_ids = set(
                    Enrollment.objects.filter(
                        student=user.student_profile
                    ).values_list('course_id', flat=True)
                )
                watched_ids = set(
                    VideoProgress.objects.filter(
                        student=user.student_profile,
                        completed=True
                    ).values_list('video_id', flat=True)
                )
                context['enrolled_courses'] = enrolled_ids
                context['watched_videos'] = watched_ids
            elif user.role == 'instructor':
                # المدرب يشوف كورساته كـ enrolled
                instructor_courses = set(
                    Course.objects.filter(instructor=user).values_list('id', flat=True)
                )
                context['enrolled_courses'] = instructor_courses
                context['watched_videos'] = set()

        return context

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        Course.objects.filter(pk=course.pk).update(views_count=F('views_count') + 1)
        serializer = self.get_serializer(course)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def reviews(self, request, slug=None):
        course = self.get_object()
        reviews = course.reviews.select_related('student__user').order_by('-created_at')
        page = self.paginate_queryset(reviews)
        serializer = CourseReviewSerializer(page or reviews, many=True, context={'request': request})
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
            CourseReviewSerializer(review, context={'request': request}).data,
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


# ─────────────────────────────────────────────────────────────
#  INSTRUCTOR CONTENT VIEWSET - إدارة محتوى الكورس للمدرب
# ─────────────────────────────────────────────────────────────

def to_bool(val, default=False):
    """تحويل أي قيمة لـ boolean بأمان"""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('1', 'true', 'yes', 't')
    if isinstance(val, int):
        return bool(val)
    return default


class InstructorContentViewSet(viewsets.ViewSet):
    """
    ViewSet لإدارة محتوى الكورس (sections + videos) للمدرب
    """
    permission_classes = [IsAuthenticated]

    def _get_course(self, request, course_pk):
        """جلب الكورس والتحقق من ملكية المدرب"""
        try:
            course = Course.objects.get(pk=course_pk, instructor=request.user)
            return course, None
        except Course.DoesNotExist:
            return None, Response(
                {'error': 'الكورس غير موجود أو ليس لديك صلاحية'},
                status=status.HTTP_404_NOT_FOUND
            )

    # ── Sections ──────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='(?P<course_pk>[^/.]+)/sections')
    def list_sections(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err
        sections = Section.objects.filter(course=course).prefetch_related(
            'videos__attachments'
        ).order_by('order')
        data = []
        for s in sections:
            data.append({
                'id': s.id,
                'title': s.title,
                'description': s.description,
                'order': s.order,
                'videos': VideoSerializer(
                    s.videos.all(), many=True, context={'request': request}
                ).data
            })
        return Response(data)

    @action(detail=False, methods=['post'], url_path='(?P<course_pk>[^/.]+)/sections/add')
    def add_section(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        title = request.data.get('title', '').strip()
        if not title:
            return Response({'error': 'عنوان القسم مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        last_order = Section.objects.filter(course=course).count()
        section = Section.objects.create(
            course=course,
            title=title,
            description=request.data.get('description', ''),
            order=last_order
        )
        return Response({
            'id': section.id,
            'title': section.title,
            'description': section.description,
            'order': section.order,
            'videos': []
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_path='(?P<course_pk>[^/.]+)/sections/(?P<section_pk>[^/.]+)/edit')
    def edit_section(self, request, course_pk=None, section_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        try:
            section = Section.objects.get(pk=section_pk, course=course)
        except Section.DoesNotExist:
            return Response({'error': 'القسم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if 'title' in request.data:
            section.title = request.data['title']
        if 'description' in request.data:
            section.description = request.data['description']
        if 'order' in request.data:
            section.order = request.data['order']
        section.save()

        return Response({'id': section.id, 'title': section.title, 'order': section.order})

    @action(detail=False, methods=['delete'], url_path='(?P<course_pk>[^/.]+)/sections/(?P<section_pk>[^/.]+)/delete')
    def delete_section(self, request, course_pk=None, section_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        try:
            section = Section.objects.get(pk=section_pk, course=course)
        except Section.DoesNotExist:
            return Response({'error': 'القسم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        section.delete()
        return Response({'message': 'تم حذف القسم'})

    @action(detail=False, methods=['post'], url_path='(?P<course_pk>[^/.]+)/sections/reorder')
    def reorder_sections(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        order_list = request.data.get('order', [])  # [{"id": 1, "order": 0}, ...]
        for item in order_list:
            Section.objects.filter(pk=item['id'], course=course).update(order=item['order'])

        return Response({'message': 'تم إعادة الترتيب'})

    # ── Videos ──────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='(?P<course_pk>[^/.]+)/videos')
    def add_video(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        title = request.data.get('title', '').strip()
        if not title:
            return Response({'error': 'عنوان الفيديو مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        # section_id اختياري
        section_id = request.data.get('section_id') or None
        section = None
        if section_id:
            try:
                section = Section.objects.get(pk=section_id, course=course)
            except Section.DoesNotExist:
                return Response({'error': 'القسم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        # مدة الفيديو
        try:
            duration_val = request.data.get('duration_minutes', 0)
            duration = int(float(duration_val) * 60) if duration_val else 0
        except (ValueError, TypeError):
            duration = 0

        # ترتيب الفيديو
        order = Video.objects.filter(course=course, section=section).count()

        video = Video.objects.create(
            course=course,
            section=section,
            title=title,
            description=request.data.get('description', '') or '',
            video_file=request.FILES.get('video_file', None),
            video_url=request.data.get('video_url', '') or None,
            duration=duration,
            order=order,
            is_free=to_bool(request.data.get('is_free', False)),
            is_downloadable=to_bool(request.data.get('is_downloadable', False)),
        )

        serializer = VideoSerializer(video, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'], url_path='(?P<course_pk>[^/.]+)/videos/(?P<video_pk>[^/.]+)/edit')
    def edit_video(self, request, course_pk=None, video_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        try:
            video = Video.objects.get(pk=video_pk, course=course)
        except Video.DoesNotExist:
            return Response({'error': 'الفيديو غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if 'title' in request.data:
            video.title = request.data['title']
        if 'description' in request.data:
            video.description = request.data['description']
        if 'video_url' in request.data:
            video.video_url = request.data['video_url'] or None
        if 'video_file' in request.FILES:
            video.video_file = request.FILES['video_file']
        if 'is_free' in request.data:
            video.is_free = to_bool(request.data['is_free'])
        if 'is_downloadable' in request.data:
            video.is_downloadable = to_bool(request.data['is_downloadable'])
        if 'order' in request.data:
            video.order = request.data['order']
        if 'duration_minutes' in request.data:
            try:
                video.duration = int(float(request.data['duration_minutes']) * 60)
            except (ValueError, TypeError):
                pass
        video.save()

        return Response(VideoSerializer(video, context={'request': request}).data)

    @action(detail=False, methods=['delete'], url_path='(?P<course_pk>[^/.]+)/videos/(?P<video_pk>[^/.]+)/delete')
    def delete_video(self, request, course_pk=None, video_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        try:
            video = Video.objects.get(pk=video_pk, course=course)
        except Video.DoesNotExist:
            return Response({'error': 'الفيديو غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        video.delete()
        return Response({'message': 'تم حذف الفيديو'})

    @action(detail=False, methods=['post'], url_path='(?P<course_pk>[^/.]+)/videos/reorder')
    def reorder_videos(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        order_list = request.data.get('order', [])
        for item in order_list:
            Video.objects.filter(pk=item['id'], course=course).update(order=item['order'])

        return Response({'message': 'تم إعادة ترتيب الفيديوهات'})

    # ── Course Actions ──────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='(?P<course_pk>[^/.]+)/toggle-publish')
    def toggle_publish(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        course.is_published = not course.is_published
        course.save()

        return Response({
            'message': 'تم نشر الكورس' if course.is_published else 'تم إلغاء نشر الكورس',
            'is_published': course.is_published
        })

    @action(detail=False, methods=['get'], url_path='(?P<course_pk>[^/.]+)/stats')
    def course_stats(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        from enrollments.models import Enrollment as Enroll
        enrollments = Enroll.objects.filter(course=course)

        return Response({
            'total_students': enrollments.count(),
            'active_students': enrollments.filter(status='active').count(),
            'completed_students': enrollments.filter(is_completed=True).count(),
            'average_progress': enrollments.aggregate(
                avg=Sum('progress')
            )['avg'] or 0,
            'total_revenue': float(course.price) * enrollments.count(),
            'total_videos': course.total_videos,
            'total_duration': course.total_duration,
            'views_count': course.views_count,
            'rating': float(course.rating),
        })

    @action(detail=False, methods=['get'], url_path='(?P<course_pk>[^/.]+)/students')
    def course_students(self, request, course_pk=None):
        course, err = self._get_course(request, course_pk)
        if err:
            return err

        from enrollments.models import Enrollment as Enroll
        enrollments = Enroll.objects.filter(course=course).select_related(
            'student__user'
        ).order_by('-enrolled_at')

        data = []
        for e in enrollments:
            data.append({
                'id': e.id,
                'student_name': e.student.user.get_full_name() or e.student.user.username,
                'student_email': e.student.user.email,
                'progress': e.progress,
                'status': e.status,
                'enrolled_at': e.enrolled_at,
                'last_accessed': e.last_accessed,
            })

        return Response(data)


# ─────────────────────────────────────────────────────────────
#  VIDEO TOKEN - HMAC streaming
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_video_token(request, video_id):
    """
    إصدار token مؤقت للوصول لملف الفيديو (HMAC-SHA256)
    """
    import hmac, hashlib, time
    from django.conf import settings

    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return Response({'error': 'الفيديو غير موجود'}, status=status.HTTP_404_NOT_FOUND)

    # التحقق من الصلاحية
    is_instructor = video.course.instructor == request.user
    is_enrolled = False
    if hasattr(request.user, 'student_profile'):
        is_enrolled = Enrollment.objects.filter(
            student=request.user.student_profile,
            course=video.course
        ).exists()

    if not video.is_free and not is_instructor and not is_enrolled:
        return Response({'error': 'ليس لديك صلاحية لمشاهدة هذا الفيديو'}, status=status.HTTP_403_FORBIDDEN)

    # إنشاء token
    secret = getattr(settings, 'SECRET_KEY', 'default-secret')
    expires = int(time.time()) + 7200  # ساعتين
    payload = f"{video_id}:{request.user.id}:{expires}"
    token = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return Response({
        'token': token,
        'expires': expires,
        'video_id': video_id,
    })


# ─────────────────────────────────────────────────────────────
#  INSTRUCTOR COURSE VIEWSET
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
#  VIDEO STREAM — بث الفيديو المحلي بعد التحقق من التوكن
# ─────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stream_video(request, video_id):
    """بث الفيديو المحلي أو redirect للرابط الخارجي"""
    import os, mimetypes
    from django.http import FileResponse, HttpResponse, HttpResponseRedirect

    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        return HttpResponse('Not Found', status=404)

    # تحقق من الصلاحية
    is_instructor = video.course.instructor == request.user
    is_enrolled = False
    if hasattr(request.user, 'student_profile') and request.user.student_profile:
        is_enrolled = Enrollment.objects.filter(
            student=request.user.student_profile,
            course=video.course
        ).exists()

    if not video.is_free and not is_instructor and not is_enrolled:
        return HttpResponse('Forbidden', status=403)

    # ملف محلي
    if video.video_file:
        try:
            file_path = video.video_file.path
            if not os.path.exists(file_path):
                return HttpResponse('File Not Found', status=404)
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type or 'video/mp4'
            )
            response['Content-Disposition'] = 'inline'
            response['Accept-Ranges'] = 'bytes'
            return response
        except Exception:
            return HttpResponse('Error', status=500)

    # رابط خارجي
    if video.video_url:
        return HttpResponseRedirect(video.video_url)

    return HttpResponse('No video source', status=404)
