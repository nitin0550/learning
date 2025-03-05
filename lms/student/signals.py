#from django.db.models.signals import post_save
#from django.dispatch import receiver
#from django.contrib.auth.models import User
#from .models import StudentProfile
#
#@receiver(post_save, sender=User)
#def create_student_profile(sender, instance, created, **kwargs):
#    if created:
#        StudentProfile.objects.create(user=instance)
#
#@receiver(post_save, sender=User)
#def save_student_profile(sender, instance, **kwargs):
#    instance.studentprofile.save()
#
# student/signals.py

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from expert.models import Enrollment

@receiver(pre_save, sender=Enrollment)
def check_expiration(sender, instance, **kwargs):
    expiration_date = instance.enrolled_at + timedelta(days=instance.course.enrollment_duration)
    if timezone.now() >= expiration_date:
        instance.delete()  # Delete expired enrollments before they’re saved/updated
