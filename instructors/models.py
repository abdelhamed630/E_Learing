"""
نموذج المدرب
المدرب يتم إضافته من Admin فقط
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Instructor(models.Model):
    """نموذج المدرب"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='instructor_profile',
        verbose_name='المستخدم',
        limit_choices_to={'role': 'instructor'}  # فقط المستخدمين اللي role=instructor
    )
    
    # معلومات مهنية
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name='نبذة تعريفية'
    )
    specialization = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='التخصص'
    )
    years_of_experience = models.PositiveIntegerField(
        default=0,
        verbose_name='سنوات الخبرة'
    )
    
    # روابط
    website = models.URLField(
        blank=True,
        null=True,
        verbose_name='الموقع الشخصي'
    )
    linkedin = models.URLField(
        blank=True,
        null=True,
        verbose_name='LinkedIn'
    )
    github = models.URLField(
        blank=True,
        null=True,
        verbose_name='GitHub'
    )
    
    # الصورة والملفات
    avatar = models.ImageField(
        upload_to='instructors/avatars/',
        blank=True,
        null=True,
        verbose_name='الصورة الشخصية'
    )
    resume = models.FileField(
        upload_to='instructors/resumes/',
        blank=True,
        null=True,
        verbose_name='السيرة الذاتية'
    )
    
    # الحالة
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='مميز'
    )
    
    # الإحصائيات
    total_courses = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد الكورسات'
    )
    total_students = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد الطلاب'
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='متوسط التقييم'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإضافة'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )
    
    class Meta:
        verbose_name = 'مدرب'
        verbose_name_plural = 'المدربون'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    def update_stats(self):
        """تحديث الإحصائيات"""
        # عدد الكورسات
        self.total_courses = self.user.courses.filter(is_published=True).count()
        
        # عدد الطلاب (من التسجيلات)
        from enrollments.models import Enrollment
        self.total_students = Enrollment.objects.filter(
            course__instructor=self.user
        ).values('student').distinct().count()
        
        # متوسط التقييم
        from courses.models import Course
        from django.db.models import Avg
        avg = self.user.courses.filter(
            is_published=True
        ).aggregate(Avg('rating'))['rating__avg']
        self.average_rating = avg or 0
        
        self.save()
