"""
Serializers للتسجيلات
"""
from rest_framework import serializers
from .models import Enrollment, VideoProgress, CourseNote, Certificate, LearningStreak


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer للتسجيل"""
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    course_instructor = serializers.CharField(source='course.instructor.username', read_only=True)
    is_completed = serializers.BooleanField(source='is_completed', read_only=True)
    days_since_enrollment = serializers.IntegerField(source='days_since_enrollment', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student_name', 'course_title', 'course_thumbnail',
            'course_instructor', 'status', 'progress', 'total_time_spent',
            'certificate_issued', 'certificate_url', 'enrolled_at',
            'started_at', 'completed_at', 'last_accessed',
            'is_completed', 'days_since_enrollment'
        ]
        read_only_fields = [
            'id', 'enrolled_at', 'started_at', 'completed_at',
            'last_accessed', 'certificate_issued', 'certificate_url'
        ]


class EnrollmentDetailSerializer(EnrollmentSerializer):
    """Serializer لتفاصيل التسجيل مع معلومات الكورس"""
    from courses.serializers import CourseDetailSerializer
    
    course = CourseDetailSerializer(read_only=True)
    videos_completed = serializers.SerializerMethodField()
    total_videos = serializers.SerializerMethodField()
    
    class Meta(EnrollmentSerializer.Meta):
        fields = EnrollmentSerializer.Meta.fields + [
            'course', 'videos_completed', 'total_videos'
        ]
    
    def get_videos_completed(self, obj):
        """عدد الفيديوهات المكتملة"""
        return VideoProgress.objects.filter(
            enrollment=obj,
            completed=True
        ).count()
    
    def get_total_videos(self, obj):
        """إجمالي عدد الفيديوهات"""
        return obj.course.videos.count()


class VideoProgressSerializer(serializers.ModelSerializer):
    """Serializer لتقدم الفيديو"""
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_duration = serializers.IntegerField(source='video.duration', read_only=True)
    completion_percentage = serializers.IntegerField(source='completion_percentage', read_only=True)
    
    class Meta:
        model = VideoProgress
        fields = [
            'id', 'video', 'video_title', 'video_duration',
            'watched_duration', 'last_position', 'completed',
            'completion_percentage', 'view_count',
            'first_watched', 'last_watched', 'completed_at'
        ]
        read_only_fields = [
            'id', 'first_watched', 'last_watched', 'completed_at', 'view_count'
        ]


class UpdateVideoProgressSerializer(serializers.Serializer):
    """Serializer لتحديث تقدم الفيديو"""
    watched_duration = serializers.IntegerField(
        required=True,
        min_value=0
    )
    last_position = serializers.IntegerField(
        required=True,
        min_value=0
    )
    completed = serializers.BooleanField(default=False)


class CourseNoteSerializer(serializers.ModelSerializer):
    """Serializer للملاحظات"""
    video_title = serializers.CharField(source='video.title', read_only=True, allow_null=True)
    
    class Meta:
        model = CourseNote
        fields = [
            'id', 'video', 'video_title', 'title', 'content',
            'timestamp', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateCourseNoteSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء ملاحظة"""
    class Meta:
        model = CourseNote
        fields = ['video', 'title', 'content', 'timestamp']
    
    def validate_timestamp(self, value):
        """التحقق من الموضع في الفيديو"""
        if value is not None and value < 0:
            raise serializers.ValidationError("الموضع يجب أن يكون أكبر من أو يساوي 0")
        return value


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer للشهادة"""
    student_name = serializers.CharField(source='enrollment.student.user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='enrollment.course.title', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_number', 'student_name', 'course_title',
            'issued_at', 'certificate_file', 'verification_url', 'final_grade'
        ]
        read_only_fields = [
            'id', 'certificate_number', 'issued_at'
        ]


class LearningStreakSerializer(serializers.ModelSerializer):
    """Serializer لأيام التعلم"""
    class Meta:
        model = LearningStreak
        fields = [
            'id', 'date', 'time_spent', 'videos_watched',
            'notes_added', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EnrollmentStatsSerializer(serializers.Serializer):
    """Serializer لإحصائيات التسجيل"""
    total_enrollments = serializers.IntegerField()
    active_enrollments = serializers.IntegerField()
    completed_enrollments = serializers.IntegerField()
    average_progress = serializers.FloatField()
    total_time_spent = serializers.IntegerField()
    certificates_earned = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
