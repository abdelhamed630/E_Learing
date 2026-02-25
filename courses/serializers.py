from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum
from .models import Category, Course, Section, Video, Attachment, CourseReview

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'courses_count']

    def get_courses_count(self, obj):
        return obj.courses.filter(is_published=True).count()


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'title', 'file', 'file_size', 'created_at']
        read_only_fields = ['id', 'created_at']


class VideoSerializer(serializers.ModelSerializer):
    # ✅ @property → SerializerMethodField دايمًا
    duration_formatted = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    is_watched = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id', 'title', 'description', 'video_url', 'thumbnail',
            'duration', 'duration_formatted', 'order', 'is_free',
            'is_downloadable', 'views_count', 'attachments', 'is_watched'
        ]
        read_only_fields = ['id', 'views_count']

    def get_duration_formatted(self, obj):
        return obj.duration_formatted

    def get_is_watched(self, obj):
        # ✅ نستخدم الـ context اللي حضّرناه في get_serializer_context
        watched_videos = self.context.get('watched_videos')
        if watched_videos is not None:
            return obj.id in watched_videos
        return False


class SectionSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)
    videos_count = serializers.SerializerMethodField()
    # ✅ @property → SerializerMethodField
    total_duration = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ['id', 'title', 'description', 'order', 'videos', 'videos_count', 'total_duration']
        read_only_fields = ['id']

    def get_videos_count(self, obj):
        return obj.videos.count()

    def get_total_duration(self, obj):
        # ✅ نستخدم الـ @property في الـ model مباشرة
        return obj.total_duration


class CourseListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    instructor = UserSerializer(read_only=True)
    # ✅ @property → SerializerMethodField
    final_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'thumbnail', 'category', 'instructor',
            'level', 'language', 'price', 'discount_price', 'final_price',
            'discount_percentage', 'duration_hours', 'students_count',
            'rating', 'is_featured', 'is_enrolled', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'students_count', 'rating', 'created_at']

    def get_final_price(self, obj):
        return obj.final_price

    def get_discount_percentage(self, obj):
        return obj.discount_percentage

    def get_is_enrolled(self, obj):
        # ✅ نستخدم الـ context بدل query جديد في كل row
        enrolled_courses = self.context.get('enrolled_courses')
        if enrolled_courses is not None:
            return obj.id in enrolled_courses
        return False


class CourseDetailSerializer(CourseListSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    # ✅ @property → SerializerMethodField
    total_videos = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            'description', 'trailer_url', 'requirements', 'what_will_learn',
            'sections', 'total_videos', 'total_duration', 'views_count',
            'reviews_count', 'updated_at'
        ]

    def get_total_videos(self, obj):
        return obj.total_videos

    def get_total_duration(self, obj):
        return obj.total_duration

    def get_reviews_count(self, obj):
        return obj.reviews.count()


class CourseReviewSerializer(serializers.ModelSerializer):
    # ✅ إصلاح: student هنا هو User مش Student model
    # فـ full_name مش موجودة - نستخدم get_full_name()
    student_name = serializers.SerializerMethodField()
    student_avatar = serializers.SerializerMethodField()

    class Meta:
        model = CourseReview
        fields = [
            'id', 'student_name', 'student_avatar', 'rating',
            'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        # ✅ obj.student هو User object
        return obj.student.get_full_name() or obj.student.username

    def get_student_avatar(self, obj):
        # ✅ User model عندك avatar field؟ لو مفيش نرجع None
        request = self.context.get('request')
        avatar = getattr(obj.student, 'avatar', None)
        if avatar and request:
            try:
                return request.build_absolute_uri(avatar.url)
            except Exception:
                return None
        return None


class CreateCourseReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseReview
        fields = ['rating', 'comment']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("التقييم يجب أن يكون بين 1 و 5")
        return value
