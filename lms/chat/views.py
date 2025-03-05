from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from chat.forms import MessageForm
from .models import Message
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils import timezone 

@login_required
def chat_view(request, user_id):
    try:
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return render(request, 'chat/error.html')

        if request.user.is_staff and other_user.is_staff:
            messages.error(request, "User not found.")
            return redirect('expert_chat')

        if not request.user.is_staff and not other_user.is_staff:
            messages.error(request, "User not found.")
            return redirect('student_chat')
        
        if request.method == 'POST':
            form = MessageForm(request.POST, request.FILES)
            if form.is_valid():
                message = form.save(commit=False)
                message.sender = request.user
                message.receiver = other_user
                message.save()
                return redirect('chat_view', user_id=user_id)
        else:
            form = MessageForm()
            
        # Get all messages between the logged-in user and the other user
        if request.user.is_staff:
            if Message.deleted_for_expert == False:
                chat_messages = Message.objects.filter(
                    sender__in=[request.user, other_user],
                    receiver__in=[request.user, other_user],
                ).order_by('timestamp')
            else:
                chat_messages = Message.objects.filter(
                    Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user),
                    deleted_for_expert=False  # Exclude deleted messages for the student
                ).order_by('timestamp')
        else:
            if Message.deleted_for_student == False:
                chat_messages = Message.objects.filter(
                    sender__in=[request.user, other_user],
                    receiver__in=[request.user, other_user],
                ).order_by('timestamp')
            else:
                chat_messages = Message.objects.filter(
                    Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user),
                    deleted_for_student=False  # Exclude deleted messages for the student
                ).order_by('timestamp')

        today = timezone.now()
        yesterday = today - timedelta(days=1)

        if request.user.is_staff:
            return render(request, 'chat/expert_chating_page.html', {
                'messages': chat_messages,
                'other_user': other_user,
                'today': today,
                'yesterday': yesterday,
                'form': form,
                })
        else:
            return render(request, 'chat/student_chating_page.html', {
                'messages': chat_messages,
                'other_user': other_user,
                'today': today,
                'yesterday': yesterday,
                'form': form,
                })
        
    except Exception as e:
        messages.error(request, f'Error loading chat: {str(e)}')
        return redirect('expert_chat' if request.user.is_staff else 'student_chat')

@login_required
def delete_all_chat(request, user_id):
      # Ensure only students can delete their chats
    other_user = get_object_or_404(User, id=user_id)
    # Delete all messages where the student is either the sender or recipient with the selected user
    Message.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).delete()

    messages.success(request, "All chat messages with this user have been deleted.")
    if request.user.is_staff:
        return redirect('expert_chat')
    else:
        return redirect('student_chat')