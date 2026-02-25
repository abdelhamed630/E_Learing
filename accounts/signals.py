"""
Signals للحسابات
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile
from .tasks import send_welcome_email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    إنشاء Profile تلقائياً عند إنشاء مستخدم
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    حفظ Profile عند حفظ المستخدم
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """
    ✅ إنشاء Student تلقائياً إذا كان role='student'
    """
    if created and instance.role == 'student':
        from students.models import Student
        Student.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def send_welcome_email_signal(sender, instance, created, **kwargs):
    """
    إرسال إيميل ترحيبي عند التسجيل
    """
    if created and instance.is_active:
        send_welcome_email.delay(instance.id)
