
# Create your models here.
# student/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def user_directory_path(instance, filename):
    # Get the user's username
    user_id = str(instance.user.id)
    # Create a unique filename by appending the current timestamp
    ext = filename.split('.')[-1]
    new_filename = f"{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return f'student/{user_id}/profile_picture/{new_filename}'

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Additional fields for student profile
    profile_picture = models.ImageField(upload_to=user_directory_path, blank=True, null=True, default='defaults/default-profile.png')
    mobile_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username
    
class Student_Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('course', 'Course'),
        ('general', 'General')
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

