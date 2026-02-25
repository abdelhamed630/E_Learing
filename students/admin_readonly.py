"""
Admin لتطبيق الطلاب
Read-Only - للعرض فقط، بدون إضافة أو تعديل
"""
from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_full_name',
        'get_email',
        'phone',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'phone'
    ]
    readonly_fields = ['user', 'phone', 'birth_date', 'avatar', 'bio', 'is_active', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user',)
        }),
        ('المعلومات الشخصية', {
            'fields': ('phone', 'birth_date', 'avatar', 'bio')
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """عرض الاسم الكامل"""
        return obj.full_name
    get_full_name.short_description = 'الاسم الكامل'
    
    def get_email(self, obj):
        """عرض البريد الإلكتروني"""
        return obj.email
    get_email.short_description = 'البريد الإلكتروني'
    
    # ❌ منع الإضافة
    def has_add_permission(self, request):
        """لا يمكن إضافة طلاب من هنا - يتسجلوا تلقائياً"""
        return False
    
    # ❌ منع التعديل
    def has_change_permission(self, request, obj=None):
        """قراءة فقط - الطالب يعدل بياناته من API"""
        return True  # يمكن الدخول لصفحة العرض
    
    # ❌ منع الحذف (إلا للـ superuser)
    def has_delete_permission(self, request, obj=None):
        """فقط الـ superuser يقدر يحذف"""
        return request.user.is_superuser
    
    # إضافة رسالة توضيحية في أعلى الصفحة
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'الطلاب (التسجيل تلقائي - قراءة فقط)'
        return super().changelist_view(request, extra_context=extra_context)
