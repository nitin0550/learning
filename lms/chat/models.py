import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def chat_files(instance, filename):
    if instance.sender.is_staff:
        user_type = 'expert'
    else:
        user_type = 'student'
    user_id = str(instance.sender.id)
    ext = filename.split('.')[-1]
    new_filename = f"{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join(user_type, user_id, 'chat_files', new_filename)

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', null=True ,blank=False)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=False)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=chat_files, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    deleted_for_student = models.BooleanField(default=False)
    deleted_for_expert = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} to {self.receiver}: {self.content[:20]}"
