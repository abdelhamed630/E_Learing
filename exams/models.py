"""
نماذج الامتحانات
الطالب يحل الامتحانات فقط - لا يعدل ولا ينشئ
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Exam(models.Model):
    """نموذج الامتحان"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('published', 'منشور'),
        ('archived', 'مؤرشف'),
    ]

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name='الكورس'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان الامتحان')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    instructions = models.TextField(blank=True, null=True, verbose_name='تعليمات الامتحان')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='الحالة'
    )

    # إعدادات الامتحان
    duration = models.IntegerField(
        help_text='المدة بالدقائق',
        validators=[MinValueValidator(1)],
        verbose_name='مدة الامتحان (دقائق)'
    )
    passing_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='درجة النجاح %'
    )
    max_attempts = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        verbose_name='عدد المحاولات المسموحة'
    )

    # خيارات الامتحان
    shuffle_questions = models.BooleanField(default=False, verbose_name='خلط الأسئلة')
    shuffle_answers = models.BooleanField(default=False, verbose_name='خلط الإجابات')
    show_result_immediately = models.BooleanField(default=True, verbose_name='إظهار النتيجة فوراً')
    show_correct_answers = models.BooleanField(default=False, verbose_name='إظهار الإجابات الصحيحة')
    allow_review = models.BooleanField(default=True, verbose_name='السماح بمراجعة الإجابات')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        verbose_name = 'امتحان'
        verbose_name_plural = 'الامتحانات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course', 'status']),
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all())

    def is_available(self):
        return self.status == 'published'


class Question(models.Model):
    """نموذج السؤال"""
    QUESTION_TYPES = [
        ('multiple_choice', 'اختيار من متعدد'),
        ('true_false', 'صح أو خطأ'),
        ('multiple_select', 'اختيار متعدد'),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='الامتحان'
    )
    question_text = models.TextField(verbose_name='نص السؤال')
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='multiple_choice',
        verbose_name='نوع السؤال'
    )
    image = models.ImageField(
        upload_to='exams/questions/',
        blank=True,
        null=True,
        verbose_name='صورة السؤال'
    )
    points = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='درجة السؤال'
    )
    order = models.IntegerField(default=0, verbose_name='ترتيب السؤال')
    explanation = models.TextField(
        blank=True,
        null=True,
        verbose_name='شرح الإجابة'
    )

    class Meta:
        verbose_name = 'سؤال'
        verbose_name_plural = 'الأسئلة'
        ordering = ['exam', 'order']
        indexes = [
            models.Index(fields=['exam', 'order']),
        ]

    def __str__(self):
        return f"{self.exam.title} - {self.question_text[:60]}"

    @property
    def correct_answers(self):
        return self.answers.filter(is_correct=True)


class Answer(models.Model):
    """نموذج الإجابة"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='السؤال'
    )
    answer_text = models.CharField(max_length=500, verbose_name='نص الإجابة')
    is_correct = models.BooleanField(default=False, verbose_name='إجابة صحيحة')
    order = models.IntegerField(default=0, verbose_name='الترتيب')

    class Meta:
        verbose_name = 'إجابة'
        verbose_name_plural = 'الإجابات'
        ordering = ['question', 'order']

    def __str__(self):
        return f"{self.question.question_text[:30]} → {self.answer_text[:30]}"


class ExamAttempt(models.Model):
    """نموذج محاولة الامتحان"""
    STATUS_CHOICES = [
        ('in_progress', 'جاري'),
        ('submitted', 'تم التسليم'),
        ('expired', 'منتهية المدة'),
        ('graded', 'تم التصحيح'),
    ]

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='exam_attempts',
        verbose_name='الطالب'
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='الامتحان'
    )
    enrollment = models.ForeignKey(
        'enrollments.Enrollment',
        on_delete=models.CASCADE,
        related_name='exam_attempts',
        verbose_name='التسجيل'
    )

    # الحالة والنتيجة
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name='الحالة'
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='الدرجة %'
    )
    points_earned = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='النقاط المكتسبة'
    )
    passed = models.BooleanField(default=False, verbose_name='ناجح')

    # الوقت
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت البدء')
    submitted_at = models.DateTimeField(blank=True, null=True, verbose_name='وقت التسليم')
    expires_at = models.DateTimeField(verbose_name='وقت الانتهاء')

    # رقم المحاولة
    attempt_number = models.IntegerField(default=1, verbose_name='رقم المحاولة')

    class Meta:
        verbose_name = 'محاولة امتحان'
        verbose_name_plural = 'محاولات الامتحانات'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student} - {self.exam.title} - محاولة {self.attempt_number}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'in_progress'

    @property
    def time_remaining(self):
        """الوقت المتبقي بالثواني"""
        if self.status != 'in_progress':
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    @property
    def duration_taken(self):
        """المدة المستغرقة بالدقائق"""
        if self.submitted_at:
            delta = self.submitted_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None


class StudentAnswer(models.Model):
    """نموذج إجابة الطالب"""
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name='المحاولة'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name='السؤال'
    )
    selected_answers = models.ManyToManyField(
        Answer,
        blank=True,
        verbose_name='الإجابات المختارة'
    )
    is_correct = models.BooleanField(default=False, verbose_name='إجابة صحيحة')
    points_earned = models.IntegerField(default=0, verbose_name='النقاط المكتسبة')
    answered_at = models.DateTimeField(auto_now=True, verbose_name='وقت الإجابة')

    class Meta:
        verbose_name = 'إجابة طالب'
        verbose_name_plural = 'إجابات الطلاب'
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt.student} - {self.question.question_text[:40]}"

    def check_answer(self):
        """التحقق من صحة الإجابة وحساب النقاط"""
        correct_ids = set(
            self.question.answers.filter(is_correct=True).values_list('id', flat=True)
        )
        selected_ids = set(self.selected_answers.values_list('id', flat=True))

        if self.question.question_type == 'multiple_select':
            # يجب تحديد جميع الإجابات الصحيحة
            self.is_correct = correct_ids == selected_ids
        else:
            # يكفي اختيار واحد صحيح
            self.is_correct = bool(selected_ids & correct_ids)

        self.points_earned = self.question.points if self.is_correct else 0
        self.save(update_fields=['is_correct', 'points_earned'])

        return self.is_correct
