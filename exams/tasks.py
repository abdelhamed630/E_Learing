"""
Celery Tasks للامتحانات
"""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg


@shared_task
def grade_exam_attempt(attempt_id):
    """
    تصحيح الامتحان وحساب الدرجة
    """
    try:
        from .models import ExamAttempt, StudentAnswer

        attempt = ExamAttempt.objects.get(id=attempt_id)

        if attempt.status not in ['submitted', 'expired']:
            return f'المحاولة #{attempt_id} ليست جاهزة للتصحيح'

        # تصحيح كل إجابة
        total_points = attempt.exam.total_points
        earned_points = 0

        for student_answer in attempt.student_answers.all():
            student_answer.check_answer()
            earned_points += student_answer.points_earned

        # حساب الدرجة كنسبة مئوية
        score = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score >= attempt.exam.passing_score

        # تحديث المحاولة
        attempt.score = round(score, 2)
        attempt.points_earned = earned_points
        attempt.passed = passed
        attempt.status = 'graded'
        attempt.save()

        # مسح الكاش
        cache.delete(f'exam_detail_{attempt.exam.id}_student_{attempt.student.id}')

        # إرسال إشعار بالنتيجة
        send_exam_result_notification.delay(attempt_id)

        return f'تم تصحيح المحاولة #{attempt_id} - الدرجة: {score:.2f}%'

    except ExamAttempt.DoesNotExist:
        return f'المحاولة #{attempt_id} غير موجودة'
    except Exception as e:
        return f'خطأ في التصحيح: {str(e)}'


@shared_task
def auto_submit_attempt(attempt_id):
    """
    تسليم تلقائي عند انتهاء الوقت
    """
    try:
        from .models import ExamAttempt

        attempt = ExamAttempt.objects.get(id=attempt_id)

        if attempt.status != 'in_progress':
            return f'المحاولة #{attempt_id} ليست جارية'

        if not attempt.is_expired:
            return f'المحاولة #{attempt_id} لم تنته مدتها بعد'

        attempt.status = 'expired'
        attempt.submitted_at = attempt.expires_at
        attempt.save()

        # تصحيح ما تم الإجابة عليه
        grade_exam_attempt.delay(attempt_id)

        return f'تم التسليم التلقائي للمحاولة #{attempt_id}'

    except ExamAttempt.DoesNotExist:
        return f'المحاولة #{attempt_id} غير موجودة'


@shared_task
def send_exam_result_notification(attempt_id):
    """
    إرسال إشعار بنتيجة الامتحان
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import ExamAttempt

        attempt = ExamAttempt.objects.get(id=attempt_id)
        student = attempt.student
        exam = attempt.exam

        result_text = 'ناجح ✅' if attempt.passed else 'راسب ❌'

        subject = f'نتيجة امتحان {exam.title}'
        message = f'''
        مرحباً {student.user.get_full_name() or student.user.username}،

        نتيجة امتحانك في "{exam.title}":

        ● الدرجة: {attempt.score}%
        ● درجة النجاح: {exam.passing_score}%
        ● النتيجة: {result_text}
        ● المحاولة: {attempt.attempt_number} من {exam.max_attempts}

        {'🎉 تهانينا! لقد نجحت في الامتحان.' if attempt.passed else 'لا تيأس! يمكنك المحاولة مرة أخرى.'}

        مع تحياتنا،
        فريق E-Learning
        '''

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.user.email],
            fail_silently=True,
        )

        return f'تم إرسال إشعار النتيجة إلى {student.user.email}'

    except Exception as e:
        return f'خطأ في إرسال الإشعار: {str(e)}'


@shared_task
def cleanup_expired_attempts():
    """
    تسليم تلقائي للمحاولات المنتهية (مهمة دورية - كل 5 دقائق)
    """
    from .models import ExamAttempt

    now = timezone.now()
    expired = ExamAttempt.objects.filter(
        status='in_progress',
        expires_at__lt=now
    )

    count = 0
    for attempt in expired:
        auto_submit_attempt.delay(attempt.id)
        count += 1

    return f'تم التسليم التلقائي لـ {count} محاولة منتهية'


@shared_task
def calculate_exam_statistics(exam_id):
    """
    حساب إحصائيات الامتحان (مهمة دورية)
    """
    try:
        from .models import Exam, ExamAttempt

        exam = Exam.objects.get(id=exam_id)
        attempts = ExamAttempt.objects.filter(
            exam=exam,
            status='graded'
        )

        if not attempts.exists():
            return 'لا توجد محاولات مصححة'

        stats = {
            'total_attempts': attempts.count(),
            'passed_count': attempts.filter(passed=True).count(),
            'failed_count': attempts.filter(passed=False).count(),
            'avg_score': float(attempts.aggregate(Avg('score'))['score__avg'] or 0),
            'highest_score': float(attempts.order_by('-score').first().score or 0),
            'lowest_score': float(attempts.order_by('score').first().score or 0),
        }

        # حفظ في الكاش
        cache.set(f'exam_stats_{exam_id}', stats, 3600)

        return f'تم حساب إحصائيات الامتحان #{exam_id}: {stats}'

    except Exam.DoesNotExist:
        return f'الامتحان #{exam_id} غير موجود'
