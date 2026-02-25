"""
Custom Exceptions
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class CustomValidationError(APIException):
    """خطأ تحقق مخصص"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'بيانات غير صحيحة'
    default_code = 'validation_error'


class ResourceNotFound(APIException):
    """العنصر غير موجود"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'العنصر غير موجود'
    default_code = 'not_found'


class PermissionDenied(APIException):
    """صلاحيات غير كافية"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'ليس لديك صلاحية للقيام بهذا الإجراء'
    default_code = 'permission_denied'


class AlreadyExists(APIException):
    """العنصر موجود بالفعل"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'العنصر موجود بالفعل'
    default_code = 'already_exists'


class ServiceUnavailable(APIException):
    """الخدمة غير متاحة"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'الخدمة غير متاحة حالياً، حاول لاحقاً'
    default_code = 'service_unavailable'
