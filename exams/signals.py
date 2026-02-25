"""
Signals للامتحانات
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ExamAttempt
from .tasks import calculate_exam_statistics


@receiver(post_save, sender=ExamAttempt)
def attempt_post_save(sender, instance, **kwargs):
    """تحديث إحصائيات الامتحان بعد كل تصحيح"""
    if instance.status == 'graded':
        calculate_exam_statistics.delay(instance.exam.id)
