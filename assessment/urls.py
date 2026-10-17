from django.urls import path
from . import views

urlpatterns = [
    # Public & Auth
    path('', views.home, name='home'),
    path('register/', views.student_register, name='student_register'),
    path('login/', views.student_login, name='student_login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.user_logout, name='user_logout'),

    # Student Module
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),
    path('attempt/<int:attempt_id>/take/', views.take_test, name='take_test'),
    path('attempt/<int:attempt_id>/submit/', views.submit_test, name='submit_test'),
    path('attempt/<int:attempt_id>/result/', views.test_result, name='test_result'),
    path('attempt/<int:attempt_id>/certificate/', views.download_certificate, name='download_certificate'),

    # AJAX Endpoints for Timed Exam
    path('api/save-answer/', views.api_save_answer, name='api_save_answer'),
    path('api/run-code/', views.api_run_code, name='api_run_code'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Admin / Instructor Module
    path('instructor/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('instructor/tests/', views.admin_tests_list, name='admin_tests_list'),
    path('instructor/tests/create/', views.admin_test_create, name='admin_test_create'),
    path('instructor/tests/<int:test_id>/edit/', views.admin_test_edit, name='admin_test_edit'),
    path('instructor/tests/<int:test_id>/delete/', views.admin_test_delete, name='admin_test_delete'),
    path('instructor/tests/<int:test_id>/questions/', views.admin_manage_questions, name='admin_manage_questions'),
    path('instructor/tests/<int:test_id>/questions/add-mcq/', views.admin_question_create_mcq, name='admin_question_create_mcq'),
    path('instructor/tests/<int:test_id>/questions/add-coding/', views.admin_question_create_coding, name='admin_question_create_coding'),
    path('instructor/questions/<int:question_id>/delete/', views.admin_question_delete, name='admin_question_delete'),
    path('instructor/results/', views.admin_student_results, name='admin_student_results'),
]
