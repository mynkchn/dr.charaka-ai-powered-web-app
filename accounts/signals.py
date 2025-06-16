from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import requests

def get_location_from_ip(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}')
        data = response.json()
        if data['status'] == 'success':
            return f"{data['city']}, {data['country']}"
        return "Unknown Location"
    except:
        return "Unknown Location"

@receiver(user_logged_in)
def send_login_notification(sender, request, user, **kwargs):
    # Get user's IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Get location from IP
    location = get_location_from_ip(ip)
    
    # Prepare email context
    context = {
        'user': request.user,
        'location': location,
        'ip': ip,
        'login_time': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Now'
    }
    
    # Render email template
    html_message = render_to_string('accounts/email/login_notification.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject='Welcome to Dr. Charaka!',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True
    ) 