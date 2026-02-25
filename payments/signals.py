"""
Signals للمدفوعات
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Refund
from .tasks import send_refund_notification


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """بعد حفظ الدفعة"""
    if instance.status == 'completed' and not created:
        # يمكن إضافة منطق إضافي هنا
        pass


@receiver(post_save, sender=Refund)
def refund_post_save(sender, instance, **kwargs):
    """بعد تحديث طلب الاسترجاع"""
    if instance.status in ['approved', 'rejected', 'completed']:
        # إرسال إشعار للطالب
        send_refund_notification.delay(instance.id)
