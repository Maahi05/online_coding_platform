from django.db import models
from django.contrib.auth.models import User
import uuid

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=50, unique=True)
    college = models.CharField(max_length=150, blank=True, default='')
    branch = models.CharField(max_length=100, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        full_name = self.user.get_full_name()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} ({self.roll_number})"

    def total_tests_taken(self):
        return self.attempts.filter(status__in=['COMPLETED', 'TIMED_OUT']).count()

    def average_score(self):
        attempts = self.attempts.filter(status__in=['COMPLETED', 'TIMED_OUT'])
        if not attempts.exists():
            return 0.0
        avg = attempts.aggregate(models.Avg('percentage'))['percentage__avg']
        return round(avg or 0.0, 2)


class Test(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    total_marks = models.PositiveIntegerField(default=100)
    pass_marks = models.PositiveIntegerField(default=40)
    has_negative_marking = models.BooleanField(default=False)
    negative_marks_per_question = models.FloatField(default=0.25, help_text="Marks deducted per wrong MCQ answer")
    randomize_questions = models.BooleanField(default=True, help_text="Randomize question sequence for each student")
    allow_multiple_attempts = models.BooleanField(default=False, help_text="Allow student to retake test")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def mcq_count(self):
        return self.questions.filter(question_type='MCQ').count()

    @property
    def coding_count(self):
        return self.questions.filter(question_type='CODING').count()

    @property
    def calculated_total_marks(self):
        agg = self.questions.aggregate(models.Sum('marks'))['marks__sum']
        return agg if agg is not None else 0


class Question(models.Model):
    QUESTION_TYPES = (
        ('MCQ', 'Multiple Choice Question'),
        ('CODING', 'Python Coding Question'),
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='MCQ')
    marks = models.PositiveIntegerField(default=5)
    order = models.PositiveIntegerField(default=1)

    # Coding specific fields
    starter_code = models.TextField(blank=True, default='# Write your Python solution here\n')
    problem_constraints = models.TextField(blank=True, default='')
    explanation = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"[{self.question_type}] {self.question_text[:60]}"


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.option_text} ({'Correct' if self.is_correct else 'Incorrect'})"


class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(blank=True, help_text="Standard input passed to program")
    expected_output = models.TextField(help_text="Expected standard output")
    is_sample = models.BooleanField(default=False, help_text="Visible to student during test")

    def __str__(self):
        return f"TestCase #{self.id} for Q{self.question_id} ({'Sample' if self.is_sample else 'Hidden'})"


class TestAttempt(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('TIMED_OUT', 'Timed Out'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0.0)
    total_marks = models.FloatField(default=0.0)
    percentage = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    time_taken_seconds = models.PositiveIntegerField(default=0)
    question_order = models.JSONField(default=list, blank=True, help_text="Assigned randomized question IDs")

    class Meta:
        ordering = ['-score', 'time_taken_seconds', 'completed_at']

    def __str__(self):
        return f"{self.student.user.username} - {self.test.title} ({self.score}/{self.total_marks})"

    @property
    def is_passed(self):
        return self.score >= self.test.pass_marks

    @property
    def formatted_time_taken(self):
        mins = self.time_taken_seconds // 60
        secs = self.time_taken_seconds % 60
        return f"{mins}m {secs}s"


class Submission(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='submissions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    submitted_code = models.TextField(blank=True, default='')
    marks_awarded = models.FloatField(default=0.0)
    is_correct = models.BooleanField(default=False)
    test_cases_passed = models.PositiveIntegerField(default=0)
    total_test_cases = models.PositiveIntegerField(default=0)
    execution_output = models.TextField(blank=True, default='')
    evaluation_details = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Submission: {self.attempt.student.user.username} - Q{self.question_id}"


class Certificate(models.Model):
    attempt = models.OneToOneField(TestAttempt, on_delete=models.CASCADE, related_name='certificate')
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate {self.certificate_id} - {self.attempt.student.user.username}"
