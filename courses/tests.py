"""
Tests للكورسات
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from students.models import Student
from .models import Category, Course, Video


class CourseModelTest(TestCase):
    """اختبار نماذج الكورسات"""
    
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='pass123'
        )
        
        self.category = Category.objects.create(
            name='برمجة',
            description='كورسات البرمجة'
        )
        
        self.course = Course.objects.create(
            title='Django للمبتدئين',
            description='تعلم Django',
            category=self.category,
            instructor=self.instructor,
            price=299.99,
            is_published=True
        )
    
    def test_course_creation(self):
        """اختبار إنشاء كورس"""
        self.assertEqual(self.course.title, 'Django للمبتدئين')
        self.assertTrue(self.course.is_published)
    
    def test_course_slug_auto_generate(self):
        """اختبار توليد الـ slug تلقائياً"""
        self.assertIsNotNone(self.course.slug)
    
    def test_final_price_with_discount(self):
        """اختبار السعر النهائي مع الخصم"""
        self.course.discount_price = 199.99
        self.course.save()
        self.assertEqual(self.course.final_price, 199.99)
    
    def test_discount_percentage(self):
        """اختبار نسبة الخصم"""
        self.course.discount_price = 200.00
        self.course.save()
        self.assertEqual(self.course.discount_percentage, 33)


class CourseAPITest(APITestCase):
    """اختبار APIs الكورسات"""
    
    def setUp(self):
        # إنشاء مدرس
        self.instructor = User.objects.create_user(
            username='instructor',
            password='pass123'
        )
        
        # إنشاء طالب
        self.student_user = User.objects.create_user(
            username='student',
            password='pass123'
        )
        self.student = Student.objects.create(user=self.student_user)
        
        # إنشاء كورس
        self.category = Category.objects.create(name='برمجة')
        self.course = Course.objects.create(
            title='Python للمبتدئين',
            description='تعلم Python',
            category=self.category,
            instructor=self.instructor,
            price=199.99,
            is_published=True
        )
    
    def test_list_courses(self):
        """اختبار عرض قائمة الكورسات"""
        response = self.client.get('/api/courses/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_course_detail(self):
        """اختبار عرض تفاصيل الكورس"""
        response = self.client.get(f'/api/courses/courses/{self.course.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Python للمبتدئين')
    
    def test_featured_courses(self):
        """اختبار عرض الكورسات المميزة"""
        self.course.is_featured = True
        self.course.save()
        
        response = self.client.get('/api/courses/courses/featured/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
