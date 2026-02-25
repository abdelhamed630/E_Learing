"""
Tests للمدفوعات
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from students.models import Student
from courses.models import Course, Category
from .models import Payment, Coupon, CouponUsage, Refund

User = get_user_model()


class PaymentModelTest(TestCase):
    """اختبار نموذج الدفعة"""

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
            price=500,
            is_published=True
        )

        self.payment = Payment.objects.create(
            student=self.student,
            course=self.course,
            amount=500,
            payment_method='credit_card'
        )

    def test_payment_creation(self):
        """اختبار إنشاء دفعة"""
        self.assertIsNotNone(self.payment.transaction_id)
        self.assertEqual(self.payment.status, 'pending')

    def test_mark_as_completed(self):
        """اختبار تحديد الدفعة كمكتملة"""
        self.payment.mark_as_completed()
        self.assertEqual(self.payment.status, 'completed')
        self.assertIsNotNone(self.payment.completed_at)

    def test_can_be_refunded(self):
        """اختبار إمكانية الاسترجاع"""
        self.payment.mark_as_completed()
        self.assertTrue(self.payment.can_be_refunded)


class CouponModelTest(TestCase):
    """اختبار نموذج الكوبون"""

    def setUp(self):
        self.coupon = Coupon.objects.create(
            code='SAVE20',
            discount_type='percentage',
            discount_value=20,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            max_uses=100
        )

    def test_coupon_is_valid(self):
        """اختبار صلاحية الكوبون"""
        is_valid, message = self.coupon.is_valid()
        self.assertTrue(is_valid)

    def test_coupon_expired(self):
        """اختبار كوبون منتهي"""
        self.coupon.valid_until = timezone.now() - timedelta(days=1)
        self.coupon.save()

        is_valid, message = self.coupon.is_valid()
        self.assertFalse(is_valid)

    def test_calculate_discount(self):
        """اختبار حساب الخصم"""
        discount = self.coupon.calculate_discount(1000)
        self.assertEqual(discount, 200)  # 20% من 1000
