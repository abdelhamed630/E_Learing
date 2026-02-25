"""
Admin للمدربين
الأدمن فقط يقدر يضيف/يعدل/يحذف مدربين
"""
from django.contrib import admin
from .models import Instructor


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'specialization', 'years_of_experience',
        'total_courses', 'total_students', 'average_rating',
        'is_active', 'is_featured', 'created_at'
    ]
    list_filter = ['is_active', 'is_featured', 'created_at']
    search_fields = [
        'user__username', 'user__email',
        'user__first_name', 'user__last_name',
        'specialization', 'bio'
    ]
    readonly_fields = [
        'total_courses', 'total_students', 'average_rating',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user',)
        }),
        ('معلومات مهنية', {
            'fields': ('bio', 'specialization', 'years_of_experience')
        }),
        ('الروابط', {
            'fields': ('website', 'linkedin', 'github')
        }),
        ('الملفات', {
            'fields': ('avatar', 'resume')
        }),
        ('الحالة', {
            'fields': ('is_active', 'is_featured')
        }),
        ('الإحصائيات', {
            'fields': ('total_courses', 'total_students', 'average_rating'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_stats', 'mark_as_featured', 'mark_as_active']
    
    def update_stats(self, request, queryset):
        """تحديث إحصائيات المدربين المختارين"""
        for instructor in queryset:
            instructor.update_stats()
        self.message_user(request, f'تم تحديث إحصائيات {queryset.count()} مدرب')
    update_stats.short_description = 'تحديث الإحصائيات'
    
    def mark_as_featured(self, request, queryset):
        """وضع علامة مميز"""
        queryset.update(is_featured=True)
        self.message_user(request, f'تم وضع علامة مميز على {queryset.count()} مدرب')
    mark_as_featured.short_description = 'وضع علامة مميز'
    
    def mark_as_active(self, request, queryset):
        """تفعيل المدربين"""
        queryset.update(is_active=True)
        self.message_user(request, f'تم تفعيل {queryset.count()} مدرب')
    mark_as_active.short_description = 'تفعيل'
