# expert/notifications.py
from .models import Expert_Notification
from student.models import Student_Notification

def create_notification_expert(user, title, message, notification_type='general'):
    Expert_Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False
    )

def create_notification_student(user, title, message, notification_type='general'):
    Student_Notification.objects.create(  
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False
    )

def create_enrollment_notification(expert, student):
    message = f"Student {student.username} has enrolled in your course"
    create_notification_expert(
        expert,
        "New Student Enrollment",
        message,
        "enrollment"
    )