from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    path('', views.chat_interface, name='chat_interface'),
    path('new/', views.new_chat_session, name='new_chat'),
    path('session/<uuid:session_id>/', views.chat_session, name='chat_session'),
    path('send-message/', views.send_message, name='send_message'),
    path('delete-session/<uuid:session_id>/', views.delete_session, name='delete_session'),
    path('history/', views.chat_history, name='chat_history'),
]