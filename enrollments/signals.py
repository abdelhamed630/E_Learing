"""
Signals للتسجيلات
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment, VideoProgress
from .tasks import calculate_enrollment_progress, update_learning_streak


@receiver(post_save, sender=VideoProgress)
def update_progress_on_video_watch(sender, instance, created, **kwargs):
    """
    تحديث التقدم عند مشاهدة فيديو
    """
    if instance.completed:
        # تحديث تقدم التسجيل
        calculate_enrollment_progress.delay(instance.enrollment.id)
        
        # تحديث سلسلة التعلم
        update_learning_streak.delay(instance.student.id)


@receiver(post_save, sender=Enrollment)
def enrollment_post_save(sender, instance, created, **kwargs):
    """
    عند إنشاء تسجيل جديد
    """
    if created:
        # يمكن إضافة منطق إضافي هنا
        # مثل: إرسال إيميل ترحيبي
        pass
