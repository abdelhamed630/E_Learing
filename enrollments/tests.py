"""
Tests للتسجيلات
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from students.models import Student
from courses.models import Course, Video, Category
from .models import Enrollment, VideoProgress

User = get_user_model()


class EnrollmentModelTest(TestCase):
    """اختبار نموذج التسجيل"""
    
    def setUp(self):
        # إنشاء مستخدم ومدرس
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='pass123',
            role='student'
        )
        self.student = Student.objects.create(user=self.student_user)
        
        instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='pass123',
            role='instructor'
        )
        
        # إنشاء كورس
        category = Category.objects.create(name='برمجة')
        self.course = Course.objects.create(
            title='Python',
            description='كورس Python',
            category=category,
            instructor=instructor,
            is_published=True
        )
        
        # إنشاء تسجيل
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
    
    def test_enrollment_creation(self):
        """اختبار إنشاء تسجيل"""
        self.assertEqual(self.enrollment.status, 'active')
        self.assertEqual(self.enrollment.progress, 0)
    
    def test_mark_as_started(self):
        """اختبار بدء الكورس"""
        self.enrollment.mark_as_started()
        self.assertIsNotNone(self.enrollment.started_at)
    
    def test_mark_as_completed(self):
        """اختبار إكمال الكورس"""
        self.enrollment.mark_as_completed()
        self.assertEqual(self.enrollment.status, 'completed')
        self.assertEqual(self.enrollment.progress, 100)
        self.assertIsNotNone(self.enrollment.completed_at)


class EnrollmentAPITest(APITestCase):
    """اختبار APIs التسجيلات"""
    
    def setUp(self):
        # إنشاء طالب
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='pass123',
            role='student'
        )
        self.student = Student.objects.create(user=self.student_user)
        
        # إنشاء مدرس وكورس
        instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='pass123',
            role='instructor'
        )
        
        category = Category.objects.create(name='برمجة')
        self.course = Course.objects.create(
            title='Django',
            description='كورس Django',
            category=category,
            instructor=instructor,
            is_published=True
        )
        
        self.client.force_authenticate(user=self.student_user)
    
    def test_enroll_in_course(self):
        """اختبار التسجيل في كورس"""
        response = self.client.post('/api/enrollments/enrollments/enroll/', {
            'course_id': self.course.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course
            ).exists()
        )
    
    def test_duplicate_enrollment(self):
        """اختبار التسجيل المكرر"""
        Enrollment.objects.create(student=self.student, course=self.course)
        
        response = self.client.post('/api/enrollments/enrollments/enroll/', {
            'course_id': self.course.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
