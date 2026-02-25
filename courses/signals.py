"""
Signals للكورسات
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Course, Video, CourseReview
from .tasks import (
    calculate_course_duration, 
    send_new_course_notification,
    update_course_rating
)


@receiver(post_save, sender=Course)
def course_post_save(sender, instance, created, **kwargs):
    """عند إنشاء أو تحديث كورس"""
    # مسح الـ Cache
    cache.delete('categories_list')
    cache.delete('featured_courses')
    cache.delete(f'course_detail_{instance.slug}')
    
    if created and instance.is_published:
        # إرسال إشعار في الخلفية
        send_new_course_notification.delay(instance.id)


@receiver(post_save, sender=Video)
@receiver(post_delete, sender=Video)
def video_changed(sender, instance, **kwargs):
    """عند إضافة أو حذف فيديو"""
    # إعادة حساب مدة الكورس
    calculate_course_duration.delay(instance.course.id)
    
    # مسح الـ Cache
    cache.delete(f'course_detail_{instance.course.slug}')


@receiver(post_save, sender=CourseReview)
def review_post_save(sender, instance, created, **kwargs):
    """عند إضافة تقييم جديد"""
    if created:
        # تحديث تقييم الكورس
        update_course_rating.delay(instance.course.id)
