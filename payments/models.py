"""
نماذج المدفوعات
الطالب: يدفع فقط - لا يعدل ولا يحذف
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

User = get_user_model()


class Payment(models.Model):
    """نموذج الدفعة"""
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('completed', 'مكتملة'),
        ('failed', 'فاشلة'),
        ('refunded', 'مسترجعة'),
        ('cancelled', 'ملغاة'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'بطاقة ائتمان'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('fawry', 'فوري'),
        ('vodafone_cash', 'فودافون كاش'),
        ('bank_transfer', 'تحويل بنكي'),
    ]

    # معلومات أساسية
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        verbose_name='رقم المعاملة'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='الطالب'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='الكورس'
    )

    # المبلغ
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='المبلغ'
    )
    currency = models.CharField(
        max_length=3,
        default='EGP',
        verbose_name='العملة'
    )

    # طريقة الدفع والحالة
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='طريقة الدفع'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )

    # معلومات إضافية من بوابة الدفع
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='رقم المعاملة من البوابة'
    )
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name='استجابة البوابة'
    )

    # ملاحظات
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات'
    )

    # التواريخ
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الإتمام'
    )
    refunded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الاسترجاع'
    )

    class Meta:
        verbose_name = 'دفعة'
        verbose_name_plural = 'المدفوعات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_id} - {self.student.user.username} - {self.amount} {self.currency}"

    @staticmethod
    def generate_transaction_id():
        """توليد رقم معاملة فريد"""
        return f"PAY-{uuid.uuid4().hex[:12].upper()}"

    def mark_as_completed(self):
        """تحديد الدفعة كمكتملة"""
        if self.status == 'pending':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])

    def mark_as_failed(self, reason=None):
        """تحديد الدفعة كفاشلة"""
        if self.status == 'pending':
            self.status = 'failed'
            if reason:
                self.notes = reason
            self.save(update_fields=['status', 'notes'])

    def mark_as_refunded(self):
        """تحديد الدفعة كمستردة"""
        if self.status == 'completed':
            self.status = 'refunded'
            self.refunded_at = timezone.now()
            self.save(update_fields=['status', 'refunded_at'])

    @property
    def is_successful(self):
        """التحقق من نجاح الدفعة"""
        return self.status == 'completed'

    @property
    def can_be_refunded(self):
        """التحقق من إمكانية الاسترجاع"""
        if self.status != 'completed':
            return False
        # يمكن الاسترجاع خلال 30 يوم
        if self.completed_at:
            from datetime import timedelta
            return timezone.now() - self.completed_at <= timedelta(days=30)
        return False


class Coupon(models.Model):
    """كوبون خصم"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'نسبة مئوية'),
        ('fixed', 'مبلغ ثابت'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='كود الكوبون'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='الوصف'
    )

    # نوع الخصم
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name='نوع الخصم'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='قيمة الخصم'
    )

    # حد أدنى للشراء
    minimum_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='الحد الأدنى للشراء'
    )

    # الصلاحية
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    valid_from = models.DateTimeField(
        verbose_name='صالح من'
    )
    valid_until = models.DateTimeField(
        verbose_name='صالح حتى'
    )

    # حدود الاستخدام
    max_uses = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='عدد مرات الاستخدام الأقصى'
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        verbose_name='عدد مرات الاستخدام لكل مستخدم'
    )
    current_uses = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد مرات الاستخدام الحالية'
    )

    # تحديد الكورسات (اختياري)
    courses = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='coupons',
        verbose_name='الكورسات المحددة'
    )
    # إذا كان فارغ = يصلح لجميع الكورسات

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'كوبون خصم'
        verbose_name_plural = 'كوبونات الخصم'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else ' EGP'}"

    def is_valid(self):
        """التحقق من صلاحية الكوبون"""
        now = timezone.now()
        if not self.is_active:
            return False, 'الكوبون غير نشط'
        if now < self.valid_from:
            return False, 'الكوبون لم يبدأ بعد'
        if now > self.valid_until:
            return False, 'الكوبون منتهي الصلاحية'
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, 'تم استهلاك جميع مرات استخدام الكوبون'
        return True, 'الكوبون صالح'

    def can_be_used_by(self, student, course):
        """التحقق من إمكانية استخدام الكوبون"""
        # التحقق من صلاحية الكوبون
        is_valid, message = self.is_valid()
        if not is_valid:
            return False, message

        # التحقق من عدد مرات استخدام المستخدم
        user_uses = CouponUsage.objects.filter(
            coupon=self,
            student=student
        ).count()
        if user_uses >= self.max_uses_per_user:
            return False, 'لقد استخدمت هذا الكوبون الحد الأقصى من المرات'

        # التحقق من الكورس المحدد
        if self.courses.exists() and course not in self.courses.all():
            return False, 'هذا الكوبون غير صالح لهذا الكورس'

        return True, 'يمكن استخدام الكوبون'

    def calculate_discount(self, amount):
        """حساب قيمة الخصم"""
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
        else:
            discount = self.discount_value

        # التأكد من أن الخصم لا يتجاوز المبلغ
        return min(discount, amount)


class CouponUsage(models.Model):
    """سجل استخدام الكوبونات"""
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='الكوبون'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name='الطالب'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='coupon_usage',
        verbose_name='الدفعة'
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='مبلغ الخصم'
    )
    used_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الاستخدام'
    )

    class Meta:
        verbose_name = 'استخدام كوبون'
        verbose_name_plural = 'استخدامات الكوبونات'
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.student.user.username} - {self.coupon.code} - {self.discount_amount}"


class Refund(models.Model):
    """طلب استرجاع"""
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('completed', 'مكتمل'),
    ]

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='refund',
        verbose_name='الدفعة'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='refund_requests',
        verbose_name='الطالب'
    )

    reason = models.TextField(verbose_name='سبب الاسترجاع')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )

    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='المبلغ المسترجع'
    )

    # ملاحظات الإدارة
    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات الإدارة'
    )

    # التواريخ
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الطلب'
    )
    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ المراجعة'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الإتمام'
    )

    class Meta:
        verbose_name = 'طلب استرجاع'
        verbose_name_plural = 'طلبات الاسترجاع'
        ordering = ['-requested_at']

    def __str__(self):
        return f"طلب استرجاع - {self.payment.transaction_id}"

    def approve(self, admin_notes=None):
        """الموافقة على طلب الاسترجاع"""
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()

    def reject(self, admin_notes):
        """رفض طلب الاسترجاع"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()

    def complete(self):
        """إتمام الاسترجاع"""
        if self.status == 'approved':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            # تحديث حالة الدفعة
            self.payment.mark_as_refunded()
