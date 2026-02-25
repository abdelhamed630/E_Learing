"""
Views للمدفوعات
الطالب: يدفع ويشوف مدفوعاته فقط
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg, Count
from django.db import transaction

from students.permissions import IsStudent
from courses.models import Course
from enrollments.models import Enrollment

from .models import Payment, Coupon, CouponUsage, Refund
from .serializers import (
    PaymentSerializer, CreatePaymentSerializer,
    CouponSerializer, ValidateCouponSerializer,
    CouponUsageSerializer, RefundSerializer,
    CreateRefundSerializer, PaymentStatsSerializer
)
from .tasks import process_payment, send_payment_receipt


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للمدفوعات
    الطالب: يشوف مدفوعاته فقط
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        """الطالب يشوف مدفوعاته فقط"""
        student = self.request.user.student_profile
        return Payment.objects.filter(student=student).select_related(
            'student__user', 'course'
        ).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """
        إنشاء دفعة جديدة
        """
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = request.user.student_profile
        course_id = serializer.validated_data['course_id']
        payment_method = serializer.validated_data['payment_method']
        coupon_code = serializer.validated_data.get('coupon_code')

        # التحقق من الكورس
        try:
            course = Course.objects.get(id=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {'error': 'الكورس غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )

        # التحقق من عدم التسجيل المسبق
        if Enrollment.objects.filter(student=student, course=course).exists():
            return Response(
                {'error': 'أنت مسجل بالفعل في هذا الكورس'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # حساب المبلغ
        amount = course.final_price
        discount_amount = 0
        coupon = None

        # تطبيق الكوبون إن وجد
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                can_use, message = coupon.can_be_used_by(student, course)

                if not can_use:
                    return Response(
                        {'error': message},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # التحقق من الحد الأدنى للشراء
                if amount < coupon.minimum_purchase:
                    return Response(
                        {'error': f'الحد الأدنى للشراء {coupon.minimum_purchase} EGP'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                discount_amount = coupon.calculate_discount(amount)
                amount -= discount_amount

            except Coupon.DoesNotExist:
                return Response(
                    {'error': 'الكوبون غير موجود'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # إنشاء الدفعة
        with transaction.atomic():
            payment = Payment.objects.create(
                student=student,
                course=course,
                amount=amount,
                payment_method=payment_method,
                status='pending'
            )

            # حفظ استخدام الكوبون
            if coupon and discount_amount > 0:
                CouponUsage.objects.create(
                    coupon=coupon,
                    student=student,
                    payment=payment,
                    discount_amount=discount_amount
                )
                # زيادة عداد الاستخدام
                coupon.current_uses += 1
                coupon.save(update_fields=['current_uses'])

        # معالجة الدفع في الخلفية
        process_payment.delay(payment.id)

        return Response({
            'message': 'تم إنشاء الدفعة بنجاح',
            'payment': PaymentSerializer(payment).data,
            'payment_url': f'/api/payments/process/{payment.transaction_id}/'
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def successful(self, request):
        """المدفوعات الناجحة"""
        student = request.user.student_profile
        payments = Payment.objects.filter(
            student=student,
            status='completed'
        ).select_related('course')

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات المدفوعات"""
        student = request.user.student_profile

        payments = Payment.objects.filter(student=student)

        stats = {
            'total_payments': payments.count(),
            'successful_payments': payments.filter(status='completed').count(),
            'failed_payments': payments.filter(status='failed').count(),
            'total_amount': payments.filter(
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_refunded': payments.filter(
                status='refunded'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_payment': payments.filter(
                status='completed'
            ).aggregate(Avg('amount'))['amount__avg'] or 0,
        }

        serializer = PaymentStatsSerializer(stats)
        return Response(serializer.data)


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للكوبونات
    الطالب: التحقق من الكوبون فقط
    """
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    queryset = Coupon.objects.filter(is_active=True)

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """التحقق من صلاحية الكوبون"""
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        coupon_code = serializer.validated_data['coupon_code']
        course_id = serializer.validated_data['course_id']
        student = request.user.student_profile

        try:
            coupon = Coupon.objects.get(code=coupon_code)
            course = Course.objects.get(id=course_id)

            can_use, message = coupon.can_be_used_by(student, course)

            if not can_use:
                return Response({
                    'valid': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)

            # حساب الخصم
            original_price = course.final_price
            discount = coupon.calculate_discount(original_price)
            final_price = original_price - discount

            return Response({
                'valid': True,
                'message': 'الكوبون صالح للاستخدام',
                'coupon': CouponSerializer(coupon).data,
                'original_price': original_price,
                'discount': discount,
                'final_price': final_price
            })

        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'الكوبون غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)
        except Course.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'الكورس غير موجود'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def my_usages(self, request):
        """سجل استخدامات الكوبونات"""
        student = request.user.student_profile
        usages = CouponUsage.objects.filter(
            student=student
        ).select_related('coupon', 'payment__course')

        serializer = CouponUsageSerializer(usages, many=True)
        return Response(serializer.data)


class RefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet لطلبات الاسترجاع
    الطالب: يطلب استرجاع ويشوف طلباته
    """
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        """الطالب يشوف طلباته فقط"""
        student = self.request.user.student_profile
        return Refund.objects.filter(student=student).select_related(
            'payment__course'
        ).order_by('-requested_at')

    @action(detail=False, methods=['post'])
    def request_refund(self, request):
        """طلب استرجاع"""
        serializer = CreateRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student = request.user.student_profile
        payment_id = serializer.validated_data['payment_id']
        reason = serializer.validated_data['reason']

        # التحقق من الدفعة
        try:
            payment = Payment.objects.get(
                id=payment_id,
                student=student
            )
        except Payment.DoesNotExist:
            return Response(
                {'error': 'الدفعة غير موجودة'},
                status=status.HTTP_404_NOT_FOUND
            )

        # التحقق من إمكانية الاسترجاع
        if not payment.can_be_refunded:
            return Response(
                {'error': 'لا يمكن استرجاع هذه الدفعة'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # التحقق من عدم وجود طلب سابق
        if Refund.objects.filter(payment=payment).exists():
            return Response(
                {'error': 'يوجد طلب استرجاع سابق لهذه الدفعة'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # إنشاء الطلب
        refund = Refund.objects.create(
            payment=payment,
            student=student,
            reason=reason,
            refund_amount=payment.amount
        )

        return Response({
            'message': 'تم إرسال طلب الاسترجاع بنجاح',
            'refund': RefundSerializer(refund).data
        }, status=status.HTTP_201_CREATED)
