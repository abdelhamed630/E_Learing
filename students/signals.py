"""
Signals لتطبيق الطلاب
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Student
from .tasks import send_welcome_email, update_student_cache


@receiver(post_save, sender=Student)
def student_post_save(sender, instance, created, **kwargs):
    """
    عند إنشاء أو تحديث طالب
    """
    if created:
        # إرسال إيميل ترحيبي في الخلفية
        send_welcome_email.delay(instance.id)
    else:
        # تحديث الـ Cache
        update_student_cache.delay(instance.id)
