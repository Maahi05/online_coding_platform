from django.contrib import admin
from .models import Student, Test, Question, Option, TestCase, TestAttempt, Submission, Certificate

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 2

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'question_type', 'marks', 'order')
    list_filter = ('question_type', 'test')
    inlines = [OptionInline, TestCaseInline]

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_minutes', 'total_marks', 'has_negative_marking', 'is_active', 'created_at')
    list_filter = ('is_active', 'has_negative_marking')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'college', 'branch')
    search_fields = ('user__username', 'roll_number', 'college')

@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'score', 'total_marks', 'percentage', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'test')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'marks_awarded', 'is_correct')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_id', 'attempt', 'issued_at')
