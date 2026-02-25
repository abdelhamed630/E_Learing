"""
Helper Functions للإشعارات
"""
from .models import Notification
from .tasks import send_notification_email


def notify_user(user, notification_type, title, message, link=None, data=None, send_email=False):
    """
    إرسال إشعار للمستخدم
    
    Args:
        user: المستخدم
        notification_type: نوع الإشعار
        title: العنوان
        message: الرسالة
        link: الرابط (اختياري)
        data: بيانات إضافية (اختياري)
        send_email: إرسال إيميل (افتراضي: False)
    
    Returns:
        notification: الإشعار المنشأ
    """
    # إنشاء الإشعار
    notification = Notification.create_notification(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        data=data
    )
    
    # إرسال إيميل إذا مطلوب
    if send_email:
        try:
            preference = user.notification_preference
            if preference.enable_email:
                send_notification_email.delay(user.id, title, message)
        except:
            # إرسال الإيميل حتى لو لم تكن التفضيلات موجودة
            send_notification_email.delay(user.id, title, message)
    
    return notification


def notify_course_enrollment(enrollment):
    """إشعار التسجيل في كورس"""
    return notify_user(
        user=enrollment.student.user,
        notification_type='course_enrolled',
        title=f'تسجيل في كورس {enrollment.course.title}',
        message=f'تم تسجيلك بنجاح في كورس "{enrollment.course.title}". يمكنك البدء في التعلم الآن!',
        link=f'/courses/{enrollment.course.slug}',
        data={'course_id': enrollment.course.id},
        send_email=True
    )


def notify_course_completion(enrollment):
    """إشعار إكمال كورس"""
    return notify_user(
        user=enrollment.student.user,
        notification_type='course_completed',
        title=f'تهانينا! أكملت كورس {enrollment.course.title}',
        message=f'أحسنت! لقد أكملت كورس "{enrollment.course.title}" بنجاح.',
        link=f'/certificates/{enrollment.id}',
        data={'course_id': enrollment.course.id},
        send_email=True
    )


def notify_exam_result(attempt):
    """إشعار نتيجة امتحان"""
    passed_text = 'نجحت ✅' if attempt.passed else 'لم تنجح ❌'
    
    return notify_user(
        user=attempt.student.user,
        notification_type='exam_result',
        title=f'نتيجة امتحان {attempt.exam.title}',
        message=f'{passed_text} - درجتك: {attempt.score}% (النجاح: {attempt.exam.passing_score}%)',
        link=f'/exams/{attempt.exam.id}/result/{attempt.id}',
        data={
            'exam_id': attempt.exam.id,
            'attempt_id': attempt.id,
            'score': float(attempt.score),
            'passed': attempt.passed
        },
        send_email=True
    )


def notify_payment_success(payment):
    """إشعار دفع ناجح"""
    return notify_user(
        user=payment.student.user,
        notification_type='payment_success',
        title='تم الدفع بنجاح',
        message=f'تم دفع {payment.amount} {payment.currency} لكورس "{payment.course.title}" بنجاح.',
        link=f'/payments/{payment.transaction_id}',
        data={
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': float(payment.amount)
        },
        send_email=True
    )


def notify_payment_failed(payment):
    """إشعار دفع فاشل"""
    return notify_user(
        user=payment.student.user,
        notification_type='payment_failed',
        title='فشل الدفع',
        message=f'فشلت عملية الدفع لكورس "{payment.course.title}". يرجى المحاولة مرة أخرى.',
        link=f'/courses/{payment.course.slug}',
        data={
            'payment_id': payment.id,
            'course_id': payment.course.id
        },
        send_email=True
    )


def notify_refund_status(refund):
    """إشعار حالة طلب الاسترجاع"""
    if refund.status == 'approved':
        title = 'تمت الموافقة على طلب الاسترجاع'
        message = f'تمت الموافقة على طلب استرجاع {refund.refund_amount} EGP.'
    elif refund.status == 'rejected':
        title = 'تم رفض طلب الاسترجاع'
        message = f'تم رفض طلب الاسترجاع. السبب: {refund.admin_notes}'
    else:
        return None
    
    return notify_user(
        user=refund.student.user,
        notification_type=f'refund_{refund.status}',
        title=title,
        message=message,
        link=f'/refunds/{refund.id}',
        data={
            'refund_id': refund.id,
            'status': refund.status
        },
        send_email=True
    )


def notify_new_course(course, target_students=None):
    """إشعار كورس جديد"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # إذا لم يتم تحديد طلاب معينين، أرسل للجميع
    if target_students is None:
        users = User.objects.filter(is_active=True, role='student')
    else:
        users = [student.user for student in target_students]
    
    notifications = []
    for user in users:
        notif = notify_user(
            user=user,
            notification_type='new_course',
            title=f'كورس جديد: {course.title}',
            message=f'تم إضافة كورس جديد "{course.title}". سجل الآن!',
            link=f'/courses/{course.slug}',
            data={'course_id': course.id},
            send_email=False  # نرسل إيميل جماعي منفصل
        )
        notifications.append(notif)
    
    return notifications


def notify_course_update(course):
    """إشعار تحديث كورس"""
    # الطلاب المسجلين في الكورس
    from enrollments.models import Enrollment
    
    enrollments = Enrollment.objects.filter(
        course=course,
        status='active'
    ).select_related('student__user')
    
    notifications = []
    for enrollment in enrollments:
        notif = notify_user(
            user=enrollment.student.user,
            notification_type='course_update',
            title=f'تحديث في كورس {course.title}',
            message=f'تم تحديث محتوى كورس "{course.title}". تحقق من المحتوى الجديد!',
            link=f'/courses/{course.slug}',
            data={'course_id': course.id},
            send_email=False
        )
        notifications.append(notif)
    
    return notifications
