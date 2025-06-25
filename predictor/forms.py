# forms.py
from django import forms
from .models import BreastCancerPrediction, LiverDiseasePrediction,DiabetesPrediction
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

## forms.py
from django import forms
from .models import DiabetesPrediction
from accounts.models import Patient

class DiabetesPredictionForm(forms.ModelForm):
    class Meta:
        model = DiabetesPrediction
        fields = [
            'patient', 'pregnancies', 'glucose', 'blood_pressure', 
            'skin_thickness', 'insulin', 'bmi', 'diabetes_pedigree_function', 'age'
        ]
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'id': 'id_patient',
                'required': True
            }),
            'pregnancies': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Number of pregnancies',
                'min': '0',
                'max': '20'
            }),
            'glucose': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Glucose level (mg/dL)',
                'step': '0.1',
                'min': '0'
            }),
            'blood_pressure': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Blood pressure (mm Hg)',
                'step': '0.1',
                'min': '0'
            }),
            'skin_thickness': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Skin thickness (mm)',
                'step': '0.1',
                'min': '0'
            }),
            'insulin': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Insulin level (mu U/ml)',
                'step': '0.1',
                'min': '0'
            }),
            'bmi': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Body Mass Index',
                'step': '0.1',
                'min': '0'
            }),
            'diabetes_pedigree_function': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Diabetes pedigree function',
                'step': '0.001',
                'min': '0'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Age in years',
                'min': '1',
                'max': '120'
            }),
        }

    def __init__(self, *args, **kwargs):
        doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # Filter patients to show only those belonging to the current doctor
        if doctor:
            self.fields['patient'].queryset = Patient.objects.filter(doctor=doctor)
            self.fields['patient'].empty_label = "Select a patient"
        else:
            self.fields['patient'].queryset = Patient.objects.none()
            
        # Improve patient display format
        self.fields['patient'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} - {obj.email}"

# Add this to your forms.py file

from .models import HeartDiseasePrediction

class HeartDiseasePredictionForm(forms.ModelForm):
    SEX_CHOICES = [
        ('', 'Select Gender'),
        (1, 'Male'),
        (0, 'Female'),
    ]
    
    CP_CHOICES = [
        ('', 'Select Chest Pain Type'),
        (0, 'Typical Angina'),
        (1, 'Atypical Angina'),
        (2, 'Non-Anginal Pain'),
        (3, 'Asymptomatic'),
    ]
    
    FBS_CHOICES = [
        ('', 'Select Fasting Blood Sugar'),
        (0, 'False (≤ 120 mg/dl)'),
        (1, 'True (> 120 mg/dl)'),
    ]
    
    RESTECG_CHOICES = [
        ('', 'Select Resting ECG Results'),
        (0, 'Normal'),
        (1, 'ST-T Wave Abnormality'),
        (2, 'Left Ventricular Hypertrophy'),
    ]
    
    EXANG_CHOICES = [
        ('', 'Exercise Induced Angina'),
        (0, 'No'),
        (1, 'Yes'),
    ]
    
    SLOPE_CHOICES = [
        ('', 'Select ST Slope'),
        (0, 'Upsloping'),
        (1, 'Flat'),
        (2, 'Downsloping'),
    ]
    
    CA_CHOICES = [
        ('', 'Number of Major Vessels'),
        (0, '0'),
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
    ]
    
    THAL_CHOICES = [
        ('', 'Select Thalassemia'),
        (0, 'Normal'),
        (1, 'Fixed Defect'),
        (2, 'Reversible Defect'),
        (3, 'Not Described'),
    ]
    
    sex = forms.ChoiceField(
        choices=SEX_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    cp = forms.ChoiceField(
        choices=CP_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    fbs = forms.ChoiceField(
        choices=FBS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    restecg = forms.ChoiceField(
        choices=RESTECG_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    exang = forms.ChoiceField(
        choices=EXANG_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    slope = forms.ChoiceField(
        choices=SLOPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    ca = forms.ChoiceField(
        choices=CA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    thal = forms.ChoiceField(
        choices=THAL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control glass-input'})
    )
    
    class Meta:
        model = HeartDiseasePrediction
        fields = [
            'patient', 'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 
            'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'
        ]
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'id': 'id_patient',
                'required': True
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Age in years',
                'min': '1',
                'max': '120'
            }),
            'trestbps': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Resting blood pressure (mm Hg)',
                'step': '0.1',
                'min': '0'
            }),
            'chol': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Serum cholesterol (mg/dl)',
                'step': '0.1',
                'min': '0'
            }),
            'thalach': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Maximum heart rate achieved',
                'step': '0.1',
                'min': '0'
            }),
            'oldpeak': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'ST depression induced by exercise',
                'step': '0.1',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # Filter patients to show only those belonging to the current doctor
        if doctor:
            self.fields['patient'].queryset = Patient.objects.filter(doctor=doctor)
            self.fields['patient'].empty_label = "Select a patient"
        else:
            self.fields['patient'].queryset = Patient.objects.none()
            
        # Improve patient display format
        self.fields['patient'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} - {obj.email}"
        
        # Custom field labels
        field_labels = {
            'age': 'Age (years)',
            'sex': 'Gender',
            'cp': 'Chest Pain Type',
            'trestbps': 'Resting Blood Pressure (mm Hg)',
            'chol': 'Serum Cholesterol (mg/dl)',
            'fbs': 'Fasting Blood Sugar > 120 mg/dl',
            'restecg': 'Resting ECG Results',
            'thalach': 'Maximum Heart Rate Achieved',
            'exang': 'Exercise Induced Angina',
            'oldpeak': 'ST Depression Induced by Exercise',
            'slope': 'Slope of Peak Exercise ST Segment',
            'ca': 'Number of Major Vessels (0-4)',
            'thal': 'Thalassemia',
        }
        
        field_help_texts = {
            'trestbps': 'Normal range: 90-140 mm Hg',
            'chol': 'Normal range: < 200 mg/dl',
            'thalach': 'Normal range: 60-100 bpm at rest',
            'oldpeak': 'ST depression relative to rest',
        }
        
        for field_name, field in self.fields.items():
            if field_name in field_labels:
                field.label = field_labels[field_name]
            
            if field_name in field_help_texts:
                field.help_text = field_help_texts[field_name]