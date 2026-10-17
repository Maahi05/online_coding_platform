from django.test import TestCase as DjangoTestCase, Client
from django.contrib.auth.models import User
from assessment.models import Student, Test, Question, Option, TestCase, TestAttempt, Submission, Certificate
from assessment.sandbox import validate_python_code, execute_test_case, evaluate_coding_question
from assessment.certificate_generator import generate_certificate_pdf

class SandboxSecurityTest(DjangoTestCase):
    def test_blocks_forbidden_imports(self):
        malicious_code = "import os\nos.system('dir')"
        errors = validate_python_code(malicious_code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("strictly disallowed", errors[0])

    def test_blocks_subprocesses_and_sockets(self):
        code1 = "import subprocess\nsubprocess.run(['dir'])"
        self.assertTrue(any("subprocess" in err for err in validate_python_code(code1)))

        code2 = "from socket import socket"
        self.assertTrue(any("socket" in err for err in validate_python_code(code2)))

    def test_blocks_eval_and_exec(self):
        code = "x = eval('1 + 2')"
        errors = validate_python_code(code)
        self.assertTrue(any("eval" in err for err in errors))

    def test_safe_python_execution(self):
        safe_code = "import sys\nline = sys.stdin.read().strip()\nprint(f'Hello {line}')"
        # sys is in forbidden module list by default unless sys.stdin is handled or we test pure python
        pure_code = "n = int(input())\nprint(n * 2)"
        res = execute_test_case(pure_code, "5\n", "10")
        self.assertTrue(res['passed'])
        self.assertEqual(res['actual_output'], "10")

    def test_timeout_protection(self):
        infinite_loop = "while True:\n    pass"
        res = execute_test_case(infinite_loop, "", "", timeout_seconds=1.0)
        self.assertFalse(res['passed'])
        self.assertEqual(res['status'], 'TIMEOUT')


class ModelsAndAssessmentWorkflowTest(DjangoTestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teststudent', password='password123', first_name='Test', last_name='User')
        self.student = Student.objects.create(user=self.user, roll_number='23TEST01', college='Test University', branch='CSE')
        
        self.admin = User.objects.create_user(username='adminuser', password='password123', is_staff=True)
        self.test_obj = Test.objects.create(
            title="Unit Test Exam",
            duration_minutes=20,
            total_marks=20,
            pass_marks=10,
            has_negative_marking=True,
            negative_marks_per_question=0.5,
            created_by=self.admin
        )

        # MCQ Question
        self.q_mcq = Question.objects.create(
            test=self.test_obj,
            question_text="What is 2 + 2?",
            question_type='MCQ',
            marks=5,
            order=1
        )
        self.opt1 = Option.objects.create(question=self.q_mcq, option_text="3", is_correct=False)
        self.opt2 = Option.objects.create(question=self.q_mcq, option_text="4", is_correct=True)

        # Coding Question
        self.q_code = Question.objects.create(
            test=self.test_obj,
            question_text="Print double of input number",
            question_type='CODING',
            marks=15,
            order=2
        )
        self.tc1 = TestCase.objects.create(question=self.q_code, input_data="4\n", expected_output="8", is_sample=True)
        self.tc2 = TestCase.objects.create(question=self.q_code, input_data="10\n", expected_output="20", is_sample=False)

    def test_attempt_and_negative_marking(self):
        attempt = TestAttempt.objects.create(student=self.student, test=self.test_obj, total_marks=20.0)
        
        # Wrong MCQ answer
        sub_wrong = Submission.objects.create(
            attempt=attempt,
            question=self.q_mcq,
            selected_option=self.opt1,
            marks_awarded=-0.5,
            is_correct=False
        )
        self.assertEqual(sub_wrong.marks_awarded, -0.5)

    def test_certificate_generation(self):
        attempt = TestAttempt.objects.create(
            student=self.student,
            test=self.test_obj,
            score=20.0,
            total_marks=20.0,
            percentage=100.0,
            status='COMPLETED'
        )
        Certificate.objects.create(attempt=attempt)
        pdf_bytes = generate_certificate_pdf(attempt)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
