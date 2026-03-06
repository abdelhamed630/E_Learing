"""
Views للامتحانات
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction

from students.permissions import IsStudent
from .models import Exam, Question, Answer, ExamAttempt, StudentAnswer
from .tasks import auto_submit_attempt
from .serializers import (
    ExamSerializer, ExamDetailSerializer,
    SubmitExamSerializer, ExamResultSerializer, ExamAttemptSerializer
)


# ═══════════════════════════════════════════════════
#  STUDENT — قراءة وحل الامتحانات
# ═══════════════════════════════════════════════════
class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExamDetailSerializer
        return ExamSerializer

    def get_queryset(self):
        student = self.request.user.student_profile
        # الامتحانات المتاحة للطالب (الكورسات المسجل فيها)
        from enrollments.models import Enrollment
        enrolled_courses = Enrollment.objects.filter(
            student=student, status='active'
        ).values_list('course_id', flat=True)
        return Exam.objects.filter(
            course__in=enrolled_courses,
            status='published'
        ).select_related('course')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated and hasattr(self.request.user, 'student_profile'):
            context['student'] = self.request.user.student_profile
        return context

    # POST /exams/{id}/start/
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        exam = self.get_object()
        student = request.user.student_profile

        # التحقق من المحاولات المتبقية
        attempts_used = ExamAttempt.objects.filter(
            student=student, exam=exam
        ).exclude(status='in_progress').count()

        if attempts_used >= exam.max_attempts:
            return Response({'error': 'لقد استنفدت جميع محاولاتك'}, status=status.HTTP_400_BAD_REQUEST)

        # إنهاء أي محاولة سابقة في التقدم
        ExamAttempt.objects.filter(student=student, exam=exam, status='in_progress').update(status='submitted')

        attempt = ExamAttempt.objects.create(
            student=student,
            exam=exam,
            attempt_number=attempts_used + 1,
            status='in_progress',
        )

        return Response({
            'attempt': ExamAttemptSerializer(attempt).data,
            'exam': ExamDetailSerializer(exam, context=self.get_serializer_context()).data,
            'time_limit_minutes': exam.duration,
        }, status=status.HTTP_201_CREATED)

    # POST /exams/attempts/{attempt_id}/submit/
    @action(detail=False, methods=['post'], url_path='attempts/(?P<attempt_id>[^/.]+)/submit')
    def submit(self, request, attempt_id=None):
        student = request.user.student_profile
        try:
            attempt = ExamAttempt.objects.get(id=attempt_id, student=student)
        except ExamAttempt.DoesNotExist:
            return Response({'error': 'المحاولة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status != 'in_progress':
            return Response({'error': 'هذه المحاولة تم تسليمها بالفعل'}, status=status.HTTP_400_BAD_REQUEST)

        if attempt.is_expired:
            auto_submit_attempt.delay(attempt.id)
            return Response({'error': 'انتهى وقت الامتحان وتم التسليم تلقائياً'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            total_points = 0
            earned_points = 0

            for answer_data in serializer.validated_data.get('answers', []):
                try:
                    question = Question.objects.get(id=answer_data['question_id'], exam=attempt.exam)
                    answers = Answer.objects.filter(id__in=answer_data['answer_ids'], question=question)
                    correct_answers = question.answers.filter(is_correct=True)

                    selected_ids = set(answers.values_list('id', flat=True))
                    correct_ids  = set(correct_answers.values_list('id', flat=True))
                    is_correct   = selected_ids == correct_ids and bool(selected_ids)
                    pts          = question.points if is_correct else 0

                    student_answer = StudentAnswer.objects.create(
                        attempt=attempt, question=question,
                        is_correct=is_correct, points_earned=pts
                    )
                    student_answer.selected_answers.set(answers)

                    total_points  += question.points
                    earned_points += pts
                except Question.DoesNotExist:
                    continue

            # حساب الدرجة
            score = (earned_points / total_points * 100) if total_points > 0 else 0
            passed = score >= attempt.exam.passing_score

            attempt.status        = 'graded'
            attempt.score         = score
            attempt.points_earned = earned_points
            attempt.passed        = passed
            attempt.save()

        return Response({
            'score': round(score, 1),
            'passed': passed,
            'points_earned': earned_points,
            'total_points': total_points,
            'attempt_id': attempt.id,
        })

    # GET /exams/attempts/{attempt_id}/result/
    @action(detail=False, methods=['get'], url_path='attempts/(?P<attempt_id>[^/.]+)/result')
    def result(self, request, attempt_id=None):
        student = request.user.student_profile
        try:
            attempt = ExamAttempt.objects.get(id=attempt_id, student=student)
        except ExamAttempt.DoesNotExist:
            return Response({'error': 'المحاولة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status not in ['graded', 'submitted']:
            return Response({'error': 'النتيجة غير جاهزة بعد'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ExamResultSerializer(attempt, context={'request': request}).data)

    # GET /exams/my_attempts/
    @action(detail=False, methods=['get'])
    def my_attempts(self, request):
        student = request.user.student_profile
        attempts = ExamAttempt.objects.filter(
            student=student
        ).select_related('exam__course').order_by('-started_at')
        return Response(ExamAttemptSerializer(attempts, many=True).data)

    # GET /exams/{id}/my_stats/
    @action(detail=True, methods=['get'])
    def my_stats(self, request, pk=None):
        exam = self.get_object()
        student = request.user.student_profile
        attempts = ExamAttempt.objects.filter(
            student=student, exam=exam
        ).exclude(status='in_progress').order_by('-started_at')
        best = attempts.order_by('-score').first()
        return Response({
            'attempts_used': attempts.count(),
            'attempts_left': max(0, exam.max_attempts - attempts.count()),
            'best_score': best.score if best else None,
            'passed': best.passed if best else False,
            'last_attempt': ExamAttemptSerializer(attempts.first()).data if attempts.exists() else None,
        })


# ═══════════════════════════════════════════════════
#  INSTRUCTOR — إدارة الامتحانات والنتائج
# ═══════════════════════════════════════════════════
class InstructorExamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from .serializers import InstructorExamSerializer
        return InstructorExamSerializer

    def get_queryset(self):
        return Exam.objects.filter(
            course__instructor=self.request.user
        ).select_related('course').prefetch_related(
            'questions__answers'
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()

    # ── نشر / سحب الامتحان ──
    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        exam = self.get_object()
        exam.status = 'published' if exam.status != 'published' else 'draft'
        exam.save()
        return Response({'status': exam.status, 'message': 'تم تحديث حالة الامتحان ✅'})

    # ── إضافة سؤال ──
    @action(detail=True, methods=['post'], url_path='questions')
    def add_question(self, request, pk=None):
        from .serializers import QuestionWriteSerializer, QuestionSerializer
        exam = self.get_object()
        serializer = QuestionWriteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            question = serializer.save(exam=exam)
            return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── تعديل / حذف سؤال ──
    @action(detail=True, methods=['patch', 'delete'], url_path='questions/(?P<question_id>[^/.]+)')
    def manage_question(self, request, pk=None, question_id=None):
        from .serializers import QuestionWriteSerializer, QuestionSerializer
        exam = self.get_object()
        try:
            question = Question.objects.get(id=question_id, exam=exam)
        except Question.DoesNotExist:
            return Response({'error': 'السؤال غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = QuestionWriteSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(QuestionSerializer(question).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── نتائج الطلاب ──
    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, pk=None):
        from .serializers import InstructorAttemptSerializer
        exam = self.get_object()
        attempts = ExamAttempt.objects.filter(
            exam=exam
        ).exclude(status='in_progress').select_related('student__user').prefetch_related(
            'student_answers__selected_answers',
            'student_answers__question__answers'
        ).order_by('-score')
        return Response(InstructorAttemptSerializer(attempts, many=True).data)

    # ── تفاصيل محاولة طالب ──
    @action(detail=True, methods=['get'], url_path='results/(?P<attempt_id>[^/.]+)')
    def attempt_detail(self, request, pk=None, attempt_id=None):
        from .serializers import InstructorAttemptSerializer
        exam = self.get_object()
        try:
            attempt = ExamAttempt.objects.select_related('student__user').prefetch_related(
                'student_answers__selected_answers',
                'student_answers__question__answers'
            ).get(id=attempt_id, exam=exam)
        except ExamAttempt.DoesNotExist:
            return Response({'error': 'المحاولة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        return Response(InstructorAttemptSerializer(attempt).data)

    # ── إحصائيات الامتحان ──
    @action(detail=True, methods=['get'], url_path='stats')
    def exam_stats(self, request, pk=None):
        exam = self.get_object()
        attempts = ExamAttempt.objects.filter(exam=exam).exclude(status='in_progress')
        total = attempts.count()
        passed = attempts.filter(passed=True).count()
        scores = list(attempts.values_list('score', flat=True))
        avg = sum(float(s) for s in scores) / len(scores) if scores else 0
        return Response({
            'total_attempts': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': round(passed / total * 100, 1) if total else 0,
            'average_score': round(avg, 1),
            'highest_score': max((float(s) for s in scores), default=0),
            'lowest_score': min((float(s) for s in scores), default=0),
        })
