from django.contrib import admin
from .models import Message

class MessageAdmin(admin.ModelAdmin):
    search_fields = ('sender__username', 'receiver__username', 'content')

admin.site.register(Message, MessageAdmin)