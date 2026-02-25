"""
Admin للإشعارات
"""
from django.contrib import admin
from .models import Notification, NotificationPreference, Announcement, EmailLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'title',
        'is_read', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('معلومات الإشعار', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('الرابط والبيانات', {
            'fields': ('link', 'data')
        }),
        ('الحالة', {
            'fields': ('is_read', 'read_at')
        }),
        ('التاريخ', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'enable_in_app', 'enable_email',
        'email_frequency'
    ]
    list_filter = ['enable_in_app', 'enable_email', 'email_frequency']
    search_fields = ['user__username', 'user__email']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'priority', 'target_audience',
        'is_published', 'created_at'
    ]
    list_filter = ['priority', 'target_audience', 'is_published', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('المحتوى', {
            'fields': ('title', 'content')
        }),
        ('الإعدادات', {
            'fields': ('priority', 'target_audience')
        }),
        ('النشر', {
            'fields': ('is_published', 'publish_at', 'expires_at')
        }),
        ('الإشعارات', {
            'fields': ('send_notification', 'send_email')
        }),
        ('معلومات إضافية', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'subject', 'status',
        'created_at', 'sent_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email', 'subject']
    readonly_fields = ['created_at', 'sent_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
