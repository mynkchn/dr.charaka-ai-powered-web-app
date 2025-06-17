from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, PatientForm
from .models import User, Patient
import uuid
import random
import hashlib
import time
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm

# Efficient OTP generation using hash-based algorithm
def generate_otp():
    """Generate 6-digit OTP using efficient hash-based method"""
    timestamp = str(int(time.time()))
    random_seed = str(random.randint(100000, 999999))
    hash_input = f"{timestamp}{random_seed}".encode()
    hash_digest = hashlib.sha256(hash_input).hexdigest()
    otp = str(int(hash_digest[:8], 16))[-6:].zfill(6)
    return otp

def register_view(request):
    """Fixed registration - only creates user AFTER OTP verification"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Store form data in session instead of creating user immediately
            user_data = {
                'username': form.cleaned_data['email'],
                'email': form.cleaned_data['email'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'password': form.cleaned_data['password1'],
                'is_doctor': form.cleaned_data.get('is_doctor', False),
            }
            
            # Add doctor-specific fields if applicable
            if user_data['is_doctor']:
                user_data.update({
                    'specialization': form.cleaned_data.get('specialization', ''),
                    'license_number': form.cleaned_data.get('license_number', ''),
                    'years_of_experience': form.cleaned_data.get('years_of_experience', 0),
                })
            
            # Store user data in session
            request.session['pending_user_data'] = user_data
            
            # Generate OTP
            otp = generate_otp()
            request.session['registration_otp'] = otp
            request.session['otp_email'] = user_data['email']
            request.session['otp_timestamp'] = time.time()
            
            # Send OTP email
            context = {
                'first_name': user_data['first_name'],
                'otp': otp
            }
            html_message = render_to_string('accounts/email/verify_email_otp.html', context)
            plain_message = strip_tags(html_message)
            
            try:
                send_mail(
                    'Verify your email - Dr. Charaka',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_data['email']],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Registration initiated! Please check your email for the OTP to complete registration.')
                return redirect('accounts:verify_otp')
            except Exception as e:
                messages.error(request, 'Error sending verification email. Please try again.')
                return render(request, 'accounts/register.html', {'form': form})
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def verify_otp_view(request):
    """Enhanced OTP verification with better security and user experience"""
    # Check if there's pending user data or reset data
    pending_user_data = request.session.get('pending_user_data')
    reset_email = request.session.get('reset_email')
    otp_email = request.session.get('otp_email')
    otp_timestamp = request.session.get('otp_timestamp', 0)
    
    # Check OTP expiry (5 minutes)
    if time.time() - otp_timestamp > 300:  # 5 minutes
        messages.error(request, 'OTP has expired. Please try again.')
        if pending_user_data:
            return redirect('accounts:signup')
        elif reset_email:
            return redirect('accounts:password_reset')
        else:
            return redirect('accounts:login')
    
    if request.method == 'POST':
        otp = ''.join(request.POST.getlist('otp'))  # Handle individual digit inputs
        
        # Check registration OTP
        stored_registration_otp = request.session.get('registration_otp')
        stored_reset_otp = request.session.get('reset_otp')
        
        if otp == stored_registration_otp and pending_user_data:
            try:
                # Create user after successful OTP verification
                user = User.objects.create_user(
                    username=pending_user_data['username'],
                    email=pending_user_data['email'],
                    password=pending_user_data['password'],
                    first_name=pending_user_data['first_name'],
                    last_name=pending_user_data['last_name'],
                )
                
                # Set additional fields
                user.is_doctor = pending_user_data['is_doctor']
                user.email_verified = True  # Mark as verified since OTP was successful
                
                if user.is_doctor:
                    user.specialization = pending_user_data.get('specialization', '')
                    user.license_number = pending_user_data.get('license_number', '')
                    user.years_of_experience = pending_user_data.get('years_of_experience', 0)
                
                user.save()
                
                # Clear session data
                request.session.pop('pending_user_data', None)
                request.session.pop('registration_otp', None)
                request.session.pop('otp_email', None)
                request.session.pop('otp_timestamp', None)
                
                # Log user in
                login(request, user)
                messages.success(request, 'Registration completed successfully! Welcome to Dr. Charaka.')
                return redirect('core:home')
                
            except Exception as e:
                messages.error(request, 'Error creating account. Please try again.')
                return redirect('accounts:signup')
                
        elif otp == stored_reset_otp and reset_email:
            # Handle password reset OTP
            request.session['reset_otp_verified'] = True
            return redirect('accounts:password_reset_confirm')
            
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    # Determine the context for the template
    context = {
        'email': otp_email,
        'is_registration': bool(pending_user_data),
        'is_password_reset': bool(reset_email),
        'expires_in': max(0, 300 - int(time.time() - otp_timestamp)),  # Time remaining in seconds
    }
    
    return render(request, 'accounts/verify_otp.html', context)

def login_view(request):
    """Fixed login - no OTP sending, only authenticates verified users"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.email_verified:
                login(request, user)
                return redirect('core:home')
            else:
                messages.error(request, 'Please complete your registration by verifying your email address.')
                return redirect('accounts:signup')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def signup_view(request):
    """Redirect to register_view for consistency"""
    return register_view(request)

def resend_otp(request):
    """Resend OTP for current session"""
    if request.method == 'POST':
        otp_email = request.session.get('otp_email')
        pending_user_data = request.session.get('pending_user_data')
        reset_email = request.session.get('reset_email')
        
        if not otp_email:
            messages.error(request, 'No active OTP session found.')
            return redirect('accounts:login')
        
        # Generate new OTP
        otp = generate_otp()
        request.session['otp_timestamp'] = time.time()
        
        if pending_user_data:
            request.session['registration_otp'] = otp
            template = 'accounts/email/verify_email_otp.html'
            subject = 'Verify your email - Dr. Charaka'
            context = {'first_name': pending_user_data['first_name'], 'otp': otp}
        elif reset_email:
            request.session['reset_otp'] = otp
            template = 'accounts/email/reset_password_otp.html'
            subject = 'Reset Your Password - Dr. Charaka'
            try:
                user = User.objects.get(email=reset_email)
                context = {'user': user, 'otp': otp}
            except User.DoesNotExist:
                messages.error(request, 'Invalid session.')
                return redirect('accounts:password_reset')
        else:
            messages.error(request, 'Invalid session.')
            return redirect('accounts:login')
        
        # Send new OTP
        try:
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [otp_email],
                html_message=html_message,
                fail_silently=False,
            )
            messages.success(request, 'New OTP sent successfully!')
        except Exception as e:
            messages.error(request, 'Error sending OTP. Please try again.')
    
    return redirect('accounts:verify_otp')

def password_reset_view(request):
    """Enhanced password reset with OTP"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/password_reset.html')
            
        try:
            user = User.objects.get(email=email)
            # Generate OTP
            otp = generate_otp()
            request.session['reset_otp'] = otp
            request.session['reset_email'] = email
            request.session['otp_email'] = email
            request.session['otp_timestamp'] = time.time()
            
            # Send OTP email
            context = {'user': user, 'otp': otp}
            html_message = render_to_string('accounts/email/reset_password_otp.html', context)
            plain_message = strip_tags(html_message)
            
            try:
                send_mail(
                    'Reset Your Password - Dr. Charaka',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'OTP has been sent to your email address.')
                return redirect('accounts:verify_otp')
            except Exception as e:
                messages.error(request, f'Error sending email: {str(e)}')
                return render(request, 'accounts/password_reset.html')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    return render(request, 'accounts/password_reset.html')

def password_reset_confirm(request):
    """Password reset confirmation after OTP verification"""
    if not request.session.get('reset_otp_verified'):
        messages.error(request, 'Please verify OTP first.')
        return redirect('accounts:password_reset_view')
        
    if request.method == 'POST':
        email = request.session.get('reset_email')
        if not email:
            messages.error(request, 'Session expired. Please try again.')
            return redirect('accounts:password_reset_view')
            
        try:
            user = User.objects.get(email=email)
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                # Clear session data
                request.session.pop('reset_otp', None)
                request.session.pop('reset_email', None)
                request.session.pop('reset_otp_verified', None)
                request.session.pop('otp_email', None)
                request.session.pop('otp_timestamp', None)
                
                messages.success(request, 'Your password has been reset successfully. You can now login.')
                return redirect('accounts:login')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('accounts:password_reset_view')
    else:
        try:
            user = User.objects.get(email=request.session.get('reset_email'))
            form = SetPasswordForm(user)
        except User.DoesNotExist:
            messages.error(request, 'Invalid session.')
            return redirect('accounts:password_reset')
    
    return render(request, 'accounts/password_reset_confirm.html', {'form': form})

# Keep other existing views unchanged
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('core:home')

@login_required
def dashboard_view(request):
    if request.user.is_doctor:
        patients = Patient.objects.filter(doctor=request.user)
        
        if request.method == 'POST':
            form = PatientForm(request.POST)
            if form.is_valid():
                try:
                    patient = form.save(commit=False)
                    patient.doctor = request.user
                    patient.save()
                    messages.success(request, 'Patient added successfully!')
                    # Redirect to prevent form resubmission
                    return redirect('accounts:dashboard')
                except Exception as e:
                    messages.error(request, f'Error saving patient: {str(e)}')
                    # Return form with errors
                    return render(request, 'accounts/dashboard.html', {
                        'patients': patients,
                        'form': form
                    })
            else:
                # Form has validation errors
                messages.error(request, 'Please correct the errors below.')
                return render(request, 'accounts/dashboard.html', {
                    'patients': patients,
                    'form': form
                })
        else:
            # GET request - show empty form
            form = PatientForm()
            
        return render(request, 'accounts/dashboard.html', {
            'patients': patients,
            'form': form
        })
    else:
        # Patient dashboard
        return render(request, 'accounts/dashboard.html')

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:dashboard')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})