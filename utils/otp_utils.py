
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

def generate_and_send_otp(email):
    otp = random.randint(100000, 999999)
    cache.set(f'otp_{email}', otp, timeout=300)  # 5 minutes expiry

    send_mail(
        subject="Your Verification OTP",
        message=f"Your OTP is {otp}. It is valid for 5 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email]
    )
    return otp

def verify_otp(email, otp_input):
    cached_otp = cache.get(f'otp_{email}')
    return cached_otp and str(cached_otp) == str(otp_input)