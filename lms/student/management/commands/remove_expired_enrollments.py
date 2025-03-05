# student/management/commands/remove_expired_enrollments.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from expert.models import Enrollment

class Command(BaseCommand):
    help = "Removes expired enrollments based on the duration set by the course expert"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_enrollments = []

        for enrollment in Enrollment.objects.select_related('course'):
            expiration_date = enrollment.enrolled_at + timezone.timedelta(days=enrollment.course.enrollment_duration)
            if now >= expiration_date:
                expired_enrollments.append(enrollment)
        
        # Delete all expired enrollments
        if expired_enrollments:
            Enrollment.objects.filter(id__in=[en.id for en in expired_enrollments]).delete()
            self.stdout.write(self.style.SUCCESS(f"{len(expired_enrollments)} expired enrollments removed"))
        else:
            self.stdout.write("No expired enrollments found")
