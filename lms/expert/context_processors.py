from .models import Expert_Notification
from chat.models import Message

#def notification_context(request):
#    if request.user.is_authenticated:
#        unread_count = Expert_Notification.objects.filter(
#            recipient=request.user,
#            is_read=False
#        ).exists()
#        return {'has_unread_notifications': unread_count}
#    return {'has_unread_notifications': False}

def context_processor(request):
    context = {
        'has_unread_notifications_expert': False,
        'has_unread_messages_expert': False
    }
    
    if request.user.is_authenticated:
        
        
        messages = Message.objects.filter(
            receiver=request.user,
            is_read=False,
            deleted_for_student=False
        )
        has_messages = messages.exists()
        context['has_unread_messages_expert'] = has_messages

        # Check for unread notifications
        notifications = Expert_Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        has_notifications = notifications.exists()
        context['has_unread_notifications_expert'] = has_notifications

    return context