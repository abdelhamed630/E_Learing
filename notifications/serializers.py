"""
Serializers للإشعارات
"""
from rest_framework import serializers
from .models import Notification, NotificationPreference, Announcement


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer للإشعار"""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title', 'message', 'link', 'data',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer لتفضيلات الإشعارات"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'enable_in_app', 'enable_email',
            'notify_course_updates', 'notify_exam_results',
            'notify_payments', 'notify_announcements',
            'notify_reminders', 'email_frequency'
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serializer للإعلان"""
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    target_audience_display = serializers.CharField(
        source='get_target_audience_display',
        read_only=True
    )
    is_active = serializers.BooleanField(
        source='is_active',
        read_only=True
    )

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content',
            'priority', 'priority_display',
            'target_audience', 'target_audience_display',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
