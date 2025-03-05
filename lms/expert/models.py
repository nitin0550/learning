import subprocess
from click import File
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import os
from datetime import timedelta
from django.db import transaction
from django.utils.text import slugify
from lms import settings
import logging

logger = logging.getLogger(__name__)

def user_directory_path(instance, filename):
    # Get the user's username
    user_id = str(instance.user.id)
    # Create a unique filename by appending the current timestamp
    ext = filename.split('.')[-1]
    new_filename = f"{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return f'expert/{user_id}/profile_picture/{new_filename}'

class ExpertProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Additional fields for expert profile
    profile_picture = models.ImageField(upload_to=user_directory_path, blank=True, null=True, default='defaults/default-profile.png')
    mobile_number = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=100)
    is_expert = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_expert_profile(sender, instance, created, **kwargs):
    if created:
        ExpertProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_expert_profile(sender, instance, **kwargs):
    instance.expertprofile.save()




class Course(models.Model):
    expert = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    course_title = models.CharField(max_length=200)
    about_course = models.TextField(blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_courses', null=True)
    price = models.IntegerField(default=0)
    expert = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expert_courses', null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    enrollment_duration = models.PositiveIntegerField(help_text="Duration in days for which the student has access", default=30)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.course_title
    
DEFAULT_EXPERT_ID = 1  # Replace with a valid user ID of an existing expert
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_enrollments')
    expert = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expert_enrollments', default=DEFAULT_EXPERT_ID)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expiration_date  = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


    class Meta:
        unique_together = ('student', 'course')  # Prevent duplicate enrollments

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.course_title}"


def user_directory_path_videos(instance, filename):
    username = instance.course.expert.username
    course_title = instance.course.course_title
    user_id = str(instance.course.expert.id)
    course_id = str(instance.course.id)
    ext = filename.split('.')[-1]
    new_filename = f"{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    # Generate file path: user/{username}/courses/{course_title}/{filename}
    return os.path.join('expert', user_id, 'courses', course_id, new_filename)

def user_directory_path_thumbnails(instance, filename):
    username = instance.course.expert.username
    course_title = instance.course.course_title
    user_id = str(instance.course.expert.id)
    course_id = str(instance.course.id)

    ext = filename.split('.')[-1]
    new_filename = f"{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join('expert', user_id, 'courses', course_id, 'thumbnails', new_filename)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    lesson_title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to=user_directory_path_videos, blank=True, null=True)
    thumbnail = models.ImageField(upload_to=user_directory_path_thumbnails, blank=True, null=True)
    hls_url = models.CharField(max_length=255, blank=True, null=True)  # Store HLS directory path
    duration = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.lesson_title

    def save(self, *args, **kwargs):
        # Set the upload path for the video dynamically
        if self.course:
            self.video.name = user_directory_path_videos(self, self.video.name)  # Override video file path
        super().save(*args, **kwargs)

    
    def hls_url(self):
        # Return the URL for the .m3u8 file, stored in media folder
        return self.hls_url
    
    
class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateTimeField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    
    
    def __str__(self):
        return f"{self.title} - {self.course.course_title}"



class Quiz(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(help_text='Duration in minutes', default=timedelta(minutes=30))
    passing_score = models.FloatField(default=35)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']  # Default ordering newest first

    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
        ('SA', 'Short Answer'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=3, choices=QUESTION_TYPES)
    option_1 = models.CharField(max_length=255, blank=True, null=True)
    option_2 = models.CharField(max_length=255, blank=True, null=True)
    option_3 = models.CharField(max_length=255, blank=True, null=True)
    option_4 = models.CharField(max_length=255, blank=True, null=True)
    correct_answer = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return self.question_text

class QuizAssignment(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)   

    class Meta:
        unique_together = ['quiz', 'student']
        ordering = ['-assigned_date']

    def __str__(self):
        return f"{self.quiz.title} - {self.student.username}"


class QuizAnswer(models.Model):
    assignment = models.ForeignKey(QuizAssignment, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    student_answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Answer by {self.assignment.student.username} for {self.question.question_text[:30]}"

@receiver(post_save, sender='expert.Enrollment')
def update_wallet_on_enrollment(sender, instance, created, **kwargs):
    if created:  # Only process new enrollments
        try:
            with transaction.atomic():
                course = instance.course
                expert = course.instructor
                
                # Get or create expert wallet
                wallet, _ = Wallet.objects.get_or_create(
                    expert=expert,
                    defaults={'balance': 0}
                )
                
                # Add course price to wallet
                wallet.balance += course.price
                wallet.save()
                
        except Exception as e:
            print(f"Error updating wallet: {str(e)}")
class Wallet(models.Model):
    expert = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.expert.username}'s wallet"

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    
    expert = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bank_account = models.CharField(max_length=255)
    ifsc_code = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.expert.username} - ₹{self.amount}"
    
class Expert_Notification(models.Model):
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