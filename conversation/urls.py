# conversation/urls.py

from django.urls import path
from .views import doctor_chat_view

urlpatterns = [
    path('chat/', doctor_chat_view, name='doctor_chat'),
]
