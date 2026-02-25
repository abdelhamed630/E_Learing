"""
Views للإشعارات
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Notification, NotificationPreference, Announcement
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    AnnouncementSerializer
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للإشعارات
    المستخدم: يشوف إشعاراته فقط
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """المستخدم يشوف إشعاراته فقط"""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """الإشعارات غير المقروءة"""
        notifications = self.get_queryset().filter(is_read=False)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """عدد الإشعارات غير المقروءة"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """تحديد إشعار كمقروء"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({
            'message': 'تم تحديد الإشعار كمقروء',
            'notification': NotificationSerializer(notification).data
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """تحديد جميع الإشعارات كمقروءة"""
        unread = self.get_queryset().filter(is_read=False)
        count = unread.count()
        
        for notification in unread:
            notification.mark_as_read()
        
        return Response({
            'message': f'تم تحديد {count} إشعار كمقروء'
        })

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """مسح جميع الإشعارات"""
        count = self.get_queryset().count()
        self.get_queryset().delete()
        
        return Response({
            'message': f'تم مسح {count} إشعار'
        })

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """الإشعارات حسب النوع"""
        notification_type = request.query_params.get('type')
        
        if not notification_type:
            return Response(
                {'error': 'يجب تحديد نوع الإشعار'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notifications = self.get_queryset().filter(
            notification_type=notification_type
        )
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet لتفضيلات الإشعارات
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """عرض تفضيلات المستخدم الحالي"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_preferences(self, request):
        """تحديث تفضيلات الإشعارات"""
        preference, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = NotificationPreferenceSerializer(
            preference,
            data=request.data,
            partial=(request.method == 'PATCH')
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'تم تحديث التفضيلات بنجاح',
            'preferences': serializer.data
        })


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للإعلانات
    المستخدم: يشوف الإعلانات النشطة فقط
    """
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """الإعلانات النشطة للمستخدم"""
        user = self.request.user
        queryset = Announcement.objects.filter(is_published=True)
        
        # فلترة حسب الفئة المستهدفة
        if user.role == 'student':
            queryset = queryset.filter(
                Q(target_audience='all') | Q(target_audience='students')
            )
        elif user.role == 'instructor':
            queryset = queryset.filter(
                Q(target_audience='all') | Q(target_audience='instructors')
            )
        
        # فلترة الإعلانات النشطة فقط
        from django.utils import timezone
        now = timezone.now()
        
        queryset = queryset.filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=now)
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gte=now)
        )
        
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """الإعلانات العاجلة"""
        announcements = self.get_queryset().filter(priority='urgent')
        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data)
