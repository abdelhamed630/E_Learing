"""
Validators مشتركة للمشروع
"""
from rest_framework import serializers


def validate_image_file(value, max_size_mb=2):
    """
    التحقق من صحة ملف الصورة
    
    Args:
        value: الملف المرفوع
        max_size_mb: الحجم الأقصى بالميجابايت (افتراضي: 2MB)
    
    Returns:
        value: الملف المرفوع إذا كان صالح
    
    Raises:
        ValidationError: إذا كان الملف غير صالح
    """
    if not value:
        return value
    
    # التحقق من نوع الملف
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if value.content_type not in allowed_types:
        raise serializers.ValidationError(
            "نوع الملف غير مدعوم. استخدم JPG, PNG, GIF, أو WebP"
        )
    
    # التحقق من حجم الملف
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise serializers.ValidationError(
            f"حجم الصورة يجب أن يكون أقل من {max_size_mb}MB"
        )
    
    return value


def validate_document_file(value, max_size_mb=10):
    """
    التحقق من صحة ملف مستند
    
    للملفات المرفقة مثل PDF, DOC, DOCX
    """
    if not value:
        return value
    
    # أنواع المستندات المسموحة
    allowed_types = [
        'application/pdf',
        'application/msword',  # .doc
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.ms-powerpoint',  # .ppt
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/vnd.ms-excel',  # .xls
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'text/plain',  # .txt
    ]
    
    if value.content_type not in allowed_types:
        raise serializers.ValidationError(
            "نوع الملف غير مدعوم. استخدم PDF, Word, Excel, PowerPoint, أو Text"
        )
    
    # التحقق من حجم الملف
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise serializers.ValidationError(
            f"حجم الملف يجب أن يكون أقل من {max_size_mb}MB"
        )
    
    return value


def validate_video_file(value, max_size_mb=100):
    """
    التحقق من صحة ملف فيديو
    """
    if not value:
        return value
    
    allowed_types = [
        'video/mp4',
        'video/mpeg',
        'video/quicktime',  # .mov
        'video/x-msvideo',  # .avi
        'video/webm',
    ]
    
    if value.content_type not in allowed_types:
        raise serializers.ValidationError(
            "نوع الملف غير مدعوم. استخدم MP4, AVI, MOV, أو WebM"
        )
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise serializers.ValidationError(
            f"حجم الفيديو يجب أن يكون أقل من {max_size_mb}MB"
        )
    
    return value
