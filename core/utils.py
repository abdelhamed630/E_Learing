"""
Utility Functions مشتركة
"""
import random
import string
from django.utils.text import slugify as django_slugify


def generate_random_string(length=12, uppercase=True, digits=True):
    """
    توليد string عشوائي
    
    Args:
        length: الطول (افتراضي: 12)
        uppercase: استخدام حروف كبيرة (افتراضي: True)
        digits: استخدام أرقام (افتراضي: True)
    
    Returns:
        str: النص العشوائي
    """
    chars = string.ascii_lowercase
    if uppercase:
        chars += string.ascii_uppercase
    if digits:
        chars += string.digits
    
    return ''.join(random.choices(chars, k=length))


def generate_unique_code(prefix='', length=8):
    """
    توليد كود فريد مع prefix
    
    مثال: generate_unique_code('USER', 6) → USER-A3F9K2
    """
    code = generate_random_string(length, uppercase=True, digits=True)
    if prefix:
        return f"{prefix}-{code}"
    return code


def slugify_arabic(text, allow_unicode=True):
    """
    تحويل النص لـ slug مع دعم العربي
    
    Args:
        text: النص المراد تحويله
        allow_unicode: السماح بـ unicode (العربي)
    
    Returns:
        str: الـ slug
    """
    return django_slugify(text, allow_unicode=allow_unicode)


def format_file_size(size_bytes):
    """
    تحويل حجم الملف لصيغة قابلة للقراءة
    
    Args:
        size_bytes: الحجم بالبايت
    
    Returns:
        str: الحجم بصيغة قابلة للقراءة (مثال: 1.5 MB)
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds):
    """
    تحويل الثواني لصيغة قابلة للقراءة
    
    Args:
        seconds: المدة بالثواني
    
    Returns:
        str: المدة بصيغة قابلة للقراءة (مثال: 1h 30m)
    """
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        if remaining_minutes:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours:
        return f"{days}d {remaining_hours}h"
    return f"{days}d"


def get_client_ip(request):
    """
    الحصول على IP المستخدم من الـ request
    
    Args:
        request: Django request object
    
    Returns:
        str: IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    الحصول على User Agent من الـ request
    
    Args:
        request: Django request object
    
    Returns:
        str: User agent string
    """
    return request.META.get('HTTP_USER_AGENT', '')


def paginate_queryset(queryset, page, page_size=10):
    """
    تقسيم QuerySet لصفحات
    
    Args:
        queryset: Django QuerySet
        page: رقم الصفحة (يبدأ من 1)
        page_size: عدد العناصر في الصفحة
    
    Returns:
        dict: {items, total, page, pages}
    """
    from django.core.paginator import Paginator
    
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    return {
        'items': list(page_obj),
        'total': paginator.count,
        'page': page_obj.number,
        'pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }


def truncate_text(text, max_length=100, suffix='...'):
    """
    اختصار النص
    
    Args:
        text: النص
        max_length: الطول الأقصى
        suffix: النهاية (افتراضي: ...)
    
    Returns:
        str: النص المختصر
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_percentage(part, total):
    """
    حساب النسبة المئوية
    
    Args:
        part: الجزء
        total: الكل
    
    Returns:
        float: النسبة المئوية (0-100)
    """
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def days_until(target_date):
    """
    عدد الأيام المتبقية حتى تاريخ معين
    
    Args:
        target_date: التاريخ المستهدف
    
    Returns:
        int: عدد الأيام (قد يكون سالب إذا التاريخ في الماضي)
    """
    from django.utils import timezone
    
    if not target_date:
        return None
    
    now = timezone.now()
    if target_date.tzinfo is None:
        target_date = timezone.make_aware(target_date)
    
    delta = target_date - now
    return delta.days


def is_valid_email(email):
    """
    التحقق من صحة البريد الإلكتروني
    
    Args:
        email: البريد الإلكتروني
    
    Returns:
        bool: صحيح إذا كان البريد صالح
    """
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def clean_phone_number(phone):
    """
    تنظيف رقم الهاتف (إزالة المسافات والرموز)
    
    Args:
        phone: رقم الهاتف
    
    Returns:
        str: رقم الهاتف النظيف
    """
    if not phone:
        return ''
    
    # إزالة جميع الحروف والرموز ما عدا الأرقام والـ +
    import re
    return re.sub(r'[^\d+]', '', phone)
