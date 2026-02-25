"""
Celery Tasks لتطبيق الطلاب
"""
from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from .models import Student


@shared_task
def send_welcome_email(student_id):
    """
    إرسال إيميل ترحيبي للطالب الجديد
    """
    try:
        student = Student.objects.get(id=student_id)
        
        subject = f'مرحباً بك {student.full_name}!'
        message = f'''
        مرحباً {student.full_name}،
        
        نحن سعداء بانضمامك إلينا كطالب جديد!
        
        يمكنك الآن:
        - مشاهدة جميع الكورسات المتاحة
        - مشاهدة الفيديوهات التعليمية
        - حل الامتحانات واختبار معلوماتك
        
        نتمنى لك تجربة تعليمية ممتعة!
        
        مع تحياتنا،
        فريق الإدارة
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        
        return f'تم إرسال إيميل ترحيبي إلى {student.email}'
    
    except Student.DoesNotExist:
        return f'الطالب #{student_id} غير موجود'
    except Exception as e:
        return f'خطأ في إرسال الإيميل: {str(e)}'


@shared_task
def update_student_cache(student_id):
    """
    تحديث الـ Cache لبيانات الطالب
    """
    try:
        from .serializers import StudentSerializer
        
        student = Student.objects.select_related('user').get(id=student_id)
        serializer = StudentSerializer(student)
        
        cache_key = f'student_profile_{student_id}'
        cache.set(cache_key, serializer.data, 300)  # 5 دقائق
        
        return f'تم تحديث الـ Cache للطالب #{student_id}'
    
    except Student.DoesNotExist:
        return f'الطالب #{student_id} غير موجود'


@shared_task
def cleanup_inactive_students():
    """
    تنظيف الطلاب غير النشطين (مهمة دورية)
    يمكن تشغيلها كل يوم في منتصف الليل
    """
    from datetime import timedelta
    from django.utils import timezone
    
    # الطلاب الذين لم يسجلوا دخول منذ 6 أشهر
    cutoff_date = timezone.now() - timedelta(days=180)
    
    inactive_students = Student.objects.filter(
        user__last_login__lt=cutoff_date,
        is_active=True
    )
    
    count = inactive_students.count()
    
    # يمكن إضافة منطق إضافي هنا
    # مثل: إرسال إيميل تنبيه قبل تعطيل الحساب
    
    return f'تم العثور على {count} طالب غير نشط'


@shared_task
def send_bulk_notification_to_students(message, active_only=True):
    """
    إرسال إشعار جماعي لجميع الطلاب
    """
    queryset = Student.objects.select_related('user').all()
    
    if active_only:
        queryset = queryset.filter(is_active=True)
    
    emails = [student.email for student in queryset if student.email]
    
    if not emails:
        return 'لا توجد إيميلات للإرسال'
    
    try:
        send_mail(
            subject='إشعار مهم',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails,
            fail_silently=False,
        )
        
        return f'تم إرسال الإشعار إلى {len(emails)} طالب'
    
    except Exception as e:
        return f'خطأ في إرسال الإشعارات: {str(e)}'


@shared_task
def generate_student_report(student_id):
    """
    توليد تقرير شامل للطالب
    """
    try:
        student = Student.objects.get(id=student_id)
        
        # يمكن إضافة إحصائيات من الـ apps الأخرى
        report = {
            'student_id': student.id,
            'full_name': student.full_name,
            'email': student.email,
            'joined_date': student.created_at.strftime('%Y-%m-%d'),
            # إضافة المزيد من البيانات...
        }
        
        # حفظ التقرير في الـ Cache
        cache_key = f'student_report_{student_id}'
        cache.set(cache_key, report, 3600)  # ساعة واحدة
        
        return f'تم توليد التقرير للطالب #{student_id}'
    
    except Student.DoesNotExist:
        return f'الطالب #{student_id} غير موجود'
