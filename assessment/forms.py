from django import forms
from django.contrib.auth.models import User
from .models import Student, Test, Question, Option, TestCase

class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    roll_number = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 23N31A0504'}))
    college = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College / University Name'}))
    branch = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CSE, IT, ECE'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))

    class Meta:
        model = Student
        fields = ['roll_number', 'college', 'branch', 'phone']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username is already taken.")
        return username

    def clean_roll_number(self):
        roll = self.cleaned_data.get('roll_number')
        if Student.objects.filter(roll_number=roll).exists():
            raise forms.ValidationError("Roll number already registered.")
        return roll

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            'title', 'description', 'duration_minutes', 'total_marks', 'pass_marks',
            'has_negative_marking', 'negative_marks_per_question',
            'randomize_questions', 'allow_multiple_attempts', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python Core Assessment 2026'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Test instructions and topics covered'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'has_negative_marking': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'neg_marking_toggle'}),
            'negative_marks_per_question': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'min': '0'}),
            'randomize_questions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_multiple_attempts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MCQQuestionForm(forms.ModelForm):
    option_1 = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option A'}))
    option_2 = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option B'}))
    option_3 = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option C'}))
    option_4 = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option D'}))
    correct_option = forms.ChoiceField(
        choices=[('1', 'Option A'), ('2', 'Option B'), ('3', 'Option C'), ('4', 'Option D')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Question
        fields = ['question_text', 'marks', 'order', 'explanation']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter Python MCQ question text or code snippet'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explanation for correct answer'}),
        }


class CodingQuestionForm(forms.ModelForm):
    # Sample Test Case
    sample_input = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Sample Standard Input (e.g. 5\n1 2 3 4 5)'}))
    sample_expected_output = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Sample Expected Output (e.g. 15)'}))
    
    # Hidden Test Case 1
    hidden_input_1 = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Hidden Test Case 1 Input'}))
    hidden_output_1 = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Hidden Test Case 1 Expected Output'}))
    
    # Hidden Test Case 2 (optional)
    hidden_input_2 = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Hidden Test Case 2 Input (Optional)'}))
    hidden_output_2 = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 2, 'placeholder': 'Hidden Test Case 2 Expected Output (Optional)'}))

    class Meta:
        model = Question
        fields = ['question_text', 'marks', 'order', 'starter_code', 'problem_constraints', 'explanation']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Problem Statement & Requirements'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'starter_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': '# Starter template code for student'}),
            'problem_constraints': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Time limit: 2s | 1 <= N <= 10^5'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Editorial / Explanation for solution'}),
        }
