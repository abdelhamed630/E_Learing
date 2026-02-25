"""
Admin للمدفوعات
"""
from django.contrib import admin
from .models import Payment, Coupon, CouponUsage, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'student', 'course', 'amount',
        'payment_method', 'status', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = [
        'transaction_id', 'student__user__username',
        'student__user__email', 'course__title'
    ]
    readonly_fields = [
        'transaction_id', 'created_at', 'completed_at', 'refunded_at'
    ]

    fieldsets = (
        ('معلومات الدفعة', {
            'fields': ('transaction_id', 'student', 'course')
        }),
        ('المبلغ', {
            'fields': ('amount', 'currency')
        }),
        ('طريقة الدفع', {
            'fields': ('payment_method', 'status')
        }),
        ('بوابة الدفع', {
            'fields': ('gateway_transaction_id', 'gateway_response')
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'completed_at', 'refunded_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_type', 'discount_value',
        'is_active', 'valid_from', 'valid_until',
        'current_uses', 'max_uses'
    ]
    list_filter = ['is_active', 'discount_type', 'created_at']
    search_fields = ['code', 'description']
    filter_horizontal = ['courses']

    fieldsets = (
        ('معلومات الكوبون', {
            'fields': ('code', 'description')
        }),
        ('الخصم', {
            'fields': ('discount_type', 'discount_value', 'minimum_purchase')
        }),
        ('الصلاحية', {
            'fields': ('is_active', 'valid_from', 'valid_until')
        }),
        ('حدود الاستخدام', {
            'fields': ('max_uses', 'max_uses_per_user', 'current_uses')
        }),
        ('الكورسات', {
            'fields': ('courses',),
            'description': 'اترك فارغاً للسماح باستخدام الكوبون على جميع الكورسات'
        }),
    )


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'student', 'payment', 'discount_amount', 'used_at']
    list_filter = ['used_at']
    search_fields = [
        'coupon__code', 'student__user__username',
        'payment__transaction_id'
    ]
    readonly_fields = ['used_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'student', 'status',
        'refund_amount', 'requested_at'
    ]
    list_filter = ['status', 'requested_at']
    search_fields = [
        'payment__transaction_id',
        'student__user__username',
        'reason'
    ]
    readonly_fields = ['requested_at', 'reviewed_at', 'completed_at']

    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('payment', 'student', 'reason')
        }),
        ('الحالة', {
            'fields': ('status', 'refund_amount')
        }),
        ('ملاحظات الإدارة', {
            'fields': ('admin_notes',)
        }),
        ('التواريخ', {
            'fields': ('requested_at', 'reviewed_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_refunds', 'reject_refunds']

    def approve_refunds(self, request, queryset):
        for refund in queryset.filter(status='pending'):
            refund.approve()
        self.message_user(request, f'تمت الموافقة على {queryset.count()} طلب')

    approve_refunds.short_description = 'الموافقة على الطلبات المحددة'

    def reject_refunds(self, request, queryset):
        for refund in queryset.filter(status='pending'):
            refund.reject('تم الرفض من لوحة الإدارة')
        self.message_user(request, f'تم رفض {queryset.count()} طلب')

    reject_refunds.short_description = 'رفض الطلبات المحددة'
