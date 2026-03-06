"""
نماذج الكورسات والفيديوهات
"""
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Category(models.Model):
    """تصنيف الكورسات"""
    name = models.CharField(max_length=100, unique=True, verbose_name='اسم التصنيف')
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name='الرابط')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name='أيقونة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'تصنيف'
        verbose_name_plural = 'التصنيفات'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """الكورس التعليمي"""
    LEVEL_CHOICES = [
        ('beginner', 'مبتدئ'),
        ('intermediate', 'متوسط'),
        ('advanced', 'متقدم'),
    ]
    
    LANGUAGE_CHOICES = [
        ('ar', 'عربي'),
        ('en', 'إنجليزي'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='عنوان الكورس')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='الرابط')
    description = models.TextField(verbose_name='وصف الكورس')
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='courses',
        verbose_name='التصنيف'
    )
    instructor = models.ForeignKey(
    settings.AUTH_USER_MODEL,  
    on_delete=models.CASCADE,
    related_name='courses_taught',
    verbose_name='المدرس'
)
    
    # معلومات الكورس
    thumbnail = models.ImageField(
        upload_to='courses/thumbnails/', 
        blank=True, 
        null=True,
        verbose_name='صورة الكورس'
    )
    trailer_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name='رابط الفيديو التعريفي'
    )
    level = models.CharField(
        max_length=20, 
        choices=LEVEL_CHOICES, 
        default='beginner',
        verbose_name='المستوى'
    )
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default='ar',
        verbose_name='اللغة'
    )
    
    # السعر والنشر
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='السعر'
    )
    discount_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='السعر بعد الخصم'
    )
    is_published = models.BooleanField(default=False, verbose_name='منشور')
    is_featured = models.BooleanField(default=False, verbose_name='مميز')
    
    # المدة والمتطلبات
    duration_hours = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='المدة بالساعات'
    )
    requirements = models.TextField(
        blank=True, 
        null=True,
        verbose_name='المتطلبات'
    )
    what_will_learn = models.TextField(
        blank=True, 
        null=True,
        verbose_name='ما سيتعلمه الطالب'
    )
    
    # إحصائيات
    views_count = models.IntegerField(default=0, verbose_name='عدد المشاهدات')
    students_count = models.IntegerField(default=0, verbose_name='عدد الطلاب')
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='التقييم'
    )
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        verbose_name = 'كورس'
        verbose_name_plural = 'الكورسات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_published']),
            models.Index(fields=['category']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    @property
    def final_price(self):
        """السعر النهائي بعد الخصم"""
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price
    
    @property
    def discount_percentage(self):
        """نسبة الخصم"""
        if self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0
    
    @property
    def total_videos(self):
        """إجمالي عدد الفيديوهات"""
        return self.videos.count()
    
    @property
    def total_duration(self):
        """إجمالي مدة الكورس بالدقائق"""
        total = self.videos.aggregate(models.Sum('duration'))['duration__sum'] or 0
        return total


class Section(models.Model):
    """قسم داخل الكورس"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name='الكورس'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان القسم')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    order = models.IntegerField(default=0, verbose_name='الترتيب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'قسم'
        verbose_name_plural = 'الأقسام'
        ordering = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def total_duration(self):
        """إجمالي مدة الفيديوهات في القسم بالثواني"""
        from django.db.models import Sum
        return self.videos.aggregate(Sum('duration'))['duration__sum'] or 0


class Video(models.Model):
    """فيديو تعليمي"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='الكورس'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='videos',
        null=True,
        blank=True,
        verbose_name='القسم'
    )
    
    title = models.CharField(max_length=200, verbose_name='عنوان الفيديو')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    video_file = models.FileField(
        upload_to='videos/files/',
        blank=True,
        null=True,
        verbose_name='ملف الفيديو'
    )
    video_url = models.URLField(blank=True, null=True, verbose_name='رابط الفيديو')
    thumbnail = models.ImageField(
        upload_to='videos/thumbnails/',
        blank=True,
        null=True,
        verbose_name='صورة مصغرة'
    )
    
    duration = models.IntegerField(
        help_text='المدة بالثواني',
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='مدة الفيديو'
    )
    order = models.IntegerField(default=0, verbose_name='الترتيب')
    is_free = models.BooleanField(default=False, verbose_name='مجاني')
    is_downloadable = models.BooleanField(default=False, verbose_name='قابل للتحميل')
    
    views_count = models.IntegerField(default=0, verbose_name='عدد المشاهدات')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        verbose_name = 'فيديو'
        verbose_name_plural = 'الفيديوهات'
        ordering = ['course', 'section', 'order']
        indexes = [
            models.Index(fields=['course', 'order']),
        ]
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def duration_formatted(self):
        """المدة بصيغة منسقة (HH:MM:SS)"""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class Attachment(models.Model):
    """ملف مرفق للفيديو"""
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='الفيديو'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان الملف')
    file = models.FileField(upload_to='videos/attachments/', verbose_name='الملف')
    file_size = models.IntegerField(default=0, verbose_name='حجم الملف (بايت)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    
    class Meta:
        verbose_name = 'ملف مرفق'
        verbose_name_plural = 'الملفات المرفقة'
        ordering = ['video', 'created_at']
    
    def __str__(self):
        return self.title


class CourseReview(models.Model):
    """تقييم الكورس"""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='الكورس'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='course_reviews',
        verbose_name='الطالب'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='التقييم'
    )
    comment = models.TextField(blank=True, null=True, verbose_name='التعليق')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التقييم')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        verbose_name = 'تقييم كورس'
        verbose_name_plural = 'تقييمات الكورسات'
        unique_together = ['course', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student} - {self.course.title} ({self.rating}⭐)"
