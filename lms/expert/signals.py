from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import ExpertProfile, Enrollment
from chat.models import Message

#@receiver(post_save, sender=User)
#def create_expert_profile(sender, instance, created, **kwargs):
#    if created:
#        ExpertProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_expert_profile(sender, instance, **kwargs):
    instance.expertprofile.save()

@receiver(post_save, sender=Enrollment)
def send_welcome_message(sender, instance, created, **kwargs):
    if created:  # This only triggers on new enrollments
        # Retrieve the student and expert from the enrollment instance
        student = instance.student
        expert = instance.course.instructor
        course = instance.course

        # Create a welcome message
        welcome_text = f"Welcome, {student.username}! I’m excited to guide you through the {course.course_title} course. Feel free to ask any questions!"

        # Save the welcome message to the chat model
        Message.objects.create(
            sender=expert,
            receiver=student,
            content=welcome_text
        )