"""
Tests لتطبيق الطلاب
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Student


class StudentModelTest(TestCase):
    """اختبار نموذج الطالب"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.student = Student.objects.create(
            user=self.user,
            phone='01234567890',
            bio='طالب تجريبي'
        )
    
    def test_student_creation(self):
        """اختبار إنشاء طالب"""
        self.assertEqual(self.student.user.username, 'testuser')
        self.assertEqual(self.student.phone, '01234567890')
        self.assertTrue(self.student.is_active)
    
    def test_student_str(self):
        """اختبار __str__ method"""
        self.assertEqual(str(self.student), 'testuser')
    
    def test_full_name_property(self):
        """اختبار خاصية full_name"""
        self.user.first_name = 'أحمد'
        self.user.last_name = 'محمد'
        self.user.save()
        self.assertEqual(self.student.full_name, 'أحمد محمد')
    
    def test_email_property(self):
        """اختبار خاصية email"""
        self.assertEqual(self.student.email, 'test@example.com')


class StudentAPITest(APITestCase):
    """اختبار APIs الطلاب"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='pass123'
        )
        self.student = Student.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
    
    def test_get_profile(self):
        """اختبار الحصول على الملف الشخصي"""
        response = self.client.get('/api/student/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'student1')
    
    def test_update_profile(self):
        """اختبار تحديث الملف الشخصي"""
        data = {
            'phone': '01111111111',
            'bio': 'بايو جديد'
        }
        response = self.client.patch('/api/student/me/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.phone, '01111111111')
    
    def test_unauthorized_access(self):
        """اختبار الوصول بدون تسجيل دخول"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/student/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
