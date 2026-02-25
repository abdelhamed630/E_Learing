"""
Tests للامتحانات
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from students.models import Student
from courses.models import Course, Category
from enrollments.models import Enrollment
from .models import Exam, Question, Answer, ExamAttempt, StudentAnswer

User = get_user_model()


class ExamModelTest(TestCase):
    """اختبار نماذج الامتحانات"""

    def setUp(self):
        instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='pass123',
            role='instructor'
        )
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='pass123',
            role='student'
        )
        self.student = Student.objects.create(user=self.student_user)

        category = Category.objects.create(name='برمجة')
        self.course = Course.objects.create(
            title='Django',
            description='كورس Django',
            category=category,
            instructor=instructor,
            is_published=True
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )

        self.exam = Exam.objects.create(
            course=self.course,
            title='اختبار Django',
            duration=30,
            passing_score=60,
            max_attempts=3,
            status='published'
        )

        self.question = Question.objects.create(
            exam=self.exam,
            question_text='ما هو Django؟',
            question_type='multiple_choice',
            points=10
        )

        self.correct_answer = Answer.objects.create(
            question=self.question,
            answer_text='إطار عمل Python',
            is_correct=True
        )
        self.wrong_answer = Answer.objects.create(
            question=self.question,
            answer_text='لغة برمجة',
            is_correct=False
        )

    def test_exam_properties(self):
        """اختبار خصائص الامتحان"""
        self.assertEqual(self.exam.total_questions, 1)
        self.assertEqual(self.exam.total_points, 10)
        self.assertTrue(self.exam.is_available())

    def test_correct_answer(self):
        """اختبار تصحيح إجابة صحيحة"""
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            enrollment=self.enrollment,
            attempt_number=1,
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        student_answer = StudentAnswer.objects.create(
            attempt=attempt,
            question=self.question
        )
        student_answer.selected_answers.set([self.correct_answer])
        is_correct = student_answer.check_answer()

        self.assertTrue(is_correct)
        self.assertEqual(student_answer.points_earned, 10)

    def test_wrong_answer(self):
        """اختبار تصحيح إجابة خاطئة"""
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            enrollment=self.enrollment,
            attempt_number=1,
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        student_answer = StudentAnswer.objects.create(
            attempt=attempt,
            question=self.question
        )
        student_answer.selected_answers.set([self.wrong_answer])
        is_correct = student_answer.check_answer()

        self.assertFalse(is_correct)
        self.assertEqual(student_answer.points_earned, 0)

    def test_attempt_expiry(self):
        """اختبار انتهاء مدة المحاولة"""
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            enrollment=self.enrollment,
            attempt_number=1,
            expires_at=timezone.now() - timedelta(minutes=1)  # منتهية
        )

        self.assertTrue(attempt.is_expired)
        self.assertEqual(attempt.time_remaining, 0)


class ExamAPITest(APITestCase):
    """اختبار APIs الامتحانات"""

    def setUp(self):
        instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='pass123',
            role='instructor'
        )
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='pass123',
            role='student'
        )
        self.student = Student.objects.create(user=self.student_user)

        category = Category.objects.create(name='برمجة')
        self.course = Course.objects.create(
            title='Django',
            description='كورس',
            category=category,
            instructor=instructor,
            is_published=True
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        self.exam = Exam.objects.create(
            course=self.course,
            title='اختبار',
            duration=30,
            passing_score=60,
            max_attempts=3,
            status='published'
        )

        self.client.force_authenticate(user=self.student_user)

    def test_list_exams(self):
        """اختبار عرض قائمة الامتحانات"""
        response = self.client.get('/api/exams/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_start_exam(self):
        """اختبار بدء امتحان"""
        response = self.client.post(f'/api/exams/{self.exam.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('attempt', response.data)

    def test_cant_start_exam_without_enrollment(self):
        """اختبار منع بدء امتحان بدون تسجيل"""
        other_user = User.objects.create_user(
            username='other',
            email='other@test.com',
            password='pass123',
            role='student'
        )
        Student.objects.create(user=other_user)
        self.client.force_authenticate(user=other_user)

        response = self.client.post(f'/api/exams/{self.exam.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
