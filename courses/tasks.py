"""
Celery Tasks للكورسات
"""
from celery import shared_task
from django.core.cache import cache
from django.db.models import Avg, Sum
from .models import Course, Video


@shared_task
def update_course_rating(course_id):
    """
    تحديث تقييم الكورس بناءً على تقييمات الطلاب
    """
    try:
        course = Course.objects.get(id=course_id)
        
        # حساب متوسط التقييم
        avg_rating = course.reviews.aggregate(Avg('rating'))['rating__avg']
        
        if avg_rating:
            course.rating = round(avg_rating, 2)
            course.save(update_fields=['rating'])
            
            # مسح الـ Cache
            cache.delete(f'course_detail_{course.slug}')
            cache.delete('featured_courses')
            
            return f'تم تحديث تقييم الكورس: {course.title} - {course.rating}⭐'
        
        return f'لا توجد تقييمات للكورس: {course.title}'
    
    except Course.DoesNotExist:
        return f'الكورس #{course_id} غير موجود'


@shared_task
def increment_video_views(video_id):
    """
    زيادة عدد مشاهدات الفيديو
    """
    try:
        from django.db.models import F
        Video.objects.filter(id=video_id).update(
            views_count=F('views_count') + 1
        )
        return f'تم تحديث مشاهدات الفيديو #{video_id}'
    
    except Exception as e:
        return f'خطأ في تحديث المشاهدات: {str(e)}'


@shared_task
def update_course_students_count(course_id):
    """
    تحديث عدد الطلاب المسجلين في الكورس
    """
    try:
        from enrollments.models import Enrollment
        course = Course.objects.get(id=course_id)
        
        students_count = Enrollment.objects.filter(course=course).count()
        course.students_count = students_count
        course.save(update_fields=['students_count'])
        
        # مسح الـ Cache
        cache.delete(f'course_detail_{course.slug}')
        
        return f'عدد الطلاب في {course.title}: {students_count}'
    
    except Course.DoesNotExist:
        return f'الكورس #{course_id} غير موجود'


@shared_task
def calculate_course_duration(course_id):
    """
    حساب إجمالي مدة الكورس
    """
    try:
        course = Course.objects.get(id=course_id)
        
        total_seconds = course.videos.aggregate(
            total=Sum('duration')
        )['total'] or 0
        
        # تحويل إلى ساعات
        duration_hours = int(total_seconds / 3600)
        
        course.duration_hours = duration_hours
        course.save(update_fields=['duration_hours'])
        
        return f'مدة الكورس {course.title}: {duration_hours} ساعة'
    
    except Course.DoesNotExist:
        return f'الكورس #{course_id} غير موجود'


@shared_task
def send_new_course_notification(course_id):
    """
    إرسال إشعار للطلاب عند إضافة كورس جديد
    """
    try:
        from django.core.mail import send_mass_mail
        from students.models import Student
        
        course = Course.objects.get(id=course_id)
        
        if not course.is_published:
            return 'الكورس غير منشور'
        
        # جميع الطلاب النشطين
        students = Student.objects.filter(is_active=True).select_related('user')
        
        messages = []
        for student in students:
            if student.email:
                subject = f'كورس جديد: {course.title}'
                message = f'''
                مرحباً {student.full_name}،
                
                تم إضافة كورس جديد: {course.title}
                المستوى: {course.get_level_display()}
                السعر: {course.final_price} جنيه
                
                سجل الآن!
                '''
                messages.append((subject, message, 'noreply@e-learning.com', [student.email]))
        
        if messages:
            send_mass_mail(messages, fail_silently=True)
            return f'تم إرسال {len(messages)} إشعار'
        
        return 'لا توجد إيميلات للإرسال'
    
    except Course.DoesNotExist:
        return f'الكورس #{course_id} غير موجود'


@shared_task
def cleanup_course_cache():
    """
    تنظيف الـ Cache الخاص بالكورسات (مهمة دورية)
    """
    cache.delete('categories_list')
    cache.delete('featured_courses')
    
    return 'تم تنظيف الـ Cache بنجاح'


@shared_task
def generate_course_statistics():
    """
    توليد إحصائيات الكورسات (مهمة دورية يومية)
    """
    from django.db.models import Count, Avg, Sum
    
    stats = {
        'total_courses': Course.objects.filter(is_published=True).count(),
        'total_students': 0,  # من enrollments
        'avg_rating': Course.objects.filter(is_published=True).aggregate(
            Avg('rating')
        )['rating__avg'] or 0,
        'total_videos': Video.objects.count(),
    }
    
    # حفظ في الـ Cache
    cache.set('course_statistics', stats, 86400)  # 24 ساعة
    
    return f'إحصائيات الكورسات: {stats}'
