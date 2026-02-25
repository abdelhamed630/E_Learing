"""
Serializers للامتحانات
"""
from rest_framework import serializers
from .models import Exam, Question, Answer, ExamAttempt, StudentAnswer


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer للإجابة - بدون is_correct للطالب"""
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer للسؤال"""
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type',
            'image', 'points', 'order', 'answers'
        ]


class ExamSerializer(serializers.ModelSerializer):
    """Serializer للامتحان (قائمة)"""
    total_questions = serializers.IntegerField(source='total_questions', read_only=True)
    total_points = serializers.IntegerField(source='total_points', read_only=True)
    attempts_used = serializers.SerializerMethodField()
    attempts_left = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'description', 'duration', 'passing_score',
            'max_attempts', 'shuffle_questions', 'show_result_immediately',
            'allow_review', 'total_questions', 'total_points',
            'attempts_used', 'attempts_left', 'best_score'
        ]

    def get_attempts_used(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            return ExamAttempt.objects.filter(
                student=request.user.student_profile,
                exam=obj
            ).exclude(status='in_progress').count()
        return 0

    def get_attempts_left(self, obj):
        return obj.max_attempts - self.get_attempts_used(obj)

    def get_best_score(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            best = ExamAttempt.objects.filter(
                student=request.user.student_profile,
                exam=obj,
                status='graded'
            ).order_by('-score').first()
            return float(best.score) if best else None
        return None


class ExamDetailSerializer(ExamSerializer):
    """Serializer لتفاصيل الامتحان مع الأسئلة"""
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(ExamSerializer.Meta):
        fields = ExamSerializer.Meta.fields + [
            'instructions', 'questions'
        ]


class StartExamSerializer(serializers.Serializer):
    """Serializer لبدء الامتحان"""
    exam_id = serializers.IntegerField(required=True)


class SubmitAnswerSerializer(serializers.Serializer):
    """Serializer لتسليم إجابة سؤال واحد"""
    question_id = serializers.IntegerField(required=True)
    answer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )

    def validate_answer_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("لا يمكن تكرار نفس الإجابة")
        return value


class SubmitExamSerializer(serializers.Serializer):
    """Serializer لتسليم الامتحان كاملاً"""
    answers = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )

    def validate_answers(self, value):
        for item in value:
            if 'question_id' not in item:
                raise serializers.ValidationError("كل إجابة يجب أن تحتوي على question_id")
            if 'answer_ids' not in item:
                raise serializers.ValidationError("كل إجابة يجب أن تحتوي على answer_ids")
            if not isinstance(item['answer_ids'], list) or len(item['answer_ids']) == 0:
                raise serializers.ValidationError("answer_ids يجب أن يكون قائمة غير فارغة")
        return value


class StudentAnswerSerializer(serializers.ModelSerializer):
    """Serializer لإجابة الطالب"""
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    question_points = serializers.IntegerField(source='question.points', read_only=True)
    selected_answers = AnswerSerializer(many=True, read_only=True)
    correct_answers = serializers.SerializerMethodField()
    explanation = serializers.CharField(source='question.explanation', read_only=True)

    class Meta:
        model = StudentAnswer
        fields = [
            'id', 'question', 'question_text', 'question_type',
            'question_points', 'selected_answers', 'correct_answers',
            'is_correct', 'points_earned', 'explanation', 'answered_at'
        ]

    def get_correct_answers(self, obj):
        """إظهار الإجابات الصحيحة بعد التسليم"""
        attempt = obj.attempt
        if (attempt.status == 'graded' and attempt.exam.show_correct_answers):
            answers = obj.question.answers.filter(is_correct=True)
            return AnswerSerializer(answers, many=True).data
        return None


class ExamAttemptSerializer(serializers.ModelSerializer):
    """Serializer لمحاولة الامتحان"""
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    course_title = serializers.CharField(source='exam.course.title', read_only=True)
    time_remaining = serializers.IntegerField(source='time_remaining', read_only=True)
    duration_taken = serializers.IntegerField(source='duration_taken', read_only=True)
    is_expired = serializers.BooleanField(source='is_expired', read_only=True)

    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'exam', 'exam_title', 'course_title',
            'status', 'score', 'points_earned', 'passed',
            'started_at', 'submitted_at', 'expires_at',
            'time_remaining', 'duration_taken', 'is_expired',
            'attempt_number'
        ]
        read_only_fields = [
            'id', 'score', 'points_earned', 'passed',
            'started_at', 'submitted_at', 'expires_at', 'attempt_number'
        ]


class ExamResultSerializer(ExamAttemptSerializer):
    """Serializer لنتيجة الامتحان التفصيلية"""
    student_answers = StudentAnswerSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    correct_count = serializers.SerializerMethodField()
    wrong_count = serializers.SerializerMethodField()
    passing_score = serializers.IntegerField(source='exam.passing_score', read_only=True)

    class Meta(ExamAttemptSerializer.Meta):
        fields = ExamAttemptSerializer.Meta.fields + [
            'student_answers', 'total_questions',
            'correct_count', 'wrong_count', 'passing_score'
        ]

    def get_total_questions(self, obj):
        return obj.exam.total_questions

    def get_correct_count(self, obj):
        return obj.student_answers.filter(is_correct=True).count()

    def get_wrong_count(self, obj):
        return obj.student_answers.filter(is_correct=False).count()
