"""
Admin للكورسات
"""
from django.contrib import admin
from .models import Category, Course, Section, Video, Attachment, CourseReview


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


class VideoInline(admin.TabularInline):
    model = Video
    extra = 1
    fields = ['title', 'video_url', 'duration', 'order', 'is_free']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'instructor', 'level',
        'price', 'students_count', 'rating', 'is_published', 'created_at'
    ]
    list_filter = ['is_published', 'is_featured', 'level', 'language', 'category', 'created_at']
    search_fields = ['title', 'description', 'instructor__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views_count', 'students_count', 'rating', 'created_at', 'updated_at']
    inlines = [SectionInline, VideoInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('title', 'slug', 'description', 'category', 'instructor')
        }),
        ('الوسائط', {
            'fields': ('thumbnail', 'trailer_url')
        }),
        ('التفاصيل', {
            'fields': ('level', 'language', 'duration_hours', 'requirements', 'what_will_learn')
        }),
        ('السعر', {
            'fields': ('price', 'discount_price')
        }),
        ('النشر', {
            'fields': ('is_published', 'is_featured')
        }),
        ('الإحصائيات', {
            'fields': ('views_count', 'students_count', 'rating'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'course__title']


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'section', 'duration',
        'order', 'is_free', 'views_count', 'created_at'
    ]
    list_filter = ['is_free', 'is_downloadable', 'course', 'created_at']
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    inlines = [AttachmentInline]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'video', 'file_size', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'video__title']


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ['course', 'student', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['course__title', 'student__user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
