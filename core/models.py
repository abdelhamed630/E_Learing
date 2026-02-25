"""
نماذج أساسية مشتركة
"""
from django.db import models


class TimeStampedModel(models.Model):
    """
    نموذج مجرد يحتوي على created_at و updated_at
    يمكن أن ترث منه أي نماذج أخرى
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    نموذج مجرد للحذف الناعم (Soft Delete)
    بدل ما تحذف السجل، بس تعلمه كمحذوف
    """
    is_deleted = models.BooleanField(default=False, verbose_name='محذوف')
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الحذف')

    class Meta:
        abstract = True

    def soft_delete(self):
        """حذف ناعم"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """استعادة من الحذف"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
