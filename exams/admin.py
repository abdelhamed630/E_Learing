"""
Admin للامتحانات
"""
from django.contrib import admin
from .models import Exam, Question, Answer, ExamAttempt, StudentAnswer


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ['answer_text', 'is_correct', 'order']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['question_text', 'question_type', 'points', 'order']
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'status', 'duration',
        'passing_score', 'max_attempts', 'total_questions', 'created_at'
    ]
    list_filter = ['status', 'course', 'created_at']
    search_fields = ['title', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuestionInline]

    fieldsets = (
        ('معلومات الامتحان', {
            'fields': ('course', 'title', 'description', 'instructions', 'status')
        }),
        ('الإعدادات', {
            'fields': ('duration', 'passing_score', 'max_attempts')
        }),
        ('الخيارات', {
            'fields': (
                'shuffle_questions', 'shuffle_answers',
                'show_result_immediately', 'show_correct_answers', 'allow_review'
            )
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_questions(self, obj):
        return obj.total_questions
    total_questions.short_description = 'عدد الأسئلة'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_text_short', 'question_type', 'points', 'order']
    list_filter = ['question_type', 'exam__course', 'exam']
    search_fields = ['question_text', 'exam__title']
    inlines = [AnswerInline]

    def question_text_short(self, obj):
        return obj.question_text[:60]
    question_text_short.short_description = 'السؤال'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'answer_text_short', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__exam']
    search_fields = ['answer_text', 'question__question_text']

    def answer_text_short(self, obj):
        return obj.answer_text[:50]
    answer_text_short.short_description = 'الإجابة'


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ['question', 'is_correct', 'points_earned', 'answered_at']
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'exam', 'attempt_number', 'status',
        'score', 'passed', 'started_at', 'submitted_at'
    ]
    list_filter = ['status', 'passed', 'started_at']
    search_fields = [
        'student__user__username',
        'student__user__email',
        'exam__title'
    ]
    readonly_fields = [
        'started_at', 'submitted_at', 'score',
        'points_earned', 'passed', 'attempt_number'
    ]
    inlines = [StudentAnswerInline]

    def has_add_permission(self, request):
        return False
