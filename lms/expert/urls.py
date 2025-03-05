from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('register/', views.expert_register, name='expert_register'),
    path('', views.expert_dashboard, name='expert_dashboard'),
    path('profile', views.expert_profile, name='expert_profile'),
    path('profile_setting', views.expert_profile_setting, name='expert_profile_setting'),

    path('my_courses', views.expert_my_courses, name='expert_my_courses'),

    path('student_management', views.expert_student_management, name='expert_student_management'),
    path('student_management/remove/<int:enrollment_id>/', views.remove_enrollment, name='remove_enrollment'),

    path('assignment', views.expert_assignment, name='expert_assignment'),
    path('assignment/<int:assignment_id>/', views.expert_assignment, name='expert_assignment'),  # Optional ID for edit
    path('delete_assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),

    path('learning_resources', views.expert_learning_resources, name='expert_learning_resources'),
    path('expert_notifications', views.expert_notifications, name='expert_notifications'),
    #path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),

    path('chats', views.expert_chat, name='expert_chat'),
    path('delete_chat/<int:student_id>/', views.delete_all_chat, name='expert_delete_chat'),
    path('course/<int:course_id>/send_announcement/', views.send_announcement, name='send_announcement'),
    path('view_result_list', views.expert_view_result_list, name='expert_view_result_list'),

    path('create_quiz', views.expert_create_quiz, name='expert_create_quiz'),
    path('quiz_list', views.expert_quiz_list, name='expert_quiz_list'),
    path('quiz/<int:quiz_id>/', views.expert_quiz_detail, name='expert_quiz_detail'),
    path('quiz/<int:quiz_id>/edit/', views.expert_edit_quiz, name='expert_edit_quiz'),
    path('quiz/<int:quiz_id>/delete/', views.expert_delete_quiz, name='expert_delete_quiz'),
    path('quiz/<int:quiz_id>/send/', views.send_quiz_to_students, name='send_quiz_to_students'),
    path('quiz/<int:quiz_id>/results/', views.expert_view_quiz_results, name='expert_view_quiz_results'),
    path('quiz/<int:quiz_id>/student/<int:student_id>/', views.student_quiz_details, name='student_quiz_details'),
    
    path('upload_course', views.expert_upload_course, name='expert_upload_course'),
    path('course/<int:course_id>/', views.expert_lessons, name='expert_lessons'),
    path('course/<int:lesson_id>/delete/', views.delete_video, name='delete_video'),
    path('course/<int:lesson_id>/edit/', views.edit_video, name='edit_video'),
    path('course/<int:lesson_id>/play_video/', views.expert_play_video, name='expert_play_video'),
    path('hls/<path:path>', views.serve_hls_segment, name='serve_hls_segment'),
    path('expert/hls-manifest/<int:lesson_id>/', views.get_hls_manifest, name='get_hls_manifest'),
    
    path('upload_video/<int:course_id>', views.expert_upload_video, name='expert_upload_video'),
    #path('course/<int:course_id>/add-quiz/', views.add_quiz, name='add_quiz'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    
    path('rename-course/<int:course_id>/', views.rename_course, name='rename_course'), 

    path('selles_dashboard/', views.selles_dashboard, name='selles_dashboard'),
    path('withdrawal/request/', views.request_withdrawal, name='request_withdrawal'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)