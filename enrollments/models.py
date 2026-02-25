"""
نماذج التسجيل في الكورسات وتتبع التقدم
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Enrollment(models.Model):
    """تسجيل الطالب في الكورس"""
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('dropped', 'منسحب'),
        ('expired', 'منتهي'),
    ]
    
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='الطالب'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='الكورس'
    )
    
    # حالة التسجيل
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='الحالة'
    )
    
    # التقدم
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='نسبة الإنجاز %',
        help_text='من 0 إلى 100'
    )
    
    # الوقت المستغرق (بالدقائق)
    total_time_spent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='الوقت المستغرق (دقائق)'
    )
    
    # الشهادة
    certificate_issued = models.BooleanField(
        default=False,
        verbose_name='تم إصدار الشهادة'
    )
    certificate_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='رابط الشهادة'
    )
    
    # التواريخ
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التسجيل'
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ البدء'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الإكمال'
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الانتهاء'
    )
    last_accessed = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر وصول'
    )
    
    class Meta:
        verbose_name = 'تسجيل'
        verbose_name_plural = 'التسجيلات'
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['course', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.user.username} - {self.course.title}"
    
    def mark_as_started(self):
        """تحديد بداية الكورس"""
        if not self.started_at:
            self.started_at = timezone.now()
            self.save(update_fields=['started_at'])
    
    def mark_as_completed(self):
        """تحديد إكمال الكورس"""
        if not self.completed_at:
            self.status = 'completed'
            self.progress = 100
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'progress', 'completed_at'])
    
    @property
    def is_active(self):
        """التحقق من أن التسجيل نشط"""
        return self.status == 'active'
    
    @property
    def is_completed(self):
        """التحقق من إكمال الكورس"""
        return self.status == 'completed'
    
    @property
    def days_since_enrollment(self):
        """عدد الأيام منذ التسجيل"""
        delta = timezone.now() - self.enrolled_at
        return delta.days


class VideoProgress(models.Model):
    """تتبع تقدم الطالب في مشاهدة الفيديوهات"""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name='الطالب'
    )
    video = models.ForeignKey(
        'courses.Video',
        on_delete=models.CASCADE,
        related_name='student_progress',
        verbose_name='الفيديو'
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name='التسجيل'
    )
    
    # التقدم
    watched_duration = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='المدة المشاهدة (ثواني)',
        help_text='المدة التي شاهدها الطالب بالثواني'
    )
    
    last_position = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='آخر موضع (ثواني)',
        help_text='آخر موضع وصل إليه الطالب'
    )
    
    completed = models.BooleanField(
        default=False,
        verbose_name='مكتمل'
    )
    
    # عدد المشاهدات
    view_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='عدد المشاهدات'
    )
    
    # التواريخ
    first_watched = models.DateTimeField(
        auto_now_add=True,
        verbose_name='أول مشاهدة'
    )
    last_watched = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر مشاهدة'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الإكمال'
    )
    
    class Meta:
        verbose_name = 'تقدم فيديو'
        verbose_name_plural = 'تقدم الفيديوهات'
        unique_together = ['student', 'video']
        ordering = ['-last_watched']
        indexes = [
            models.Index(fields=['student', 'completed']),
            models.Index(fields=['enrollment', 'completed']),
        ]
    
    def __str__(self):
        return f"{self.student.user.username} - {self.video.title}"
    
    @property
    def completion_percentage(self):
        """نسبة الإنجاز"""
        if self.video.duration > 0:
            return min(100, int((self.watched_duration / self.video.duration) * 100))
        return 0
    
    def mark_as_completed(self):
        """تحديد إكمال الفيديو"""
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.watched_duration = self.video.duration
            self.save(update_fields=['completed', 'completed_at', 'watched_duration'])


class CourseNote(models.Model):
    """ملاحظات الطالب على الكورس"""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='course_notes',
        verbose_name='الطالب'
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='التسجيل'
    )
    video = models.ForeignKey(
        'courses.Video',
        on_delete=models.CASCADE,
        related_name='student_notes',
        blank=True,
        null=True,
        verbose_name='الفيديو'
    )
    
    # المحتوى
    title = models.CharField(
        max_length=200,
        verbose_name='العنوان'
    )
    content = models.TextField(
        verbose_name='المحتوى'
    )
    
    # الموضع في الفيديو (إذا كان مرتبط بفيديو)
    timestamp = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='الموضع (ثواني)',
        help_text='موضع الملاحظة في الفيديو'
    )
    
    # التواريخ
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )
    
    class Meta:
        verbose_name = 'ملاحظة'
        verbose_name_plural = 'الملاحظات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.user.username} - {self.title}"


class Certificate(models.Model):
    """شهادة إتمام الكورس"""
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='certificate',
        verbose_name='التسجيل'
    )
    
    # معلومات الشهادة
    certificate_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم الشهادة'
    )
    
    issued_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإصدار'
    )
    
    # الملف
    certificate_file = models.FileField(
        upload_to='certificates/',
        blank=True,
        null=True,
        verbose_name='ملف الشهادة'
    )
    
    # رابط التحقق
    verification_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='رابط التحقق'
    )
    
    # الدرجة النهائية
    final_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='الدرجة النهائية'
    )
    
    class Meta:
        verbose_name = 'شهادة'
        verbose_name_plural = 'الشهادات'
        ordering = ['-issued_at']
    
    def __str__(self):
        return f"شهادة #{self.certificate_number} - {self.enrollment.student.user.username}"


class LearningStreak(models.Model):
    """سجل التعلم المتواصل للطالب"""
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='learning_streaks',
        verbose_name='الطالب'
    )
    
    date = models.DateField(
        verbose_name='التاريخ'
    )
    
    # الوقت المستغرق في هذا اليوم (بالدقائق)
    time_spent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='الوقت المستغرق (دقائق)'
    )
    
    # عدد الفيديوهات المشاهدة
    videos_watched = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='الفيديوهات المشاهدة'
    )
    
    # عدد الملاحظات المضافة
    notes_added = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='الملاحظات المضافة'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    
    class Meta:
        verbose_name = 'يوم تعلم'
        verbose_name_plural = 'أيام التعلم'
        unique_together = ['student', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.user.username} - {self.date}"
