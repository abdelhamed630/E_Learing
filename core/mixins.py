"""
Mixins للـ ViewSets و Views
"""
from rest_framework.response import Response
from rest_framework import status


class SuccessMessageMixin:
    """
    إضافة رسالة نجاح تلقائية
    """
    success_message = None

    def get_success_message(self):
        return self.success_message or 'تمت العملية بنجاح'

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = {
            'message': self.get_success_message(),
            'data': response.data
        }
        return response


class PaginationMixin:
    """
    تقسيم مخصص للصفحات
    """
    default_page_size = 10
    max_page_size = 100

    def get_page_size(self, request):
        try:
            size = int(request.query_params.get('page_size', self.default_page_size))
            return min(size, self.max_page_size)
        except (TypeError, ValueError):
            return self.default_page_size


class CacheMixin:
    """
    كاش تلقائي للـ list
    """
    cache_timeout = 300  # 5 دقائق

    def get_cache_key(self):
        return f"{self.__class__.__name__}_list"

    def list(self, request, *args, **kwargs):
        from django.core.cache import cache
        
        cache_key = self.get_cache_key()
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, self.cache_timeout)
        
        return response


class FilterByUserMixin:
    """
    فلترة تلقائية حسب المستخدم الحالي
    """
    user_field = 'user'  # اسم الحقل في الـ model

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            filter_kwargs = {self.user_field: self.request.user}
            return queryset.filter(**filter_kwargs)
        return queryset.none()


class SoftDeleteMixin:
    """
    حذف ناعم بدل الحذف الكامل
    """
    def perform_destroy(self, instance):
        if hasattr(instance, 'soft_delete'):
            instance.soft_delete()
        else:
            instance.delete()
