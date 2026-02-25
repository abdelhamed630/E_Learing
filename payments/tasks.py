"""
Celery Tasks للمدفوعات
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


@shared_task
def process_payment(payment_id):
    """
    معالجة الدفع (محاكاة - يتم استبداله ببوابة دفع حقيقية)
    """
    try:
        from .models import Payment
        from enrollments.models import Enrollment

        payment = Payment.objects.get(id=payment_id)

        # محاكاة معالجة الدفع
        # في الواقع: هنا يتم الاتصال ببوابة الدفع (Stripe, PayPal, إلخ)

        # نفترض النجاح (في الواقع يعتمد على استجابة البوابة)
        payment.mark_as_completed()
        payment.gateway_transaction_id = f"GATEWAY-{payment.transaction_id}"
        payment.gateway_response = {
            'status': 'success',
            'message': 'Payment processed successfully'
        }
        payment.save()

        # إنشاء التسجيل في الكورس
        Enrollment.objects.create(
            student=payment.student,
            course=payment.course,
            status='active'
        )

        # إرسال الإيصال
        send_payment_receipt.delay(payment.id)

        return f'تم معالجة الدفع بنجاح: {payment.transaction_id}'

    except Exception as e:
        # في حالة الفشل
        try:
            payment.mark_as_failed(str(e))
        except:
            pass
        return f'فشل معالجة الدفع: {str(e)}'


@shared_task
def send_payment_receipt(payment_id):
    """
    إرسال إيصال الدفع
    """
    try:
        from .models import Payment

        payment = Payment.objects.select_related(
            'student__user', 'course'
        ).get(id=payment_id)

        if payment.status != 'completed':
            return 'الدفعة غير مكتملة'

        student = payment.student
        course = payment.course

        subject = f'إيصال دفع - {course.title}'
        message = f'''
        مرحباً {student.user.get_full_name() or student.user.username}،

        شكراً لك على شرائك كورس "{course.title}"!

        تفاصيل الدفع:
        ● رقم المعاملة: {payment.transaction_id}
        ● المبلغ: {payment.amount} {payment.currency}
        ● طريقة الدفع: {payment.get_payment_method_display()}
        ● التاريخ: {payment.completed_at.strftime("%Y-%m-%d %H:%M")}

        تم تسجيلك في الكورس بنجاح!
        يمكنك البدء في التعلم الآن.

        مع تحياتنا،
        فريق E-Learning
        '''

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.user.email],
            fail_silently=False,
        )

        return f'تم إرسال الإيصال إلى {student.user.email}'

    except Exception as e:
        return f'خطأ في إرسال الإيصال: {str(e)}'


@shared_task
def expire_pending_payments():
    """
    إلغاء المدفوعات المعلقة القديمة (مهمة دورية - كل ساعة)
    """
    from .models import Payment
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=24)

    expired = Payment.objects.filter(
        status='pending',
        created_at__lt=cutoff
    )

    count = expired.count()
    expired.update(
        status='cancelled',
        notes='تم الإلغاء تلقائياً بسبب انتهاء المدة'
    )

    return f'تم إلغاء {count} دفعة معلقة'


@shared_task
def cleanup_expired_coupons():
    """
    تعطيل الكوبونات المنتهية (مهمة دورية - يومية)
    """
    from .models import Coupon

    now = timezone.now()
    expired = Coupon.objects.filter(
        is_active=True,
        valid_until__lt=now
    )

    count = expired.count()
    expired.update(is_active=False)

    return f'تم تعطيل {count} كوبون منتهي'


@shared_task
def send_refund_notification(refund_id):
    """
    إرسال إشعار بحالة طلب الاسترجاع
    """
    try:
        from .models import Refund

        refund = Refund.objects.select_related(
            'student__user', 'payment__course'
        ).get(id=refund_id)

        student = refund.student
        status_text = refund.get_status_display()

        subject = f'تحديث طلب الاسترجاع - {refund.payment.transaction_id}'
        message = f'''
        مرحباً {student.user.get_full_name() or student.user.username}،

        تحديث بخصوص طلب الاسترجاع الخاص بك:

        ● رقم المعاملة: {refund.payment.transaction_id}
        ● الكورس: {refund.payment.course.title}
        ● المبلغ: {refund.refund_amount} EGP
        ● الحالة: {status_text}

        {'ملاحظات الإدارة: ' + refund.admin_notes if refund.admin_notes else ''}

        مع تحياتنا،
        فريق E-Learning
        '''

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.user.email],
            fail_silently=False,
        )

        return f'تم إرسال إشعار الاسترجاع إلى {student.user.email}'

    except Exception as e:
        return f'خطأ في إرسال الإشعار: {str(e)}'


@shared_task
def generate_payment_report():
    """
    توليد تقرير المدفوعات (مهمة دورية - يومية)
    """
    from .models import Payment
    from django.db.models import Sum, Count
    from datetime import timedelta

    now = timezone.now()
    yesterday = now - timedelta(days=1)

    payments = Payment.objects.filter(
        created_at__gte=yesterday,
        created_at__lt=now
    )

    report = {
        'date': yesterday.strftime('%Y-%m-%d'),
        'total_payments': payments.count(),
        'successful': payments.filter(status='completed').count(),
        'failed': payments.filter(status='failed').count(),
        'pending': payments.filter(status='pending').count(),
        'total_amount': payments.filter(
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
    }

    # حفظ في الكاش أو قاعدة البيانات
    from django.core.cache import cache
    cache.set(f'payment_report_{yesterday.date()}', report, 86400 * 7)

    return f'تقرير {yesterday.date()}: {report}'
