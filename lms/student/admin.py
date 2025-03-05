from django.contrib import admin
from .models import StudentProfile, Student_Notification


# Register your models here.
admin.site.register(StudentProfile)
admin.site.register(Student_Notification)