"""
Serializers للمدفوعات
"""
from rest_framework import serializers
from .models import Payment, Coupon, CouponUsage, Refund


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer للدفعة"""
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    is_successful = serializers.BooleanField(source='is_successful', read_only=True)
    can_be_refunded = serializers.BooleanField(source='can_be_refunded', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'student_name', 'course_title',
            'amount', 'currency', 'payment_method', 'status',
            'is_successful', 'can_be_refunded',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'status',
            'created_at', 'completed_at'
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer لإنشاء دفعة"""
    course_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        required=True
    )
    coupon_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50
    )


class CouponSerializer(serializers.ModelSerializer):
    """Serializer للكوبون"""
    discount_display = serializers.SerializerMethodField()
    is_valid_now = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type',
            'discount_value', 'discount_display', 'minimum_purchase',
            'is_active', 'valid_from', 'valid_until',
            'max_uses', 'current_uses', 'is_valid_now'
        ]
        read_only_fields = ['id', 'current_uses']

    def get_discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        return f"{obj.discount_value} EGP"

    def get_is_valid_now(self, obj):
        is_valid, _ = obj.is_valid()
        return is_valid


class ValidateCouponSerializer(serializers.Serializer):
    """Serializer للتحقق من الكوبون"""
    coupon_code = serializers.CharField(required=True)
    course_id = serializers.IntegerField(required=True)


class CouponUsageSerializer(serializers.ModelSerializer):
    """Serializer لسجل استخدام الكوبون"""
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    course_title = serializers.CharField(source='payment.course.title', read_only=True)

    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon_code', 'course_title',
            'discount_amount', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


class RefundSerializer(serializers.ModelSerializer):
    """Serializer لطلب الاسترجاع"""
    payment_transaction = serializers.CharField(
        source='payment.transaction_id',
        read_only=True
    )
    course_title = serializers.CharField(
        source='payment.course.title',
        read_only=True
    )

    class Meta:
        model = Refund
        fields = [
            'id', 'payment_transaction', 'course_title',
            'reason', 'status', 'refund_amount',
            'admin_notes', 'requested_at', 'reviewed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'admin_notes',
            'requested_at', 'reviewed_at', 'completed_at'
        ]


class CreateRefundSerializer(serializers.Serializer):
    """Serializer لإنشاء طلب استرجاع"""
    payment_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=True, min_length=10)


class PaymentStatsSerializer(serializers.Serializer):
    """Serializer لإحصائيات المدفوعات"""
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_payment = serializers.DecimalField(max_digits=10, decimal_places=2)
