import csv
import json
import random
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Avg, Count, Max

from .models import (
    Student, Test, Question, Option, TestCase,
    TestAttempt, Submission, Certificate
)
from .forms import (
    StudentRegistrationForm, TestForm, MCQQuestionForm, CodingQuestionForm
)
from .sandbox import execute_test_case, evaluate_coding_question
from .certificate_generator import generate_certificate_pdf


def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# -------------------------------------------------------------
# Home & Public Views
# -------------------------------------------------------------
def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('student_dashboard')
    
    recent_tests = Test.objects.filter(is_active=True)[:4]
    return render(request, 'assessment/home.html', {
        'recent_tests': recent_tests
    })


# -------------------------------------------------------------
# Authentication Views
# -------------------------------------------------------------
def student_register(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            student = form.save(commit=False)
            student.user = user
            student.save()

            login(request, user)
            messages.success(request, f"Welcome {user.first_name}! Your account has been registered successfully.")
            return redirect('student_dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'assessment/register.html', {'form': form})


def student_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('student_dashboard')

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'assessment/login.html')


def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            messages.success(request, "Logged in as Administrator.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid credentials or unauthorized account.")

    return render(request, 'assessment/admin_login.html')


def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('home')


# -------------------------------------------------------------
# Student Module Views
# -------------------------------------------------------------
@login_required
def student_dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    student, _ = Student.objects.get_or_create(user=request.user, defaults={'roll_number': f"ROLL-{request.user.id}"})
    
    # Active tests available
    available_tests = Test.objects.filter(is_active=True).order_by('-created_at')
    
    # Completed attempts
    attempts = student.attempts.all().order_by('-started_at')
    completed_attempts = attempts.filter(status__in=['COMPLETED', 'TIMED_OUT'])
    
    # Stats
    tests_taken = completed_attempts.count()
    avg_score = student.average_score()
    passed_tests = sum(1 for a in completed_attempts if a.is_passed)

    # Performance Analytics for Chart.js
    chart_labels = [a.test.title[:15] + '...' for a in reversed(completed_attempts[:6])]
    chart_scores = [float(a.percentage) for a in reversed(completed_attempts[:6])]

    # Map of tests already attempted by student
    attempted_test_ids = set(completed_attempts.values_list('test_id', flat=True))

    return render(request, 'assessment/student_dashboard.html', {
        'student': student,
        'available_tests': available_tests,
        'attempts': attempts[:8],
        'tests_taken': tests_taken,
        'avg_score': avg_score,
        'passed_tests': passed_tests,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
        'attempted_test_ids': attempted_test_ids,
    })


@login_required
def start_test(request, test_id):
    if request.user.is_staff:
        messages.warning(request, "Administrators cannot take tests as students.")
        return redirect('admin_dashboard')

    test = get_object_or_404(Test, id=test_id, is_active=True)
    student, _ = Student.objects.get_or_create(user=request.user, defaults={'roll_number': f"ROLL-{request.user.id}"})

    # Check multiple submissions policy
    existing_completed = TestAttempt.objects.filter(
        student=student, test=test, status__in=['COMPLETED', 'TIMED_OUT']
    ).first()
    if existing_completed and not test.allow_multiple_attempts:
        messages.warning(request, f"Multiple submissions for '{test.title}' are not permitted.")
        return redirect('test_result', attempt_id=existing_completed.id)

    # Resume active attempt or create a new one
    active_attempt = TestAttempt.objects.filter(student=student, test=test, status='IN_PROGRESS').first()
    if not active_attempt:
        # Determine question order (Randomized if enabled)
        question_ids = list(test.questions.values_list('id', flat=True))
        if test.randomize_questions:
            random.shuffle(question_ids)

        active_attempt = TestAttempt.objects.create(
            student=student,
            test=test,
            total_marks=test.calculated_total_marks,
            question_order=question_ids
        )

    return redirect('take_test', attempt_id=active_attempt.id)


@login_required
def take_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user)

    if attempt.status != 'IN_PROGRESS':
        return redirect('test_result', attempt_id=attempt.id)

    # Check timer expiry
    duration_delta = timedelta(minutes=attempt.test.duration_minutes)
    end_time = attempt.started_at + duration_delta
    now = timezone.now()

    if now >= end_time:
        # Auto submit on timeout
        return redirect('submit_test', attempt_id=attempt.id)

    seconds_remaining = max(0, int((end_time - now).total_seconds()))

    # Retrieve questions according to assigned random question_order
    question_ids = attempt.question_order
    if not question_ids:
        question_ids = list(attempt.test.questions.values_list('id', flat=True))
        attempt.question_order = question_ids
        attempt.save(update_fields=['question_order'])

    questions_dict = {q.id: q for q in attempt.test.questions.prefetch_related('options', 'test_cases').all()}
    ordered_questions = [questions_dict[qid] for qid in question_ids if qid in questions_dict]

    # Pre-fetch existing submissions to populate answers
    submissions = {s.question_id: s for s in attempt.submissions.all()}

    questions_payload = []
    for idx, q in enumerate(ordered_questions, start=1):
        sub = submissions.get(q.id)
        q_data = {
            'number': idx,
            'id': q.id,
            'text': q.question_text,
            'type': q.question_type,
            'marks': q.marks,
            'starter_code': q.starter_code or '# Write your Python solution here\n',
            'problem_constraints': q.problem_constraints,
            'answered': False,
            'selected_option': None,
            'submitted_code': '',
            'options': [],
            'sample_test_case': None
        }

        if q.question_type == 'MCQ':
            q_data['options'] = [{'id': opt.id, 'text': opt.option_text} for opt in q.options.all()]
            if sub and sub.selected_option_id:
                q_data['answered'] = True
                q_data['selected_option'] = sub.selected_option_id
        else:
            sample_tc = q.test_cases.filter(is_sample=True).first()
            if sample_tc:
                q_data['sample_test_case'] = {
                    'input': sample_tc.input_data,
                    'output': sample_tc.expected_output
                }
            if sub and sub.submitted_code:
                q_data['answered'] = True
                q_data['submitted_code'] = sub.submitted_code

        questions_payload.append(q_data)

    return render(request, 'assessment/take_test.html', {
        'attempt': attempt,
        'test': attempt.test,
        'seconds_remaining': seconds_remaining,
        'questions_payload_json': json.dumps(questions_payload),
    })


@login_required
def api_save_answer(request):
    """AJAX autosave endpoint for individual question answers."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        selected_option_id = data.get('selected_option_id')
        code_text = data.get('code_text')

        attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user, status='IN_PROGRESS')
        question = get_object_or_404(Question, id=question_id, test=attempt.test)

        submission, _ = Submission.objects.get_or_create(attempt=attempt, question=question)

        if question.question_type == 'MCQ':
            if selected_option_id:
                option = get_object_or_404(Option, id=selected_option_id, question=question)
                submission.selected_option = option
            else:
                submission.selected_option = None
        else:
            submission.submitted_code = code_text or ''

        submission.save()
        return JsonResponse({'status': 'saved'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_run_code(request):
    """AJAX endpoint to run code against sample test cases during the test."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        code = data.get('code', '')

        question = get_object_or_404(Question, id=question_id)
        sample_test_cases = question.test_cases.filter(is_sample=True)

        if not sample_test_cases.exists():
            # Run without input
            result = execute_test_case(code, "", "")
            return JsonResponse({'results': [result]})

        results = []
        for tc in sample_test_cases:
            res = execute_test_case(code, tc.input_data, tc.expected_output)
            results.append(res)

        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def submit_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student__user=request.user)

    if attempt.status != 'IN_PROGRESS':
        return redirect('test_result', attempt_id=attempt.id)

    # Compute time taken
    now = timezone.now()
    duration_delta = timedelta(minutes=attempt.test.duration_minutes)
    max_end_time = attempt.started_at + duration_delta

    is_timed_out = (now >= max_end_time)
    attempt.completed_at = min(now, max_end_time)
    attempt.time_taken_seconds = int((attempt.completed_at - attempt.started_at).total_seconds())
    attempt.status = 'TIMED_OUT' if is_timed_out else 'COMPLETED'

    # Evaluation loop
    total_score = 0.0
    questions = attempt.test.questions.prefetch_related('options', 'test_cases').all()

    for q in questions:
        submission, _ = Submission.objects.get_or_create(attempt=attempt, question=q)

        if q.question_type == 'MCQ':
            if submission.selected_option:
                if submission.selected_option.is_correct:
                    submission.marks_awarded = float(q.marks)
                    submission.is_correct = True
                else:
                    submission.is_correct = False
                    if attempt.test.has_negative_marking:
                        submission.marks_awarded = -float(attempt.test.negative_marks_per_question)
                    else:
                        submission.marks_awarded = 0.0
            else:
                submission.marks_awarded = 0.0
                submission.is_correct = False

        elif q.question_type == 'CODING':
            # Evaluate all test cases (sample + hidden) via secure sandbox
            test_cases_data = [
                {'input_data': tc.input_data, 'expected_output': tc.expected_output, 'is_sample': tc.is_sample}
                for tc in q.test_cases.all()
            ]
            eval_res = evaluate_coding_question(submission.submitted_code, test_cases_data)

            submission.test_cases_passed = eval_res['passed_count']
            submission.total_test_cases = eval_res['total_count']
            submission.marks_awarded = round(eval_res['score_ratio'] * float(q.marks), 2)
            submission.is_correct = (eval_res['score_ratio'] == 1.0)
            submission.evaluation_details = eval_res
            submission.execution_output = eval_res['overall_status']

        submission.save()
        total_score += submission.marks_awarded

    # Bound score >= 0
    attempt.score = max(0.0, round(total_score, 2))
    calcd_total = attempt.test.calculated_total_marks or attempt.test.total_marks or 1
    attempt.total_marks = calcd_total
    attempt.percentage = round((attempt.score / calcd_total) * 100, 2)
    attempt.save()

    # Generate Certificate if passed with excellence (>= 60% or top score)
    if attempt.percentage >= 60.0:
        Certificate.objects.get_or_create(attempt=attempt)

    messages.success(request, f"Test submitted successfully! You scored {attempt.score}/{attempt.total_marks} ({attempt.percentage}%).")
    return redirect('test_result', attempt_id=attempt.id)


@login_required
def test_result(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id)

    # Permission check: student owner or admin
    if not request.user.is_staff and attempt.student.user != request.user:
        messages.error(request, "Unauthorized access to test results.")
        return redirect('student_dashboard')

    submissions = attempt.submissions.select_related('question', 'selected_option').prefetch_related('question__options', 'question__test_cases').all()

    mcq_count = attempt.test.mcq_count
    coding_count = attempt.test.coding_count
    has_certificate = hasattr(attempt, 'certificate')

    return render(request, 'assessment/test_result.html', {
        'attempt': attempt,
        'test': attempt.test,
        'submissions': submissions,
        'mcq_count': mcq_count,
        'coding_count': coding_count,
        'has_certificate': has_certificate,
    })


@login_required
def download_certificate(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    if not request.user.is_staff and attempt.student.user != request.user:
        return HttpResponse("Unauthorized", status=403)

    if not hasattr(attempt, 'certificate'):
        messages.error(request, "Certificate is only awarded for scores of 60% and above.")
        return redirect('test_result', attempt_id=attempt.id)

    pdf_bytes = generate_certificate_pdf(attempt)
    filename = f"Certificate_{attempt.student.roll_number}_{attempt.test.id}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# -------------------------------------------------------------
# Leaderboard Module
# -------------------------------------------------------------
def leaderboard(request):
    tests = Test.objects.filter(is_active=True)
    selected_test_id = request.GET.get('test_id')

    attempts_query = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).select_related('student__user', 'test')

    if selected_test_id:
        attempts_query = attempts_query.filter(test_id=selected_test_id)

    # Leaderboard ordering & tie-breaking:
    # 1. Highest score (desc)
    # 2. Least time taken in seconds (asc)
    # 3. Earlier completion timestamp (asc)
    ranked_attempts = attempts_query.order_by('-score', 'time_taken_seconds', 'completed_at')[:10]

    # Assign ranks with consistent tie detection
    ranked_list = []
    current_rank = 1
    for idx, att in enumerate(ranked_attempts):
        if idx > 0:
            prev = ranked_attempts[idx - 1]
            if att.score == prev.score and att.time_taken_seconds == prev.time_taken_seconds:
                # Same score and same time = tied rank
                rank = ranked_list[-1]['rank']
            else:
                rank = idx + 1
        else:
            rank = 1

        ranked_list.append({
            'rank': rank,
            'attempt': att,
            'is_current_user': (request.user.is_authenticated and att.student.user == request.user)
        })

    return render(request, 'assessment/leaderboard.html', {
        'tests': tests,
        'selected_test_id': int(selected_test_id) if selected_test_id and selected_test_id.isdigit() else None,
        'ranked_list': ranked_list,
    })


# -------------------------------------------------------------
# Admin Module Views
# -------------------------------------------------------------
@user_passes_test(is_admin, login_url='admin_login')
def admin_dashboard(request):
    total_tests = Test.objects.count()
    total_students = Student.objects.count()
    total_attempts = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).count()
    avg_score = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).aggregate(Avg('percentage'))['percentage__avg'] or 0.0

    recent_tests = Test.objects.all().order_by('-created_at')[:5]
    recent_attempts = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).select_related('student__user', 'test').order_by('-completed_at')[:8]

    return render(request, 'admin_panel/dashboard.html', {
        'total_tests': total_tests,
        'total_students': total_students,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 1),
        'recent_tests': recent_tests,
        'recent_attempts': recent_attempts,
    })


@user_passes_test(is_admin, login_url='admin_login')
def admin_tests_list(request):
    tests = Test.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/tests_list.html', {'tests': tests})


@user_passes_test(is_admin, login_url='admin_login')
def admin_test_create(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.created_by = request.user
            test.save()
            messages.success(request, f"Test '{test.title}' created successfully! Now add questions to it.")
            return redirect('admin_manage_questions', test_id=test.id)
    else:
        form = TestForm()

    return render(request, 'admin_panel/test_form.html', {'form': form, 'title': 'Create New Test'})


@user_passes_test(is_admin, login_url='admin_login')
def admin_test_edit(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, f"Test '{test.title}' updated successfully.")
            return redirect('admin_tests_list')
    else:
        form = TestForm(instance=test)

    return render(request, 'admin_panel/test_form.html', {'form': form, 'title': f"Edit: {test.title}"})


@user_passes_test(is_admin, login_url='admin_login')
def admin_test_delete(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        title = test.title
        test.delete()
        messages.success(request, f"Test '{title}' has been deleted.")
        return redirect('admin_tests_list')

    return render(request, 'admin_panel/confirm_delete.html', {'item': test, 'type': 'Test'})


@user_passes_test(is_admin, login_url='admin_login')
def admin_manage_questions(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.prefetch_related('options', 'test_cases').all()
    return render(request, 'admin_panel/manage_questions.html', {
        'test': test,
        'questions': questions
    })


@user_passes_test(is_admin, login_url='admin_login')
def admin_question_create_mcq(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        form = MCQQuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.test = test
            q.question_type = 'MCQ'
            q.save()

            correct = form.cleaned_data['correct_option']
            Option.objects.create(question=q, option_text=form.cleaned_data['option_1'], is_correct=(correct == '1'))
            Option.objects.create(question=q, option_text=form.cleaned_data['option_2'], is_correct=(correct == '2'))
            Option.objects.create(question=q, option_text=form.cleaned_data['option_3'], is_correct=(correct == '3'))
            Option.objects.create(question=q, option_text=form.cleaned_data['option_4'], is_correct=(correct == '4'))

            messages.success(request, "Multiple choice question added.")
            return redirect('admin_manage_questions', test_id=test.id)
    else:
        # Default next order
        next_order = test.questions.count() + 1
        form = MCQQuestionForm(initial={'order': next_order, 'marks': 5})

    return render(request, 'admin_panel/question_mcq_form.html', {'form': form, 'test': test})


@user_passes_test(is_admin, login_url='admin_login')
def admin_question_create_coding(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        form = CodingQuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.test = test
            q.question_type = 'CODING'
            q.save()

            # Sample test case
            TestCase.objects.create(
                question=q,
                input_data=form.cleaned_data.get('sample_input', ''),
                expected_output=form.cleaned_data['sample_expected_output'],
                is_sample=True
            )

            # Hidden test case 1
            TestCase.objects.create(
                question=q,
                input_data=form.cleaned_data.get('hidden_input_1', ''),
                expected_output=form.cleaned_data['hidden_output_1'],
                is_sample=False
            )

            # Optional Hidden test case 2
            h_out2 = form.cleaned_data.get('hidden_output_2')
            if h_out2:
                TestCase.objects.create(
                    question=q,
                    input_data=form.cleaned_data.get('hidden_input_2', ''),
                    expected_output=h_out2,
                    is_sample=False
                )

            messages.success(request, "Coding question with test cases created successfully.")
            return redirect('admin_manage_questions', test_id=test.id)
    else:
        next_order = test.questions.count() + 1
        form = CodingQuestionForm(initial={
            'order': next_order,
            'marks': 10,
            'starter_code': "# Write your solution below\n\ndef solution():\n    pass\n\nif __name__ == '__main__':\n    # Read input from standard input\n    # print your answer\n    pass\n"
        })

    return render(request, 'admin_panel/question_coding_form.html', {'form': form, 'test': test})


@user_passes_test(is_admin, login_url='admin_login')
def admin_question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test_id = question.test.id
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect('admin_manage_questions', test_id=test_id)

    return render(request, 'admin_panel/confirm_delete.html', {'item': question, 'type': 'Question'})


@user_passes_test(is_admin, login_url='admin_login')
def admin_student_results(request):
    tests = Test.objects.all()
    selected_test_id = request.GET.get('test_id')

    attempts = TestAttempt.objects.filter(status__in=['COMPLETED', 'TIMED_OUT']).select_related('student__user', 'test').order_by('-completed_at')

    if selected_test_id and selected_test_id.isdigit():
        attempts = attempts.filter(test_id=int(selected_test_id))

    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assessment_results.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Username', 'Roll Number', 'College', 'Test', 'Score', 'Total Marks', 'Percentage', 'Status', 'Time Taken', 'Completed At'])
        for a in attempts:
            writer.writerow([
                a.student.user.get_full_name() or a.student.user.username,
                a.student.user.username,
                a.student.roll_number,
                a.student.college,
                a.test.title,
                a.score,
                a.total_marks,
                f"{a.percentage}%",
                a.status,
                a.formatted_time_taken,
                a.completed_at.strftime('%Y-%m-%d %H:%M:%S') if a.completed_at else ''
            ])
        return response

    return render(request, 'admin_panel/student_results.html', {
        'tests': tests,
        'selected_test_id': int(selected_test_id) if selected_test_id and selected_test_id.isdigit() else None,
        'attempts': attempts,
    })
