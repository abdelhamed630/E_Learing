"""
نماذج تطبيق الطلاب
الطالب: يشاهد الكورسات والفيديوهات ويحل الامتحانات فقط
"""
from django.db import models
from django.conf import settings


class Student(models.Model):
    """
    نموذج الطالب
    الصلاحيات:
    - مشاهدة الكورسات والفيديوهات
    - حل الامتحانات فقط
    """
    user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='student_profile',
    verbose_name='المستخدم'
)
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        verbose_name='رقم الهاتف'
    )
    birth_date = models.DateField(
        blank=True, 
        null=True,
        verbose_name='تاريخ الميلاد'
    )
    avatar = models.ImageField(
        upload_to='students/avatars/', 
        blank=True, 
        null=True,
        verbose_name='الصورة الشخصية'
    )
    bio = models.TextField(
        blank=True, 
        null=True,
        verbose_name='نبذة تعريفية'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التسجيل'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )
    
    class Meta:
        verbose_name = 'طالب'
        verbose_name_plural = 'الطلاب'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        """الاسم الكامل للطالب"""
        return self.user.get_full_name() or self.user.username
    
    @property
    def email(self):
        """البريد الإلكتروني"""
        return self.user.email
