"""
Views للامتحانات
الطالب: يحل الامتحانات فقط - لا ينشئ ولا يعدل
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction, models as django_models
from django.core.cache import cache
from datetime import timedelta
from students.permissions import IsStudent
from enrollments.models import Enrollment
from .models import Exam, Question, Answer, ExamAttempt, StudentAnswer
from .serializers import (
    ExamSerializer, ExamDetailSerializer,
    ExamAttemptSerializer, ExamResultSerializer,
    SubmitExamSerializer
)
from .permissions import (
    IsEnrolledInCourse, HasAttemptsLeft,
    IsAttemptOwner, IsAttemptInProgress
)
from .tasks import grade_exam_attempt, auto_submit_attempt


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet للامتحانات
    الطالب: مشاهدة وحل فقط (Read-Only على بيانات الامتحان)
    """
    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExamDetailSerializer
        return ExamSerializer

    def get_queryset(self):
        """
        إظهار امتحانات الكورسات المسجل فيها الطالب فقط
        """
        student = self.request.user.student_profile

        # الكورسات المسجل فيها الطالب
        enrolled_courses = Enrollment.objects.filter(
            student=student,
            status='active'
        ).values_list('course_id', flat=True)

        return Exam.objects.filter(
            course__in=enrolled_courses,
            status='published'
        ).select_related('course').prefetch_related('questions__answers')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """عرض تفاصيل الامتحان مع كاش"""
        exam = self.get_object()
        student = request.user.student_profile

        cache_key = f'exam_detail_{exam.id}_student_{student.id}'
        cached = cache.get(cache_key)

        if cached:
            return Response(cached)

        serializer = ExamDetailSerializer(exam, context={'request': request})
        data = serializer.data

        # خلط الأسئلة لو مفعّل
        if exam.shuffle_questions:
            import random
            questions = data.get('questions', [])
            random.shuffle(questions)
            data['questions'] = questions

            if exam.shuffle_answers:
                for question in data['questions']:
                    random.shuffle(question['answers'])

        cache.set(cache_key, data, 300)
        return Response(data)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated, IsStudent,
                                 IsEnrolledInCourse, HasAttemptsLeft])
    def start(self, request, pk=None):
        """
        بدء محاولة امتحان جديدة
        الطالب يبدأ الامتحان هنا
        """
        exam = self.get_object()
        student = request.user.student_profile

        # التحقق من عدم وجود محاولة جارية
        active_attempt = ExamAttempt.objects.filter(
            student=student,
            exam=exam,
            status='in_progress'
        ).first()

        if active_attempt:
            if active_attempt.is_expired:
                # تسليم تلقائي للمحاولة المنتهية
                auto_submit_attempt.delay(active_attempt.id)
            else:
                # إرجاع المحاولة الجارية
                serializer = ExamAttemptSerializer(active_attempt)
                return Response({
                    'message': 'لديك محاولة جارية بالفعل',
                    'attempt': serializer.data
                }, status=status.HTTP_200_OK)

        # الحصول على التسجيل
        enrollment = Enrollment.objects.get(
            student=student,
            course=exam.course,
            status='active'
        )

        # حساب رقم المحاولة
        attempt_number = ExamAttempt.objects.filter(
            student=student,
            exam=exam
        ).count() + 1

        # إنشاء المحاولة
        attempt = ExamAttempt.objects.create(
            student=student,
            exam=exam,
            enrollment=enrollment,
            attempt_number=attempt_number,
            expires_at=timezone.now() + timedelta(minutes=exam.duration),
            status='in_progress'
        )

        serializer = ExamAttemptSerializer(attempt)
        return Response({
            'message': 'تم بدء الامتحان بنجاح',
            'attempt': serializer.data,
            'time_limit_minutes': exam.duration
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'],
            url_path='attempts/(?P<attempt_id>[^/.]+)/submit',
            permission_classes=[IsAuthenticated, IsStudent])
    def submit(self, request, attempt_id=None):
        """
        تسليم الامتحان
        الطالب يسلم إجاباته هنا
        """
        student = request.user.student_profile

        try:
            attempt = ExamAttempt.objects.get(
                id=attempt_id,
                student=student
            )
        except ExamAttempt.DoesNotExist:
            return Response(
                {'error': 'المحاولة غير موجودة'},
                status=status.HTTP_404_NOT_FOUND
            )

        # التحقق من الحالة
        if attempt.status != 'in_progress':
            return Response(
                {'error': 'هذه المحاولة تم تسليمها بالفعل'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # التحقق من انتهاء الوقت
        if attempt.is_expired:
            auto_submit_attempt.delay(attempt.id)
            return Response(
                {'error': 'انتهى وقت الامتحان وتم التسليم تلقائياً'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # التحقق من البيانات
        serializer = SubmitExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # حفظ إجابات الطالب
            for answer_data in serializer.validated_data['answers']:
                question_id = answer_data['question_id']
                answer_ids = answer_data['answer_ids']

                try:
                    question = Question.objects.get(
                        id=question_id,
                        exam=attempt.exam
                    )
                    answers = Answer.objects.filter(
                        id__in=answer_ids,
                        question=question
                    )

                    student_answer, created = StudentAnswer.objects.get_or_create(
                        attempt=attempt,
                        question=question
                    )
                    student_answer.selected_answers.set(answers)
                    student_answer.save()

                except Question.DoesNotExist:
                    continue

            # تحديث حالة المحاولة
            attempt.status = 'submitted'
            attempt.submitted_at = timezone.now()
            attempt.save()

        # تصحيح الامتحان في الخلفية
        grade_exam_attempt.delay(attempt.id)

        return Response({
            'message': 'تم تسليم الامتحان بنجاح',
            'attempt_id': attempt.id
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'],
            url_path='attempts/(?P<attempt_id>[^/.]+)/result',
            permission_classes=[IsAuthenticated, IsStudent])
    def result(self, request, attempt_id=None):
        """
        عرض نتيجة محاولة
        """
        student = request.user.student_profile

        try:
            attempt = ExamAttempt.objects.get(
                id=attempt_id,
                student=student
            )
        except ExamAttempt.DoesNotExist:
            return Response(
                {'error': 'المحاولة غير موجودة'},
                status=status.HTTP_404_NOT_FOUND
            )

        if attempt.status not in ['graded', 'submitted']:
            return Response(
                {'error': 'النتيجة غير جاهزة بعد'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExamResultSerializer(attempt, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated, IsStudent])
    def my_attempts(self, request):
        """
        جميع محاولات الطالب
        """
        student = request.user.student_profile

        attempts = ExamAttempt.objects.filter(
            student=student
        ).select_related('exam', 'exam__course').order_by('-started_at')

        # فلترة حسب الامتحان
        exam_id = request.query_params.get('exam_id')
        if exam_id:
            attempts = attempts.filter(exam_id=exam_id)

        serializer = ExamAttemptSerializer(attempts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'],
            permission_classes=[IsAuthenticated, IsStudent])
    def my_stats(self, request, pk=None):
        """
        إحصائيات الطالب في امتحان معين
        """
        exam = self.get_object()
        student = request.user.student_profile

        attempts = ExamAttempt.objects.filter(
            student=student,
            exam=exam
        ).exclude(status='in_progress')

        if not attempts.exists():
            return Response({'message': 'لا توجد محاولات سابقة'})

        best = attempts.order_by('-score').first()
        latest = attempts.order_by('-started_at').first()

        stats = {
            'total_attempts': attempts.count(),
            'attempts_left': exam.max_attempts - attempts.count(),
            'best_score': float(best.score) if best.score else 0,
            'best_passed': best.passed,
            'latest_score': float(latest.score) if latest.score else 0,
            'average_score': float(
                attempts.filter(score__isnull=False).aggregate(
                    django_models.Avg('score')
                )['score__avg'] or 0
            ),
            'passed_count': attempts.filter(passed=True).count(),
        }

        return Response(stats)


class InstructorExamViewSet(viewsets.ModelViewSet):
    """ViewSet للمدرب - إدارة الامتحانات كاملة"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import InstructorExamSerializer
        return InstructorExamSerializer

    def get_queryset(self):
        return Exam.objects.filter(
            course__instructor=self.request.user
        ).select_related('course').prefetch_related(
            'questions__answers', 'attempts'
        ).order_by('-created_at')

    def perform_create(self, serializer):
        # التحقق إن الـ course تاعت المدرب
        course_id = self.request.data.get('course')
        if course_id:
            from courses.models import Course
            try:
                course = Course.objects.get(pk=course_id, instructor=self.request.user)
            except Course.DoesNotExist:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('هذا الكورس ليس من كورساتك')
        serializer.save()

    # ── نشر / إلغاء نشر الامتحان ──
    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        exam = self.get_object()
        if exam.status == 'published':
            exam.status = 'draft'
            msg = 'تم إلغاء نشر الامتحان'
        else:
            if not exam.questions.exists():
                return Response(
                    {'error': 'لا يمكن نشر امتحان بدون أسئلة'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            exam.status = 'published'
            msg = 'تم نشر الامتحان بنجاح'
        exam.save()
        return Response({'message': msg, 'status': exam.status})

    # ── إحصائيات الامتحان ──
    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        exam = self.get_object()
        attempts = ExamAttempt.objects.filter(exam=exam).exclude(status='in_progress')
        passed = attempts.filter(passed=True).count()
        total  = attempts.count()
        scores = [float(a.score or 0) for a in attempts]
        return Response({
            'total_attempts': total,
            'passed':         passed,
            'failed':         total - passed,
            'pass_rate':      round(passed / total * 100, 1) if total else 0,
            'avg_score':      round(sum(scores) / len(scores), 1) if scores else 0,
            'max_score':      max(scores) if scores else 0,
            'min_score':      min(scores) if scores else 0,
        })

    # ── إضافة سؤال لامتحان ──
    @action(detail=True, methods=['post'], url_path='questions')
    def add_question(self, request, pk=None):
        from .serializers import QuestionWriteSerializer
        exam = self.get_object()
        data = {**request.data, 'exam': exam.id}
        serializer = QuestionWriteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            question = serializer.save(exam=exam)
            from .serializers import QuestionSerializer
            return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── تعديل سؤال ──
    @action(detail=True, methods=['patch', 'delete'], url_path='questions/(?P<question_id>[^/.]+)')
    def manage_question(self, request, pk=None, question_id=None):
        exam = self.get_object()
        try:
            question = Question.objects.get(id=question_id, exam=exam)
        except Question.DoesNotExist:
            return Response({'error': 'السؤال غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        from .serializers import QuestionWriteSerializer
        serializer = QuestionWriteSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            from .serializers import QuestionSerializer
            return Response(QuestionSerializer(question).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── نتائج الطلاب في امتحان ──
    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, pk=None):
        from .serializers import InstructorAttemptSerializer
        exam = self.get_object()
        attempts = ExamAttempt.objects.filter(
            exam=exam
        ).exclude(status='in_progress').select_related(
            'student__user'
        ).prefetch_related('student_answers__selected_answers', 'student_answers__question__answers').order_by('-score')
        serializer = InstructorAttemptSerializer(attempts, many=True)
        return Response(serializer.data)

    # ── تفاصيل محاولة طالب ──
    @action(detail=True, methods=['get'], url_path='results/(?P<attempt_id>[^/.]+)')
    def attempt_detail(self, request, pk=None, attempt_id=None):
        from .serializers import InstructorAttemptSerializer
        exam = self.get_object()
        try:
            attempt = ExamAttempt.objects.get(
                id=attempt_id, exam=exam
            ).select_related('student__user')
        except ExamAttempt.DoesNotExist:
            return Response({'error': 'المحاولة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        serializer = InstructorAttemptSerializer(attempt)
        return Response(serializer.data)
