from django.urls import path, include
from django.contrib.auth.views import PasswordChangeView
from . import views
from .models import User, Patient

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('password_reset/', views.password_reset_view, name='password_reset'),
    # path('password_reset/verify-otp/', views.password_reset_verify_otp, name='password_reset_verify_otp'),
    path('password_reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    # path('verify-email/', views.verify_email_view, name='verify_email'),
    # path('verify/<uuid:token>/', views.verify_email_view, name='verify_email_token'),
    path('resend-verification/', views.resend_otp, name='resend_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('change-password/', PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/dashboard/'
    ), name='change_password'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('core/', include('core.urls')),
]