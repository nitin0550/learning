from django.urls import path
from . import views
from .views import student_register,student_dashboard

urlpatterns = [
    #path('home', views.home, name='home'),
    path('register/', student_register, name='student_register'),
    path('verify-registration/', views.verify_registration, name='verify_registration'),
    path('', student_dashboard, name='student_dashboard'),
    path('chats', views.student_chat, name='student_chat'),
    path('delete_chat/<int:expert_id>/', views.delete_all_chat, name='student_delete_chat'),
    path('profile', views.student_profile, name='student_profile'),
    path('profile_setting', views.student_profile_setting, name='student_profile_setting'),
    path('course_search', views.student_course_search, name='student_course_search'),
    path('enroll/<int:course_id>/', views.enroll_in_course, name='enroll_in_course'),
    path('enrolled_courses', views.student_enrolled_courses, name='student_enrolled_courses'),
    path('course_assignments/<int:course_id>/', views.student_course_assignments, name='student_course_assignments'),
    path('assignments/all/', views.student_all_assignments, name='student_all_assignments'),
    path('quizzes/', views.student_quiz_list, name='student_quiz_list'),
    path('quiz/<int:quiz_id>/take/', views.student_take_quiz, name='student_take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),

    path('course/<int:course_id>/lessons/', views.student_enrolled_lessons, name='student_enrolled_lessons'),
    path('course/<int:lesson_id>/play_video/', views.student_play_video, name='student_play_video'),
    path('notification', views.student_notifications, name='student_notifications'),
]