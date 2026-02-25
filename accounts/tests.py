"""
Tests للحسابات
"""
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User, Profile


class UserModelTest(TestCase):
    """اختبار نموذج المستخدم"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )
    
    def test_user_creation(self):
        """اختبار إنشاء مستخدم"""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_verified)
    
    def test_profile_auto_creation(self):
        """اختبار إنشاء Profile تلقائياً"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, Profile)
    
    def test_full_name_property(self):
        """اختبار خاصية full_name"""
        self.user.first_name = 'أحمد'
        self.user.last_name = 'محمد'
        self.user.save()
        self.assertEqual(self.user.full_name, 'أحمد محمد')
    
    def test_is_student_method(self):
        """اختبار method is_student"""
        self.assertTrue(self.user.is_student())
        self.assertFalse(self.user.is_instructor())


class AuthenticationAPITest(APITestCase):
    """اختبار APIs المصادقة"""
    
    def test_register(self):
        """اختبار التسجيل"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'first_name': 'أحمد',
            'last_name': 'محمد',
            'role': 'student'
        }
        
        response = self.client.post('/api/accounts/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
    
    def test_login(self):
        """اختبار تسجيل الدخول"""
        # إنشاء مستخدم
        user = User.objects.create_user(
            username='testlogin',
            email='login@example.com',
            password='pass123'
        )
        
        data = {
            'email': 'login@example.com',
            'password': 'pass123'
        }
        
        response = self.client.post('/api/accounts/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
    
    def test_login_invalid_credentials(self):
        """اختبار تسجيل دخول ببيانات خاطئة"""
        data = {
            'email': 'wrong@example.com',
            'password': 'wrongpass'
        }
        
        response = self.client.post('/api/accounts/login/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_profile_view_authenticated(self):
        """اختبار عرض الملف الشخصي"""
        user = User.objects.create_user(
            username='profile_test',
            email='profile@example.com',
            password='pass123'
        )
        
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/accounts/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@example.com')
    
    def test_profile_view_unauthenticated(self):
        """اختبار عرض الملف بدون مصادقة"""
        response = self.client.get('/api/accounts/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
