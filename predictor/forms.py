# forms.py
from django import forms
from .models import BreastCancerPrediction
from accounts.models import Patient

class PatientSelectionForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control glass-input',
            'placeholder': 'Select Patient'
        })
    )
    
    def __init__(self, doctor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if doctor:
            self.fields['patient'].queryset = Patient.objects.filter(doctor=doctor)

class BreastCancerPredictionForm(forms.ModelForm):
    class Meta:
        model = BreastCancerPrediction
        exclude = ['patient', 'doctor', 'prediction', 'confidence', 'created_at']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control glass-input',
                'step': '0.0001',
                'placeholder': f'Enter {field_name.replace("_", " ").title()}'
            })