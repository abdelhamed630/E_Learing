"""
Tests للإشعارات
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Notification, NotificationPreference, Announcement

User = get_user_model()


class NotificationModelTest(TestCase):
    """اختبار نموذج الإشعار"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123',
            role='student'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type='course_enrolled',
            title='تسجيل في كورس',
            message='تم تسجيلك في كورس Django'
        )

    def test_notification_creation(self):
        """اختبار إنشاء إشعار"""
        self.assertEqual(self.notification.user, self.user)
        self.assertFalse(self.notification.is_read)

    def test_mark_as_read(self):
        """اختبار تحديد الإشعار كمقروء"""
        self.notification.mark_as_read()
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_notification_preference_auto_create(self):
        """اختبار إنشاء التفضيلات تلقائياً"""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass123'
        )
        self.assertTrue(
            NotificationPreference.objects.filter(user=new_user).exists()
        )


class NotificationAPITest(APITestCase):
    """اختبار APIs الإشعارات"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='pass123',
            role='student'
        )
        self.client.force_authenticate(user=self.user)

        # إنشاء إشعارات
        Notification.objects.create(
            user=self.user,
            notification_type='exam_result',
            title='نتيجة الامتحان',
            message='نجحت في الامتحان'
        )

    def test_list_notifications(self):
        """اختبار عرض قائمة الإشعارات"""
        response = self.client.get('/api/notifications/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unread_count(self):
        """اختبار عدد الإشعارات غير المقروءة"""
        response = self.client.get('/api/notifications/notifications/unread_count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_mark_as_read(self):
        """اختبار تحديد إشعار كمقروء"""
        notification = Notification.objects.first()
        response = self.client.post(
            f'/api/notifications/notifications/{notification.id}/mark_as_read/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)


class AnnouncementTest(TestCase):
    """اختبار الإعلانات"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='pass123',
            role='admin'
        )
        
        self.announcement = Announcement.objects.create(
            title='إعلان مهم',
            content='محتوى الإعلان',
            priority='high',
            target_audience='all',
            is_published=True,
            created_by=self.admin
        )

    def test_announcement_is_active(self):
        """اختبار أن الإعلان نشط"""
        self.assertTrue(self.announcement.is_active())

    def test_get_target_users(self):
        """اختبار الحصول على المستخدمين المستهدفين"""
        User.objects.create_user(
            username='student1',
            email='s1@example.com',
            password='pass123',
            role='student'
        )
        
        users = self.announcement.get_target_users()
        self.assertGreater(users.count(), 0)
