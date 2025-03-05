import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message
from django.contrib.auth.models import User
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.other_user = await self.get_user(self.other_user_id)

        if self.user.is_authenticated and self.other_user:
            self.room_name = f"chat_{min(self.user.id, self.other_user_id)}_{max(self.user.id, self.other_user_id)}"
            self.room_group_name = f"chat_{self.room_name}"

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            await self.mark_messages_as_read(self.user, self.other_user)
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.mark_messages_as_read(self.user, self.other_user)
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        is_read = await self.is_user_in_room(self.other_user)
        # Save message to database
        msg_obj = await self.save_message(self.user, self.other_user, message, is_read)
        await self.mark_messages_as_read(self.user, self.other_user)
        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'timestamp': msg_obj.timestamp.isoformat(),
                'is_read': is_read,
            }
        )

    async def chat_message(self, event):
        # Send the message to WebSocket
        await self.mark_messages_as_read(self.user, self.other_user)
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'is_read': event['is_read'],
        }))
        

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, sender, receiver, content, is_read):
        return Message.objects.create(sender=sender, receiver=receiver, content=content, is_read=is_read)

    @database_sync_to_async
    def get_past_messages(self, user, other_user):
        # Get messages between the two users
        return Message.objects.filter(
            sender__in=[user, other_user],
            receiver__in=[user, other_user],
        ).order_by('timestamp')
    @database_sync_to_async
    def is_user_in_room(self, user):
        # Placeholder, needs actual implementation.
        return False
    @database_sync_to_async
    def mark_messages_as_read(self, user, other_user):
        # Set all messages from the other user to this user as read
        Message.objects.filter(sender=other_user, receiver=user, is_read=False).update(is_read=True)