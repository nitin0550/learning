from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>/', views.chat_view, name='chat'),
    #path('delete_chat/<int:user_id>/', views.delete_all_chat, name='delete_all_chat'),
]
