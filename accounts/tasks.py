"""
Celery Tasks للحسابات
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets


@shared_task
def send_verification_email(user_id):
    """
    إرسال إيميل توثيق البريد الإلكتروني
    """
    try:
        from .models import User, EmailVerification
        
        user = User.objects.get(id=user_id)
        
        # إنشاء رمز التوثيق
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        EmailVerification.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # رابط التوثيق
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        subject = 'توثيق البريد الإلكتروني - E-Learning'
        message = f'''
        مرحباً {user.full_name}،
        
        شكراً لتسجيلك في E-Learning!
        
        الرجاء توثيق بريدك الإلكتروني بالضغط على الرابط التالي:
        {verification_url}
        
        هذا الرابط صالح لمدة 7 أيام.
        
        إذا لم تقم بإنشاء هذا الحساب، يمكنك تجاهل هذه الرسالة.
        
        مع تحياتنا،
        فريق E-Learning
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return f'تم إرسال إيميل التوثيق إلى {user.email}'
    
    except Exception as e:
        return f'خطأ في إرسال الإيميل: {str(e)}'


@shared_task
def send_password_reset_email(user_id, token):
    """
    إرسال إيميل إعادة تعيين كلمة المرور
    """
    try:
        from .models import User
        
        user = User.objects.get(id=user_id)
        
        # رابط إعادة التعيين
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        subject = 'إعادة تعيين كلمة المرور - E-Learning'
        message = f'''
        مرحباً {user.full_name}،
        
        تلقينا طلباً لإعادة تعيين كلمة المرور لحسابك.
        
        الرجاء الضغط على الرابط التالي لإعادة تعيين كلمة المرور:
        {reset_url}
        
        هذا الرابط صالح لمدة 24 ساعة.
        
        إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذه الرسالة.
        
        مع تحياتنا،
        فريق E-Learning
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return f'تم إرسال إيميل إعادة التعيين إلى {user.email}'
    
    except Exception as e:
        return f'خطأ في إرسال الإيميل: {str(e)}'


@shared_task
def send_welcome_email(user_id):
    """
    إرسال إيميل ترحيبي للمستخدم الجديد
    """
    try:
        from .models import User
        
        user = User.objects.get(id=user_id)
        
        subject = f'مرحباً بك في E-Learning يا {user.full_name}!'
        message = f'''
        مرحباً {user.full_name}،
        
        نحن سعداء جداً بانضمامك إلى منصة E-Learning!
        
        يمكنك الآن:
        • تصفح مئات الكورسات المتاحة
        • التسجيل في الكورسات التي تهمك
        • تتبع تقدمك في التعلم
        • الحصول على شهادات إتمام
        
        ابدأ رحلتك التعليمية الآن!
        
        نتمنى لك تجربة تعليمية ممتعة ومفيدة.
        
        مع تحياتنا،
        فريق E-Learning
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return f'تم إرسال إيميل ترحيبي إلى {user.email}'
    
    except Exception as e:
        return f'خطأ في إرسال الإيميل: {str(e)}'


@shared_task
def cleanup_expired_tokens():
    """
    تنظيف الرموز المنتهية (مهمة دورية)
    """
    from .models import EmailVerification, PasswordReset
    from django.utils import timezone
    
    now = timezone.now()
    
    # حذف رموز التوثيق المنتهية
    expired_verifications = EmailVerification.objects.filter(expires_at__lt=now)
    ver_count = expired_verifications.count()
    expired_verifications.delete()
    
    # حذف رموز إعادة التعيين المنتهية
    expired_resets = PasswordReset.objects.filter(expires_at__lt=now)
    reset_count = expired_resets.count()
    expired_resets.delete()
    
    return f'تم حذف {ver_count} رمز توثيق و {reset_count} رمز إعادة تعيين'


@shared_task
def cleanup_login_history():
    """
    تنظيف سجل تسجيل الدخول القديم (مهمة دورية)
    يحتفظ بآخر 6 أشهر فقط
    """
    from .models import LoginHistory
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=180)
    old_logs = LoginHistory.objects.filter(created_at__lt=cutoff_date)
    
    count = old_logs.count()
    old_logs.delete()
    
    return f'تم حذف {count} سجل قديم'


@shared_task
def deactivate_unverified_accounts():
    """
    تعطيل الحسابات غير الموثقة بعد 30 يوم (مهمة دورية)
    """
    from .models import User
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    unverified_users = User.objects.filter(
        is_verified=False,
        is_active=True,
        created_at__lt=cutoff_date
    )
    
    count = unverified_users.count()
    unverified_users.update(is_active=False)
    
    return f'تم تعطيل {count} حساب غير موثق'
