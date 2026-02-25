"""
نماذج الإشعارات
نظام إشعارات داخل التطبيق + إيميل
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Notification(models.Model):
    """نموذج الإشعار"""
    
    NOTIFICATION_TYPES = [
        ('course_enrolled', 'تسجيل في كورس'),
        ('course_completed', 'إكمال كورس'),
        ('exam_result', 'نتيجة امتحان'),
        ('payment_success', 'دفع ناجح'),
        ('payment_failed', 'دفع فاشل'),
        ('refund_approved', 'موافقة على استرجاع'),
        ('refund_rejected', 'رفض استرجاع'),
        ('new_course', 'كورس جديد'),
        ('course_update', 'تحديث كورس'),
        ('announcement', 'إعلان'),
        ('reminder', 'تذكير'),
        ('system', 'نظام'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='المستخدم'
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        verbose_name='نوع الإشعار'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='العنوان'
    )
    message = models.TextField(
        verbose_name='الرسالة'
    )
    
    # روابط اختيارية
    link = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='الرابط'
    )
    
    # بيانات إضافية (JSON)
    data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='بيانات إضافية'
    )
    
    # الحالة
    is_read = models.BooleanField(
        default=False,
        verbose_name='مقروء'
    )
    read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='وقت القراءة'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(cls, user, notification_type, title, message, link=None, data=None):
        """إنشاء إشعار جديد"""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            data=data
        )


class NotificationPreference(models.Model):
    """تفضيلات الإشعارات للمستخدم"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preference',
        verbose_name='المستخدم'
    )
    
    # إشعارات داخل التطبيق
    enable_in_app = models.BooleanField(
        default=True,
        verbose_name='تفعيل إشعارات التطبيق'
    )
    
    # إشعارات البريد الإلكتروني
    enable_email = models.BooleanField(
        default=True,
        verbose_name='تفعيل إشعارات البريد'
    )
    
    # أنواع الإشعارات
    notify_course_updates = models.BooleanField(
        default=True,
        verbose_name='تحديثات الكورسات'
    )
    notify_exam_results = models.BooleanField(
        default=True,
        verbose_name='نتائج الامتحانات'
    )
    notify_payments = models.BooleanField(
        default=True,
        verbose_name='المدفوعات'
    )
    notify_announcements = models.BooleanField(
        default=True,
        verbose_name='الإعلانات'
    )
    notify_reminders = models.BooleanField(
        default=True,
        verbose_name='التذكيرات'
    )
    
    # إعدادات إضافية
    email_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'فوري'),
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
        ],
        default='instant',
        verbose_name='تكرار إرسال الإيميل'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'تفضيلات الإشعارات'
        verbose_name_plural = 'تفضيلات الإشعارات'

    def __str__(self):
        return f"تفضيلات {self.user.username}"


class Announcement(models.Model):
    """الإعلانات العامة"""
    
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    TARGET_CHOICES = [
        ('all', 'الجميع'),
        ('students', 'الطلاب فقط'),
        ('instructors', 'المدرسين فقط'),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name='العنوان'
    )
    content = models.TextField(
        verbose_name='المحتوى'
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='الأولوية'
    )
    
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default='all',
        verbose_name='الفئة المستهدفة'
    )
    
    # النشر
    is_published = models.BooleanField(
        default=False,
        verbose_name='منشور'
    )
    publish_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='موعد النشر'
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='موعد الانتهاء'
    )
    
    # إرسال إشعار
    send_notification = models.BooleanField(
        default=True,
        verbose_name='إرسال إشعار'
    )
    send_email = models.BooleanField(
        default=False,
        verbose_name='إرسال إيميل'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='announcements_created',
        verbose_name='أنشأ بواسطة'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'إعلان'
        verbose_name_plural = 'الإعلانات'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_active(self):
        """التحقق من أن الإعلان نشط"""
        now = timezone.now()
        if not self.is_published:
            return False
        if self.publish_at and now < self.publish_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True

    def get_target_users(self):
        """الحصول على المستخدمين المستهدفين"""
        if self.target_audience == 'all':
            return User.objects.filter(is_active=True)
        elif self.target_audience == 'students':
            return User.objects.filter(is_active=True, role='student')
        elif self.target_audience == 'instructors':
            return User.objects.filter(is_active=True, role='instructor')
        return User.objects.none()


class EmailLog(models.Model):
    """سجل الإيميلات المرسلة"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_logs',
        verbose_name='المستخدم'
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name='الموضوع'
    )
    message = models.TextField(
        verbose_name='الرسالة'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='رسالة الخطأ'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الإرسال'
    )

    class Meta:
        verbose_name = 'سجل إيميل'
        verbose_name_plural = 'سجل الإيميلات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.subject}"
