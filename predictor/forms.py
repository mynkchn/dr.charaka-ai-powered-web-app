# forms.py
from django import forms
from .models import BreastCancerPrediction, LiverDiseasePrediction
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

class LiverDiseasePredictionForm(forms.ModelForm):
    GENDER_CHOICES = [
        ('', 'Select Gender'),
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control glass-input'
        })
    )
    
    class Meta:
        model = LiverDiseasePrediction
        exclude = ['patient', 'doctor', 'prediction', 'confidence', 'created_at']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Custom field labels and help texts
        field_labels = {
            'age': 'Age (years)',
            'gender': 'Gender',
            'total_bilirubin': 'Total Bilirubin (mg/dL)',
            'direct_bilirubin': 'Direct Bilirubin (mg/dL)',
            'alkaline_phosphotase': 'Alkaline Phosphatase (IU/L)',
            'alamine_aminotransferase': 'Alanine Aminotransferase (ALT) (IU/L)',
            'aspartate_aminotransferase': 'Aspartate Aminotransferase (AST) (IU/L)',
            'total_protiens': 'Total Proteins (g/dL)',
            'albumin': 'Albumin (g/dL)',
            'albumin_and_globulin_ratio': 'Albumin/Globulin Ratio',
        }
        
        field_help_texts = {
            'total_bilirubin': 'Normal range: 0.3-1.2 mg/dL',
            'direct_bilirubin': 'Normal range: 0.1-0.3 mg/dL',
            'alkaline_phosphotase': 'Normal range: 44-147 IU/L',
            'alamine_aminotransferase': 'Normal range: 7-56 IU/L',
            'aspartate_aminotransferase': 'Normal range: 10-40 IU/L',
            'total_protiens': 'Normal range: 6.0-8.3 g/dL',
            'albumin': 'Normal range: 3.5-5.0 g/dL',
            'albumin_and_globulin_ratio': 'Normal range: 1.1-2.5',
        }
        
        for field_name, field in self.fields.items():
            if field_name in field_labels:
                field.label = field_labels[field_name]
            
            if field_name in field_help_texts:
                field.help_text = field_help_texts[field_name]
            
            if field_name != 'gender':
                field.widget.attrs.update({
                    'class': 'form-control glass-input',
                    'step': '0.01' if field_name != 'age' else '1',
                    'placeholder': f'Enter {field_labels.get(field_name, field_name.replace("_", " ").title())}'
                })
            
            # Set input types
            if field_name == 'age':
                field.widget.attrs.update({
                    'type': 'number',
                    'min': '1',
                    'max': '120'
                })
            elif field_name != 'gender':
                field.widget.attrs.update({
                    'type': 'number',
                    'min': '0',
                    'step': '0.01'
                })