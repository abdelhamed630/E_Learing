"""
Signals للإشعارات
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import NotificationPreference, Announcement
from .tasks import send_announcement_notifications

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_preference(sender, instance, created, **kwargs):
    """إنشاء تفضيلات الإشعارات تلقائياً للمستخدم الجديد"""
    if created:
        NotificationPreference.objects.create(user=instance)


@receiver(post_save, sender=Announcement)
def announcement_post_save(sender, instance, created, **kwargs):
    """إرسال إشعارات عند نشر إعلان جديد"""
    if instance.is_published and instance.send_notification:
        # إرسال الإشعارات في الخلفية
        send_announcement_notifications.delay(instance.id)
