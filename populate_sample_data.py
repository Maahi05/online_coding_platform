"""
Seed sample data for testing and demonstration of the Online Coding Test Platform.
Run via: python populate_sample_data.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coding_platform.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from assessment.models import Student, Test, Question, Option, TestCase, TestAttempt, Submission, Certificate

def seed():
    print("Seeding database with sample tests, questions, and students...")

    # 1. Admin Superuser
    admin_user, created = User.objects.get_or_create(username='admin', defaults={
        'email': 'admin@10000coders.com',
        'first_name': 'Platform',
        'last_name': 'Administrator',
        'is_staff': True,
        'is_superuser': True
    })
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Created Superuser: admin / admin123")

    # 2. Sample Students
    students_data = [
        {'username': 'rahul', 'first': 'Rahul', 'last': 'Sharma', 'roll': '23N31A0501', 'college': 'JNTU Hyderabad', 'branch': 'CSE', 'email': 'rahul@example.com'},
        {'username': 'priya', 'first': 'Priya', 'last': 'Reddy', 'roll': '23N31A0502', 'college': 'CBIT Hyderabad', 'branch': 'IT', 'email': 'priya@example.com'},
        {'username': 'sai', 'first': 'Sai', 'last': 'Kumar', 'roll': '23N31A0503', 'college': 'VNR VJIET', 'branch': 'CSE', 'email': 'sai@example.com'},
        {'username': 'ananya', 'first': 'Ananya', 'last': 'Verma', 'roll': '23N31A0504', 'college': 'Vasavi College', 'branch': 'ECE', 'email': 'ananya@example.com'},
    ]

    student_objects = []
    for s_info in students_data:
        u, u_created = User.objects.get_or_create(username=s_info['username'], defaults={
            'email': s_info['email'],
            'first_name': s_info['first'],
            'last_name': s_info['last']
        })
        if u_created:
            u.set_password('student123')
            u.save()

        st, _ = Student.objects.get_or_create(user=u, defaults={
            'roll_number': s_info['roll'],
            'college': s_info['college'],
            'branch': s_info['branch']
        })
        student_objects.append(st)

    print(f"Verified {len(student_objects)} student profiles (Password: student123).")

    # 3. Create Featured Test
    test, _ = Test.objects.get_or_create(
        title="Python Core & Problem Solving Challenge 2026",
        defaults={
            'description': "Comprehensive Python test covering list manipulations, immutable types, string algorithms, and coding problems with test-case validation.",
            'duration_minutes': 30,
            'total_marks': 50,
            'pass_marks': 20,
            'has_negative_marking': True,
            'negative_marks_per_question': 0.25,
            'randomize_questions': True,
            'allow_multiple_attempts': False,
            'is_active': True,
            'created_by': admin_user
        }
    )

    # 4. Create Questions for Test
    # Clear existing questions for clean seed
    test.questions.all().delete()

    # --- MCQ 1 ---
    q1 = Question.objects.create(
        test=test,
        question_text="What will be the output of the following Python snippet?\n\nx = [1, 2, 3]\ny = x\ny.append(4)\nprint(x)",
        question_type='MCQ',
        marks=5,
        order=1,
        explanation="In Python, variables reference the same underlying list object. Appending to y modifies the list pointed to by x."
    )
    Option.objects.create(question=q1, option_text="[1, 2, 3]", is_correct=False)
    Option.objects.create(question=q1, option_text="[1, 2, 3, 4]", is_correct=True)
    Option.objects.create(question=q1, option_text="TypeError: list assignment invalid", is_correct=False)
    Option.objects.create(question=q1, option_text="[4, 1, 2, 3]", is_correct=False)

    # --- MCQ 2 ---
    q2 = Question.objects.create(
        test=test,
        question_text="Which of the following data structures in Python is immutable?",
        question_type='MCQ',
        marks=5,
        order=2,
        explanation="Tuples are immutable sequences in Python; their elements cannot be modified after assignment."
    )
    Option.objects.create(question=q2, option_text="List", is_correct=False)
    Option.objects.create(question=q2, option_text="Dictionary", is_correct=False)
    Option.objects.create(question=q2, option_text="Tuple", is_correct=True)
    Option.objects.create(question=q2, option_text="Set", is_correct=False)

    # --- MCQ 3 ---
    q3 = Question.objects.create(
        test=test,
        question_text="What does the expression [x**2 for x in range(5) if x % 2 == 0] evaluate to?",
        question_type='MCQ',
        marks=5,
        order=3,
        explanation="range(5) produces 0, 1, 2, 3, 4. Even numbers are 0, 2, 4. Squares are 0, 4, 16."
    )
    Option.objects.create(question=q3, option_text="[0, 4, 16]", is_correct=True)
    Option.objects.create(question=q3, option_text="[1, 9]", is_correct=False)
    Option.objects.create(question=q3, option_text="[0, 1, 4, 9, 16]", is_correct=False)
    Option.objects.create(question=q3, option_text="[4, 16]", is_correct=False)

    # --- Coding Question 1 ---
    q4 = Question.objects.create(
        test=test,
        question_text="Problem: Sum of Array Elements\n\nWrite a Python program that reads an integer N followed by N space-separated integers, and prints their total sum.",
        question_type='CODING',
        marks=15,
        order=4,
        problem_constraints="1 <= N <= 10^5, -10^6 <= arr[i] <= 10^6, Time Limit: 2.0s",
        starter_code="import sys\n\ndef main():\n    lines = sys.stdin.read().split()\n    if not lines:\n        return\n    n = int(lines[0])\n    nums = [int(x) for x in lines[1:n+1]]\n    # Write logic to compute and print sum\n    print(sum(nums))\n\nif __name__ == '__main__':\n    main()\n",
        explanation="Read tokens from standard input, parse numbers into a list, and compute sum using sum() or an accumulator."
    )
    # Sample Test Case
    TestCase.objects.create(
        question=q4,
        input_data="5\n10 20 30 40 50",
        expected_output="150",
        is_sample=True
    )
    # Hidden Test Cases
    TestCase.objects.create(
        question=q4,
        input_data="3\n-5 5 100",
        expected_output="100",
        is_sample=False
    )
    TestCase.objects.create(
        question=q4,
        input_data="4\n0 0 0 0",
        expected_output="0",
        is_sample=False
    )

    # --- Coding Question 2 ---
    q5 = Question.objects.create(
        test=test,
        question_text="Problem: Reverse Words in a Sentence\n\nWrite a Python program that takes a string of words separated by spaces and prints the words in reversed order.",
        question_type='CODING',
        marks=20,
        order=5,
        problem_constraints="String length <= 1000 characters, Time Limit: 2.0s",
        starter_code="import sys\n\ndef main():\n    text = sys.stdin.read().strip()\n    # Reverse words and print\n    words = text.split()\n    print(' '.join(reversed(words)))\n\nif __name__ == '__main__':\n    main()\n",
        explanation="Use text.split() to split on spaces, reverse the sequence, and rejoin with ' '.join()."
    )
    # Sample Test Case
    TestCase.objects.create(
        question=q5,
        input_data="Python is awesome",
        expected_output="awesome is Python",
        is_sample=True
    )
    # Hidden Test Cases
    TestCase.objects.create(
        question=q5,
        input_data="hello world",
        expected_output="world hello",
        is_sample=False
    )
    TestCase.objects.create(
        question=q5,
        input_data="10000 Coders Assessment Platform",
        expected_output="Platform Assessment Coders 10000",
        is_sample=False
    )

    print(f"Created Test '{test.title}' with {test.questions.count()} questions (3 MCQs, 2 Coding Problems).")

    # 5. Populate Sample Completed Attempts for Leaderboard demonstration
    # Attempt 1: Rahul (Score: 50/50, 100%, 820s) -> Rank 1
    now = timezone.now()
    att1, _ = TestAttempt.objects.get_or_create(
        student=student_objects[0],
        test=test,
        defaults={
            'started_at': now - timedelta(hours=3),
            'completed_at': now - timedelta(hours=3, seconds=-820),
            'score': 50.0,
            'total_marks': 50.0,
            'percentage': 100.0,
            'status': 'COMPLETED',
            'time_taken_seconds': 820
        }
    )
    Certificate.objects.get_or_create(attempt=att1)

    # Attempt 2: Priya (Score: 45.0/50, 90%, 940s) -> Rank 2
    att2, _ = TestAttempt.objects.get_or_create(
        student=student_objects[1],
        test=test,
        defaults={
            'started_at': now - timedelta(hours=2),
            'completed_at': now - timedelta(hours=2, seconds=-940),
            'score': 45.0,
            'total_marks': 50.0,
            'percentage': 90.0,
            'status': 'COMPLETED',
            'time_taken_seconds': 940
        }
    )
    Certificate.objects.get_or_create(attempt=att2)

    # Attempt 3: Sai (Score: 45.0/50, 90%, 1150s) -> Rank 3 (Tied score with Priya, but took more time!)
    att3, _ = TestAttempt.objects.get_or_create(
        student=student_objects[2],
        test=test,
        defaults={
            'started_at': now - timedelta(hours=1),
            'completed_at': now - timedelta(hours=1, seconds=-1150),
            'score': 45.0,
            'total_marks': 50.0,
            'percentage': 90.0,
            'status': 'COMPLETED',
            'time_taken_seconds': 1150
        }
    )
    Certificate.objects.get_or_create(attempt=att3)

    print("Populated realistic leaderboard sample attempts and generated top performer certificates.")
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
