"""
نماذج إدارة الحسابات
نظام مستخدمين مخصص مع JWT Authentication
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator


class UserManager(BaseUserManager):
    """مدير مخصص لنموذج المستخدم"""
    
    def create_user(self, email, password=None, **extra_fields):
        """إنشاء مستخدم عادي"""
        if not email:
            raise ValueError('يجب إدخال البريد الإلكتروني')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """إنشاء مستخدم خارق (Admin)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """نموذج المستخدم المخصص"""
    
    ROLE_CHOICES = [
        ('student', 'طالب'),
        ('instructor', 'مدرس'),
        ('admin', 'مدير'),
    ]
    
    # استخدام Email كـ Username
    username = models.CharField(max_length=150, unique=True, verbose_name='اسم المستخدم')
    email = models.EmailField(unique=True, verbose_name='البريد الإلكتروني')
    
    # معلومات شخصية
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="رقم الهاتف يجب أن يكون بالصيغة: '+999999999'. حتى 15 رقم."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        verbose_name='رقم الهاتف'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='الصورة الشخصية'
    )
    
    bio = models.TextField(blank=True, null=True, verbose_name='نبذة تعريفية')
    
    # الدور
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        verbose_name='الدور'
    )
    
    # حالة الحساب
    is_verified = models.BooleanField(default=False, verbose_name='موثق')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التسجيل')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='آخر تسجيل دخول')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """الاسم الكامل"""
        return self.get_full_name() or self.username
    
    def is_student(self):
        """التحقق من أن المستخدم طالب"""
        return self.role == 'student'
    
    def is_instructor(self):
        """التحقق من أن المستخدم مدرس"""
        return self.role == 'instructor'
    
    def is_admin_user(self):
        """التحقق من أن المستخدم مدير"""
        return self.role == 'admin' or self.is_superuser


class Profile(models.Model):
    """ملف تعريفي موسع للمستخدم"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='المستخدم'
    )
    
    # معلومات إضافية
    birth_date = models.DateField(blank=True, null=True, verbose_name='تاريخ الميلاد')
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'ذكر'), ('female', 'أنثى')],
        blank=True,
        null=True,
        verbose_name='النوع'
    )
    
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name='البلد')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='المدينة')
    address = models.TextField(blank=True, null=True, verbose_name='العنوان')
    
    # روابط التواصل الاجتماعي
    facebook_url = models.URLField(blank=True, null=True, verbose_name='فيسبوك')
    twitter_url = models.URLField(blank=True, null=True, verbose_name='تويتر')
    linkedin_url = models.URLField(blank=True, null=True, verbose_name='لينكد إن')
    website_url = models.URLField(blank=True, null=True, verbose_name='الموقع الشخصي')
    
    # إعدادات الخصوصية
    show_email = models.BooleanField(default=False, verbose_name='إظهار البريد الإلكتروني')
    show_phone = models.BooleanField(default=False, verbose_name='إظهار رقم الهاتف')
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        verbose_name = 'ملف تعريفي'
        verbose_name_plural = 'الملفات التعريفية'
    
    def __str__(self):
        return f"Profile - {self.user.email}"


class EmailVerification(models.Model):
    """توثيق البريد الإلكتروني"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name='المستخدم'
    )
    token = models.CharField(max_length=100, unique=True, verbose_name='الرمز')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    expires_at = models.DateTimeField(verbose_name='تاريخ الانتهاء')
    is_used = models.BooleanField(default=False, verbose_name='مستخدم')
    
    class Meta:
        verbose_name = 'توثيق بريد إلكتروني'
        verbose_name_plural = 'توثيقات البريد الإلكتروني'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.token[:10]}"
    
    def is_valid(self):
        """التحقق من صلاحية الرمز"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at


class PasswordReset(models.Model):
    """إعادة تعيين كلمة المرور"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_resets',
        verbose_name='المستخدم'
    )
    token = models.CharField(max_length=100, unique=True, verbose_name='الرمز')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    expires_at = models.DateTimeField(verbose_name='تاريخ الانتهاء')
    is_used = models.BooleanField(default=False, verbose_name='مستخدم')
    
    class Meta:
        verbose_name = 'إعادة تعيين كلمة مرور'
        verbose_name_plural = 'إعادة تعيين كلمات المرور'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.token[:10]}"
    
    def is_valid(self):
        """التحقق من صلاحية الرمز"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at


class LoginHistory(models.Model):
    """سجل تسجيلات الدخول"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name='المستخدم'
    )
    ip_address = models.GenericIPAddressField(verbose_name='عنوان IP')
    user_agent = models.TextField(blank=True, null=True, verbose_name='متصفح المستخدم')
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name='الموقع')
    is_successful = models.BooleanField(default=True, verbose_name='نجح')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')
    
    class Meta:
        verbose_name = 'سجل تسجيل دخول'
        verbose_name_plural = 'سجلات تسجيل الدخول'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"
