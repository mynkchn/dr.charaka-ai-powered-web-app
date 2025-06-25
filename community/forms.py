# community/forms.py
from django import forms
from .models import CaseConsultation, CaseResponse

class CaseConsultationForm(forms.ModelForm):
    class Meta:
        model = CaseConsultation
        fields = [
            'title', 'description', 'patient_age', 'patient_gender',
            'symptoms', 'medical_history', 'current_medications',
            'required_specialization', 'urgency'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief case title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'patient_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'patient_gender': forms.Select(attrs={'class': 'form-control'}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'current_medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'required_specialization': forms.Select(attrs={'class': 'form-control'}),
            'urgency': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient_gender'].choices = [
            ('', 'Select Gender'),
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
        ]
        self.fields['required_specialization'].choices = [
            ('', 'Any Specialization'),
            ('Cardiology', 'Cardiology'),
            ('Neurology', 'Neurology'),
            ('Pediatrics', 'Pediatrics'),
            ('General Medicine', 'General Medicine'),
            ('Surgery', 'Surgery'),
            ('Orthopedics', 'Orthopedics'),
            ('Dermatology', 'Dermatology'),
        ]

class CaseResponseForm(forms.ModelForm):
    class Meta:
        model = CaseResponse
        fields = ['response_text']
        widgets = {
            'response_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your professional opinion and recommendations...'
            })
        }