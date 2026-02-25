"""
Celery Tasks للتسجيلات
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
import uuid


@shared_task
def calculate_enrollment_progress(enrollment_id):
    """
    حساب نسبة الإنجاز في الكورس
    """
    try:
        from .models import Enrollment, VideoProgress
        
        enrollment = Enrollment.objects.get(id=enrollment_id)
        course = enrollment.course
        
        total_videos = course.videos.count()
        if total_videos == 0:
            return 'لا توجد فيديوهات في الكورس'
        
        completed_videos = VideoProgress.objects.filter(
            enrollment=enrollment,
            completed=True
        ).count()
        
        progress = int((completed_videos / total_videos) * 100)
        enrollment.progress = progress
        
        # حساب الوقت المستغرق
        total_time = VideoProgress.objects.filter(
            enrollment=enrollment
        ).aggregate(
            total=Sum('watched_duration')
        )['total'] or 0
        
        enrollment.total_time_spent = int(total_time / 60)  # تحويل إلى دقائق
        
        # التحقق من الإكمال
        if progress >= 100 and not enrollment.completed_at:
            enrollment.mark_as_completed()
            # توليد الشهادة
            generate_certificate.delay(enrollment_id)
        
        enrollment.save()
        
        return f'تم تحديث التقدم: {progress}%'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def generate_certificate(enrollment_id):
    """
    توليد شهادة إتمام الكورس
    """
    try:
        from .models import Enrollment, Certificate
        
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        if not enrollment.is_completed:
            return 'الكورس غير مكتمل'
        
        # التحقق من وجود شهادة سابقة
        if Certificate.objects.filter(enrollment=enrollment).exists():
            return 'الشهادة موجودة بالفعل'
        
        # توليد رقم الشهادة
        cert_number = f"CERT-{uuid.uuid4().hex[:12].upper()}"
        
        # إنشاء الشهادة
        certificate = Certificate.objects.create(
            enrollment=enrollment,
            certificate_number=cert_number,
            final_grade=enrollment.progress
        )
        
        # تحديث التسجيل
        enrollment.certificate_issued = True
        enrollment.certificate_url = f"/certificates/{cert_number}"
        enrollment.save()
        
        # إرسال إيميل (اختياري)
        send_certificate_email.delay(enrollment_id, cert_number)
        
        return f'تم إصدار الشهادة: {cert_number}'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def send_certificate_email(enrollment_id, cert_number):
    """
    إرسال إيميل الشهادة
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import Enrollment
        
        enrollment = Enrollment.objects.get(id=enrollment_id)
        student = enrollment.student
        course = enrollment.course
        
        subject = f'تهانينا! حصلت على شهادة من كورس {course.title}'
        message = f'''
        عزيزي/عزيزتي {student.user.get_full_name()},
        
        تهانينا! لقد أكملت كورس "{course.title}" بنجاح!
        
        رقم الشهادة: {cert_number}
        التاريخ: {timezone.now().strftime("%Y-%m-%d")}
        
        يمكنك تحميل الشهادة من حسابك على المنصة.
        
        نتمنى لك مزيداً من التقدم والنجاح!
        
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
        
        return f'تم إرسال الإيميل إلى {student.user.email}'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def update_learning_streak(student_id):
    """
    تحديث سلسلة التعلم اليومية
    """
    try:
        from .models import LearningStreak
        from students.models import Student
        
        student = Student.objects.get(id=student_id)
        today = timezone.now().date()
        
        # الحصول أو إنشاء سجل اليوم
        streak, created = LearningStreak.objects.get_or_create(
            student=student,
            date=today,
            defaults={
                'time_spent': 0,
                'videos_watched': 0,
                'notes_added': 0
            }
        )
        
        if not created:
            # تحديث الإحصائيات
            from .models import VideoProgress, CourseNote
            
            # الوقت المستغرق اليوم
            time_today = VideoProgress.objects.filter(
                student=student,
                last_watched__date=today
            ).aggregate(
                total=Sum('watched_duration')
            )['total'] or 0
            
            streak.time_spent = int(time_today / 60)
            
            # الفيديوهات المشاهدة اليوم
            videos_today = VideoProgress.objects.filter(
                student=student,
                last_watched__date=today
            ).count()
            
            streak.videos_watched = videos_today
            
            # الملاحظات المضافة اليوم
            notes_today = CourseNote.objects.filter(
                student=student,
                created_at__date=today
            ).count()
            
            streak.notes_added = notes_today
            
            streak.save()
        
        return f'تم تحديث سجل التعلم لـ {student.user.username}'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def send_course_reminder():
    """
    إرسال تذكير للطلاب الذين لم يدخلوا منذ فترة (مهمة دورية)
    """
    try:
        from django.core.mail import send_mass_mail
        from .models import Enrollment
        
        # الطلاب الذين لم يدخلوا منذ 7 أيام
        cutoff_date = timezone.now() - timedelta(days=7)
        
        inactive_enrollments = Enrollment.objects.filter(
            status='active',
            last_accessed__lt=cutoff_date
        ).select_related('student__user', 'course')
        
        messages = []
        for enrollment in inactive_enrollments:
            subject = f'نفتقد وجودك في كورس {enrollment.course.title}'
            message = f'''
            عزيزي/عزيزتي {enrollment.student.user.get_full_name()},
            
            لاحظنا أنك لم تدخل إلى كورس "{enrollment.course.title}" منذ فترة.
            
            تقدمك الحالي: {enrollment.progress}%
            
            لا تتردد في العودة واستكمال رحلتك التعليمية!
            
            مع تحياتنا،
            فريق E-Learning
            '''
            
            messages.append((
                subject,
                message,
                'noreply@e-learning.com',
                [enrollment.student.user.email]
            ))
        
        if messages:
            send_mass_mail(messages, fail_silently=True)
            return f'تم إرسال {len(messages)} تذكير'
        
        return 'لا توجد تسجيلات غير نشطة'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def expire_old_enrollments():
    """
    انتهاء صلاحية التسجيلات القديمة (مهمة دورية)
    """
    try:
        from .models import Enrollment
        
        now = timezone.now()
        
        expired = Enrollment.objects.filter(
            expires_at__lt=now,
            status='active'
        )
        
        count = expired.count()
        expired.update(status='expired')
        
        return f'تم انتهاء صلاحية {count} تسجيل'
    
    except Exception as e:
        return f'خطأ: {str(e)}'
