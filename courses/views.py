from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.core.cache import cache
from django.db.models import F, Prefetch, Count, Sum
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
        data = list(serializer.data)
        cache.set(cache_key, data, timeout=600)
        return Response(data)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'level', 'language', 'is_featured']
    search_fields = ['title', 'description', 'instructor__username']
    ordering_fields = ['created_at', 'price', 'rating', 'students_count']
    ordering = ['-created_at']
    lookup_field = 'slug'
    permission_classes = [AllowAny]

    def get_object(self):
        """يقبل slug نصي أو id رقمي - يجيب المنشور وغير المنشور"""
        lookup = self.kwargs.get(self.lookup_field, '')
        # نبحث في كل الكورسات (مش بس المنشورة) للـ retrieve
        base_qs = Course.objects.select_related('category', 'instructor').prefetch_related(
            Prefetch('sections',
                queryset=Section.objects.prefetch_related('videos__attachments').order_by('order'))
        )
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
                Prefetch('sections',
                    queryset=Section.objects.prefetch_related(
                        'videos__attachments').order_by('order'))
            )
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        try:
            if user.is_authenticated:
                student = user.student_profile
                enrolled_ids = set(Enrollment.objects.filter(
                    student=student).values_list('course_id', flat=True))
                watched_ids = set(VideoProgress.objects.filter(
                    student=student, completed=True).values_list('video_id', flat=True))
                context['enrolled_courses'] = enrolled_ids
                context['watched_videos'] = watched_ids
        except Exception:
            context['enrolled_courses'] = set()
            context['watched_videos'] = set()
        return context

    def retrieve(self, request, *args, **kwargs):
        course = self.get_object()
        Course.objects.filter(pk=course.pk).update(views_count=F('views_count') + 1)
        return Response(self.get_serializer(course).data)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def reviews(self, request, slug=None):
        course = self.get_object()
        reviews = course.reviews.select_related('student').order_by('-created_at')
        page = self.paginate_queryset(reviews)
        serializer = CourseReviewSerializer(page or reviews, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data) if page else Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStudent])
    def add_review(self, request, slug=None):
        course = self.get_object()
        student = request.user.student_profile
        if not Enrollment.objects.filter(student=student, course=course).exists():
            return Response({'error': 'يجب التسجيل في الكورس أولاً'}, status=status.HTTP_403_FORBIDDEN)
        if CourseReview.objects.filter(course=course, student=student).exists():
            return Response({'error': 'قيّمت هذا الكورس مسبقاً'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CreateCourseReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = CourseReview.objects.create(course=course, student=student, **serializer.validated_data)
        update_course_rating.delay(course.id)
        return Response(CourseReviewSerializer(review, context={'request': request}).data, status=status.HTTP_201_CREATED)


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    queryset = Video.objects.select_related('course', 'section').prefetch_related('attachments')

    def retrieve(self, request, *args, **kwargs):
        video = self.get_object()
        student = request.user.student_profile
        is_enrolled = Enrollment.objects.filter(student=student, course=video.course).exists()
        if not video.is_free and not is_enrolled:
            return Response({'error': 'يجب التسجيل في الكورس لمشاهدة هذا الفيديو'}, status=status.HTTP_403_FORBIDDEN)
        increment_video_views.delay(video.id)
        return Response(self.get_serializer(video).data)


# ═══════════════════════════════════════════════════════════
#  INSTRUCTOR — كورسات
# ═══════════════════════════════════════════════════════════
class InstructorCourseViewSet(viewsets.ModelViewSet):
    """المدرب يدير كورساته كاملاً"""
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
        serializer.save(instructor=self.request.user, is_published=True)

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if course.students_count > 0:
            return Response({'error': 'لا يمكن حذف كورس فيه طلاب مسجلين'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    # ── نشر / إلغاء نشر الكورس ──
    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        course = self.get_object()
        course.is_published = not course.is_published
        course.save()
        return Response({
            'is_published': course.is_published,
            'message': 'تم نشر الكورس ✅' if course.is_published else 'تم إلغاء النشر'
        })

    # ── إحصائيات الكورس ──
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        course = self.get_object()
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(course=course)
        return Response({
            'total_students': enrollments.count(),
            'active_students': enrollments.filter(status='active').count(),
            'completed_students': enrollments.filter(is_completed=True).count(),
            'average_progress': enrollments.aggregate(
                avg=Sum('progress_percentage') / Count('id'))['avg'] or 0,
            'total_revenue': course.price * enrollments.count(),
            'rating': course.rating,
            'views': course.views_count,
        })

    # ── قائمة الطلاب المسجلين ──
    @action(detail=True, methods=['get'], url_path='students')
    def course_students(self, request, pk=None):
        course = self.get_object()
        from enrollments.models import Enrollment
        from enrollments.serializers import EnrollmentSerializer
        enrollments = Enrollment.objects.filter(course=course).select_related(
            'student__user').order_by('-enrolled_at')
        data = []
        for e in enrollments:
            data.append({
                'student_id': e.student.id,
                'name': e.student.user.get_full_name() or e.student.user.username,
                'email': e.student.user.email,
                'enrolled_at': e.enrolled_at,
                'progress': e.progress_percentage,
                'is_completed': e.is_completed,
                'status': e.status,
            })
        return Response(data)


# ═══════════════════════════════════════════════════════════
#  INSTRUCTOR — محتوى (أقسام + فيديوهات)
# ═══════════════════════════════════════════════════════════
class InstructorContentViewSet(viewsets.GenericViewSet):
    """المدرب يدير محتوى كورساته"""
    permission_classes = [IsAuthenticated]

    def _get_course(self, pk):
        try:
            return Course.objects.get(pk=pk, instructor=self.request.user)
        except Course.DoesNotExist:
            return None

    # GET /instructor-content/{id}/
    def retrieve(self, request, pk=None):
        course = self._get_course(pk)
        if not course:
            return Response({'error': 'الكورس غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import SectionWriteSerializer, VideoReadSerializer
        sections = Section.objects.filter(course=course).prefetch_related('videos').order_by('order')
        loose = Video.objects.filter(course=course, section=None).order_by('order')
        return Response({
            'course_id': course.id,
            'course_title': course.title,
            'sections': SectionWriteSerializer(sections, many=True).data,
            'loose_videos': VideoReadSerializer(loose, many=True).data,
        })

    # POST /instructor-content/{id}/sections/
    @action(detail=True, methods=['post'], url_path='sections')
    def add_section(self, request, pk=None):
        course = self._get_course(pk)
        if not course:
            return Response({'error': 'الكورس غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import SectionWriteSerializer
        # تجنب unique_together - نستخدم max+1 بدل count
        from django.db.models import Max
        max_order_val = Section.objects.filter(course=course).aggregate(Max('order'))['order__max']
        next_order = (max_order_val + 1) if max_order_val is not None else 0
        section = Section.objects.create(
            course=course,
            title=request.data.get('title', 'قسم جديد'),
            description=request.data.get('description', ''),
            order=next_order,
        )
        return Response(SectionWriteSerializer(section).data, status=status.HTTP_201_CREATED)

    # PATCH|DELETE /instructor-content/{id}/sections/{section_id}/
    @action(detail=True, methods=['patch', 'delete'], url_path='sections/(?P<section_id>[^/.]+)')
    def manage_section(self, request, pk=None, section_id=None):
        course = self._get_course(pk)
        if not course:
            return Response({'error': 'الكورس غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        try:
            section = Section.objects.get(id=section_id, course=course)
        except Section.DoesNotExist:
            return Response({'error': 'القسم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            section.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        from .serializers import SectionWriteSerializer
        if 'title' in request.data:
            section.title = request.data['title']
        if 'description' in request.data:
            section.description = request.data['description']
        section.save()
        return Response(SectionWriteSerializer(section).data)

    # POST /instructor-content/{id}/videos/
    @action(detail=True, methods=['post'], url_path='videos')
    def add_video(self, request, pk=None):
        course = self._get_course(pk)
        if not course:
            return Response({'error': 'الكورس غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import VideoReadSerializer
        order = Video.objects.filter(course=course).count()
        # تحويل duration_minutes → seconds
        duration = 0
        if request.data.get('duration_minutes'):
            try:
                duration = int(float(request.data['duration_minutes'])) * 60
            except (ValueError, TypeError):
                duration = 0
        elif request.data.get('duration'):
            try:
                duration = int(request.data['duration'])
            except (ValueError, TypeError):
                duration = 0

        section_id = request.data.get('section') or None

        # تحقق من الـ section ينتمي للكورس
        if section_id:
            if not Section.objects.filter(id=section_id, course=course).exists():
                return Response({'error': 'القسم لا ينتمي لهذا الكورس'}, status=status.HTTP_400_BAD_REQUEST)

        video = Video.objects.create(
            course=course,
            section_id=section_id,
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            video_url=request.data.get('video_url', '') or '',
            video_file=request.FILES.get('video_file', None),
            duration=duration,
            order=order,
            is_free=request.data.get('is_free', False),
            is_downloadable=request.data.get('is_downloadable', False),
        )
        return Response(VideoReadSerializer(video).data, status=status.HTTP_201_CREATED)

    # PATCH|DELETE /instructor-content/{id}/videos/{video_id}/
    @action(detail=True, methods=['patch', 'delete'], url_path='videos/(?P<video_id>[^/.]+)')
    def manage_video(self, request, pk=None, video_id=None):
        course = self._get_course(pk)
        if not course:
            return Response({'error': 'الكورس غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        try:
            video = Video.objects.get(id=video_id, course=course)
        except Video.DoesNotExist:
            return Response({'error': 'الفيديو غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            video.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        from .serializers import VideoReadSerializer
        updatable = ['title', 'description', 'video_url', 'is_free', 'is_downloadable', 'order']
        for k in updatable:
            if k in request.data:
                setattr(video, k, request.data[k])
        if 'duration_minutes' in request.data:
            try:
                video.duration = int(float(request.data['duration_minutes'])) * 60
            except (ValueError, TypeError):
                pass
        video.save()
        return Response(VideoReadSerializer(video).data)


# ═══════════════════════════════════════════════════
#  VIDEO STREAM — بث الفيديو المحمي
# ═══════════════════════════════════════════════════
import hmac, hashlib, time, os
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

def _sign_video(video_id: int, user_id: int) -> str:
    """ينشئ توقيع مؤقت للفيديو صالح 2 ساعة"""
    expires = int(time.time()) + 7200
    msg = f"{video_id}:{user_id}:{expires}"
    sig = hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{expires}:{sig}"

def _verify_token(video_id: int, user_id: int, token: str) -> bool:
    """يتحقق من صحة الـ token"""
    try:
        expires_str, sig = token.split(":", 1)
        expires = int(expires_str)
        if time.time() > expires:
            return False
        msg = f"{video_id}:{user_id}:{expires}"
        expected = hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def video_token(request, video_id):
    """يرجع توقيع مؤقت للفيديو — الطالب لازم يكون مسجل في الكورس"""
    from .models import Video
    from enrollments.models import Enrollment

    try:
        video = Video.objects.select_related('course').get(id=video_id)
    except Video.DoesNotExist:
        raise Http404

    # لو الفيديو مجاني أو الطالب مسجل في الكورس
    if not video.is_free:
        try:
            student = request.user.student_profile
            if not Enrollment.objects.filter(student=student, course=video.course, status='active').exists():
                return Response({'error': 'غير مصرح'}, status=403)
        except Exception:
            # Instructor يقدر يشوف فيديوهات كورساته
            if video.course.instructor != request.user:
                return Response({'error': 'غير مصرح'}, status=403)

    token = _sign_video(video_id, request.user.id)
    return Response({'token': token, 'expires_in': 7200})


@api_view(['GET'])
def video_stream(request, video_id):
    """يبث الفيديو بعد التحقق من الـ token — HTTP Range support"""
    token   = request.GET.get('token', '')
    user_id = request.GET.get('uid', '')

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise Http404

    if not _verify_token(video_id, user_id, token):
        raise Http404

    from .models import Video
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        raise Http404

    # الأولوية: video_file (على السيرفر) ثم video_url (خارجي)
    if video.video_file:
        video_path = video.video_file.path
    elif video.video_url:
        # لو خارجي، redirect مش stream
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(video.video_url)
    else:
        raise Http404

    if not os.path.exists(video_path):
        raise Http404

    file_size = os.path.getsize(video_path)
    range_header = request.META.get('HTTP_RANGE', '')

    # HTTP Range Requests — عشان المتصفح يقدر يقفز في الفيديو
    if range_header:
        try:
            range_val = range_header.strip().replace('bytes=', '')
            start_str, end_str = range_val.split('-')
            start = int(start_str)
            end   = int(end_str) if end_str else file_size - 1
            end   = min(end, file_size - 1)
            length = end - start + 1

            def range_iterator(path, s, e, chunk=65536):
                with open(path, 'rb') as f:
                    f.seek(s)
                    remaining = e - s + 1
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            response = StreamingHttpResponse(
                range_iterator(video_path, start, end),
                status=206,
                content_type='video/mp4'
            )
            response['Content-Range']  = f'bytes {start}-{end}/{file_size}'
            response['Content-Length'] = str(length)
        except Exception:
            raise Http404
    else:
        def file_iterator(path, chunk=65536):
            with open(path, 'rb') as f:
                while data := f.read(chunk):
                    yield data

        response = StreamingHttpResponse(file_iterator(video_path), content_type='video/mp4')
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges']  = 'bytes'

    # Headers الحماية
    response['Cache-Control']          = 'no-store, no-cache, private'
    response['Pragma']                 = 'no-cache'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options']        = 'SAMEORIGIN'
    response['Content-Disposition']    = 'inline'   # inline لا attachment
    return response
