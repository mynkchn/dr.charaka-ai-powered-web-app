# conversation/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User  # your custom user model
from .models import DoctorChat

@login_required
def doctor_chat_view(request):
    doctors = User.objects.filter(is_doctor=True).exclude(id=request.user.id)
    
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        message_text = request.POST.get('message')

        if not receiver_id or not message_text:
            messages.error(request, 'Both doctor and message are required.')
            return redirect('doctor_chat')

        receiver = get_object_or_404(User, id=receiver_id, is_doctor=True)

        DoctorChat.objects.create(
            sender=request.user,
            receiver=receiver,
            message=message_text
        )
        messages.success(request, f'Message sent to Dr. {receiver.first_name}')
        return redirect('doctor_chat')

    # Fetch recent chat history for displaying (optional)
    chats_sent = DoctorChat.objects.filter(sender=request.user)
    chats_received = DoctorChat.objects.filter(receiver=request.user)
    chats = chats_sent.union(chats_received).order_by('-timestamp')[:20]

    return render(request, 'conversation/doctor_chat.html', {
        'doctors': doctors,
        'chats': chats,
    })
