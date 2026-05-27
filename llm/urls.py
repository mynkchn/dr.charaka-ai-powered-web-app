from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    # Pages
    path('',                        views.chat_interface,    name='chat'),
    path('session/<uuid:session_id>/', views.chat_session_view, name='chat_session'),
    path('history/',                views.chat_history,      name='history'),

    # API endpoints (called by frontend JS)
    path('api/chat/',                          views.api_chat,           name='api_chat'),
    path('api/chat/<str:session_id>/clear/',   views.api_clear_session,  name='api_clear'),

    # Other actions
    path('session/<uuid:session_id>/delete/',  views.delete_session,     name='delete_session'),
    path('new/',                               views.new_chat_session,   name='new_session'),
]