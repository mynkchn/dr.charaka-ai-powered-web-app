from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import User, Patient
from .models import Profile

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    is_doctor = forms.BooleanField(required=False, label='Register as a Doctor')
    specialization = forms.CharField(required=False, max_length=100)
    license_number = forms.CharField(required=False, max_length=50)
    years_of_experience = forms.IntegerField(required=False, min_value=0)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_doctor', 'specialization', 'license_number', 'years_of_experience')

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'email',
            'first_name',
            'last_name',
            'password1',
            'password2',
            'is_doctor',
            Div(
                'specialization',
                'license_number',
                'years_of_experience',
                css_id='doctor-fields',
                style='display: none;'
            ),
            Submit('submit', 'Register', css_class='btn btn-primary')
        )
        
        # Add help text for password fields
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters and can\'t be entirely numeric.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
        
        # Make email field required and unique
        self.fields['email'].required = True
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        
        # Add validation for required fields
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        print("Validating email:", email)  # Debug print
        if User.objects.filter(email=email).exists():
            print("Email already exists")  # Debug print
            raise forms.ValidationError('This email address is already registered.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        print("Cleaned data:", cleaned_data)  # Debug print
        if cleaned_data.get('is_doctor'):
            if not cleaned_data.get('specialization'):
                self.add_error('specialization', 'Specialization is required for doctors')
            if not cleaned_data.get('license_number'):
                self.add_error('license_number', 'License number is required for doctors')
            if not cleaned_data.get('years_of_experience'):
                self.add_error('years_of_experience', 'Years of experience is required for doctors')
        return cleaned_data

    def save(self, commit=True):
        print("Saving form data")  # Debug print
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Use email as username
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_doctor = self.cleaned_data.get('is_doctor', False)
        user.specialization = self.cleaned_data.get('specialization', '')
        user.license_number = self.cleaned_data.get('license_number', '')
        user.years_of_experience = self.cleaned_data.get('years_of_experience', 0)
        if commit:
            print("Committing user to database")  # Debug print
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    
    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password',
            Submit('submit', 'Login', css_class='btn btn-primary')
        )

class CustomPasswordResetForm(PasswordResetForm):
    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'email',
            Submit('submit', 'Reset Password', css_class='btn btn-primary')
        )

class CustomSetPasswordForm(SetPasswordForm):
    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'new_password1',
            'new_password2',
            Submit('submit', 'Change Password', css_class='btn btn-primary')
        )

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))

class DoctorSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    medical_license = forms.CharField(max_length=50, required=True, 
        help_text='Your medical license number')
    specialization = forms.CharField(max_length=100, required=True,
        help_text='Your medical specialization')
    experience_years = forms.IntegerField(required=True, min_value=0,
        help_text='Years of experience')
    doctor_id = forms.CharField(max_length=50, required=True,
        help_text='Your unique doctor ID')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 
                 'medical_license', 'specialization', 'experience_years', 'doctor_id')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_doctor = True
        user.medical_license = self.cleaned_data['medical_license']
        user.specialization = self.cleaned_data['specialization']
        user.experience_years = self.cleaned_data['experience_years']
        user.doctor_id = self.cleaned_data['doctor_id']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'specialization', 'license_number', 'years_of_experience')
        widgets = {
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'contact_number', 
                 'email', 'address', 'medical_history', 'allergies']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'medical_history': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'allergies': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        for field in self.fields:
            if field not in ['medical_history', 'allergies', 'address']:
                self.fields[field].widget.attrs.update({'class': 'form-control'}) 

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'phone', 'gender', 'date_of_birth', 'specialization', 'license_number', 'years_of_experience']