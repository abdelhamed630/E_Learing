"""
Celery Tasks للإشعارات
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


@shared_task
def send_notification_email(user_id, subject, message):
    """
    إرسال إشعار عبر البريد الإلكتروني
    """
    try:
        from django.contrib.auth import get_user_model
        from .models import EmailLog, NotificationPreference
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        # التحقق من تفضيلات المستخدم
        try:
            preference = user.notification_preference
            if not preference.enable_email:
                return 'الإيميلات معطلة لهذا المستخدم'
        except NotificationPreference.DoesNotExist:
            pass  # افتراضياً: إرسال الإيميل
        
        # إنشاء سجل الإيميل
        email_log = EmailLog.objects.create(
            user=user,
            subject=subject,
            message=message,
            status='pending'
        )
        
        try:
            # إرسال الإيميل
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # تحديث الحالة
            email_log.status = 'sent'
            email_log.sent_at = timezone.now()
            email_log.save()
            
            return f'تم إرسال الإيميل إلى {user.email}'
        
        except Exception as e:
            # تسجيل الخطأ
            email_log.status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
            
            return f'فشل إرسال الإيميل: {str(e)}'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def send_announcement_notifications(announcement_id):
    """
    إرسال إشعارات الإعلان للمستخدمين المستهدفين
    """
    try:
        from .models import Announcement, Notification
        
        announcement = Announcement.objects.get(id=announcement_id)
        
        if not announcement.send_notification:
            return 'إرسال الإشعارات معطل لهذا الإعلان'
        
        # الحصول على المستخدمين المستهدفين
        users = announcement.get_target_users()
        
        count = 0
        for user in users:
            # إنشاء إشعار داخل التطبيق
            Notification.create_notification(
                user=user,
                notification_type='announcement',
                title=announcement.title,
                message=announcement.content,
                data={
                    'announcement_id': announcement.id,
                    'priority': announcement.priority
                }
            )
            
            # إرسال إيميل إذا مطلوب
            if announcement.send_email:
                send_notification_email.delay(
                    user.id,
                    f'إعلان: {announcement.title}',
                    announcement.content
                )
            
            count += 1
        
        return f'تم إرسال {count} إشعار'
    
    except Exception as e:
        return f'خطأ: {str(e)}'


@shared_task
def cleanup_old_notifications():
    """
    مسح الإشعارات القديمة المقروءة (مهمة دورية - شهرية)
    """
    from .models import Notification
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_notifications = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date
    )
    
    count = old_notifications.count()
    old_notifications.delete()
    
    return f'تم مسح {count} إشعار قديم'


@shared_task
def send_daily_digest():
    """
    إرسال ملخص يومي بالإشعارات (مهمة دورية - يومية)
    """
    from django.contrib.auth import get_user_model
    from .models import Notification, NotificationPreference
    from datetime import timedelta
    
    User = get_user_model()
    yesterday = timezone.now() - timedelta(days=1)
    
    # المستخدمين الذين يريدون الملخص اليومي
    preferences = NotificationPreference.objects.filter(
        enable_email=True,
        email_frequency='daily'
    ).select_related('user')
    
    count = 0
    for preference in preferences:
        user = preference.user
        
        # الإشعارات غير المقروءة من آخر 24 ساعة
        notifications = Notification.objects.filter(
            user=user,
            is_read=False,
            created_at__gte=yesterday
        )
        
        if notifications.exists():
            # تجميع الإشعارات في إيميل واحد
            message = f"لديك {notifications.count()} إشعار جديد:\n\n"
            
            for notif in notifications[:10]:  # أول 10 فقط
                message += f"• {notif.title}\n"
            
            if notifications.count() > 10:
                message += f"\n... و {notifications.count() - 10} إشعار آخر"
            
            send_notification_email.delay(
                user.id,
                f'لديك {notifications.count()} إشعار جديد',
                message
            )
            count += 1
    
    return f'تم إرسال {count} ملخص يومي'


@shared_task
def send_reminder_notification(user_id, title, message):
    """
    إرسال تذكير للمستخدم
    """
    try:
        from django.contrib.auth import get_user_model
        from .models import Notification
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        # إنشاء إشعار
        Notification.create_notification(
            user=user,
            notification_type='reminder',
            title=title,
            message=message
        )
        
        # إرسال إيميل
        send_notification_email.delay(user_id, title, message)
        
        return f'تم إرسال التذكير إلى {user.email}'
    
    except Exception as e:
        return f'خطأ: {str(e)}'
