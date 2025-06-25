# models.py
from django.db import models
from django.conf import settings
import json
from accounts.models import Patient
import os

class BreastCancerPrediction(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='breast_cancer_predictions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Mean features
    mean_radius = models.FloatField()
    mean_texture = models.FloatField()
    mean_perimeter = models.FloatField()
    mean_area = models.FloatField()
    mean_smoothness = models.FloatField()
    mean_compactness = models.FloatField()
    mean_concavity = models.FloatField()
    mean_concave_points = models.FloatField()
    mean_symmetry = models.FloatField()
    mean_fractal_dimension = models.FloatField()
    
    # Error features
    radius_error = models.FloatField()
    texture_error = models.FloatField()
    perimeter_error = models.FloatField()
    area_error = models.FloatField()
    smoothness_error = models.FloatField()
    compactness_error = models.FloatField()
    concavity_error = models.FloatField()
    concave_points_error = models.FloatField()
    symmetry_error = models.FloatField()
    fractal_dimension_error = models.FloatField()
    
    # Worst features
    worst_radius = models.FloatField()
    worst_texture = models.FloatField()
    worst_perimeter = models.FloatField()
    worst_area = models.FloatField()
    worst_smoothness = models.FloatField()
    worst_compactness = models.FloatField()
    worst_concavity = models.FloatField()
    worst_concave_points = models.FloatField()
    worst_symmetry = models.FloatField()
    worst_fractal_dimension = models.FloatField()
    
    # Prediction results
    prediction = models.CharField(max_length=20)  # 'Benign' or 'Malignant'
    confidence = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.prediction}"
    
    def get_features_dict(self):
        """Return all features as a dictionary for ML model"""
        return {
            'mean_radius': self.mean_radius,
            'mean_texture': self.mean_texture,
            'mean_perimeter': self.mean_perimeter,
            'mean_area': self.mean_area,
            'mean_smoothness': self.mean_smoothness,
            'mean_compactness': self.mean_compactness,
            'mean_concavity': self.mean_concavity,
            'mean_concave_points': self.mean_concave_points,
            'mean_symmetry': self.mean_symmetry,
            'mean_fractal_dimension': self.mean_fractal_dimension,
            'radius_error': self.radius_error,
            'texture_error': self.texture_error,
            'perimeter_error': self.perimeter_error,
            'area_error': self.area_error,
            'smoothness_error': self.smoothness_error,
            'compactness_error': self.compactness_error,
            'concavity_error': self.concavity_error,
            'concave_points_error': self.concave_points_error,
            'symmetry_error': self.symmetry_error,
            'fractal_dimension_error': self.fractal_dimension_error,
            'worst_radius': self.worst_radius,
            'worst_texture': self.worst_texture,
            'worst_perimeter': self.worst_perimeter,
            'worst_area': self.worst_area,
            'worst_smoothness': self.worst_smoothness,
            'worst_compactness': self.worst_compactness,
            'worst_concavity': self.worst_concavity,
            'worst_concave_points': self.worst_concave_points,
            'worst_symmetry': self.worst_symmetry,
            'worst_fractal_dimension': self.worst_fractal_dimension,
        }
    

class LiverDiseasePrediction(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='liver_disease_predictions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Liver disease features
    age = models.IntegerField()
    gender = models.CharField(max_length=10)  # 'Male' or 'Female'
    total_bilirubin = models.FloatField()
    direct_bilirubin = models.FloatField()
    alkaline_phosphotase = models.FloatField()
    alamine_aminotransferase = models.FloatField()
    aspartate_aminotransferase = models.FloatField()
    total_protiens = models.FloatField()
    albumin = models.FloatField()
    albumin_and_globulin_ratio = models.FloatField()
    
    # Prediction results
    prediction = models.CharField(max_length=20)  # 'No Disease' or 'Disease'
    confidence = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.prediction}"
    
    def get_features_dict(self):
        """Return all features as a dictionary for ML model"""
        return {
            'Age': self.age,
            'Gender': 1 if self.gender == 'Male' else 0,  # Convert to numeric
            'Total_Bilirubin': self.total_bilirubin,
            'Direct_Bilirubin': self.direct_bilirubin,
            'Alkaline_Phosphotase': self.alkaline_phosphotase,
            'Alamine_Aminotransferase': self.alamine_aminotransferase,
            'Aspartate_Aminotransferase': self.aspartate_aminotransferase,
            'Total_Protiens': self.total_protiens,
            'Albumin': self.albumin,
            'Albumin_and_Globulin_Ratio': self.albumin_and_globulin_ratio,
        }




# Generic prediction model for extensibility
class PredictionReport(models.Model):
    PREDICTION_TYPES = [
        ('breast_cancer', 'Breast Cancer'),
        ('heart_disease', 'Heart Disease'),
        ('diabetes', 'Diabetes'),
        # Add more as needed
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prediction_reports')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prediction_type = models.CharField(max_length=50, choices=PREDICTION_TYPES)
    prediction_data = models.JSONField()  # Store prediction details
    pdf_generated = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file=models.FileField(upload_to='reports/',blank=True,null=True)
    
    def __str__(self):
        return f"{self.patient} - {self.prediction_type} - {self.created_at.date()}"
    
    # Add this to your existing models.py

class DiabetesPrediction(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diabetes_predictions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Diabetes features
    pregnancies = models.IntegerField()
    glucose = models.FloatField()
    blood_pressure = models.FloatField()
    skin_thickness = models.FloatField()
    insulin = models.FloatField()
    bmi = models.FloatField()
    diabetes_pedigree_function = models.FloatField()
    age = models.IntegerField()
    
    # Prediction results
    prediction = models.CharField(max_length=20)  # 'No Diabetes' or 'Diabetes'
    confidence = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.prediction}"
    
    def get_features_dict(self):
        """Return all features as a dictionary for ML model"""
        return {
            'Pregnancies': self.pregnancies,
            'Glucose': self.glucose,
            'BloodPressure': self.blood_pressure,
            'SkinThickness': self.skin_thickness,
            'Insulin': self.insulin,
            'BMI': self.bmi,
            'DiabetesPedigreeFunction': self.diabetes_pedigree_function,
            'Age': self.age,
        }
    
# Add this to your models.py file

class HeartDiseasePrediction(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='heart_disease_predictions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Heart disease features
    age = models.IntegerField()
    sex = models.IntegerField()  # 1 = male, 0 = female
    cp = models.IntegerField()  # chest pain type (0-3)
    trestbps = models.FloatField()  # resting blood pressure
    chol = models.FloatField()  # serum cholesterol in mg/dl
    fbs = models.IntegerField()  # fasting blood sugar > 120 mg/dl (1 = true, 0 = false)
    restecg = models.IntegerField()  # resting electrocardiographic results (0-2)
    thalach = models.FloatField()  # maximum heart rate achieved
    exang = models.IntegerField()  # exercise induced angina (1 = yes, 0 = no)
    oldpeak = models.FloatField()  # ST depression induced by exercise relative to rest
    slope = models.IntegerField()  # slope of peak exercise ST segment (0-2)
    ca = models.IntegerField()  # number of major vessels colored by fluoroscopy (0-4)
    thal = models.IntegerField()  # thalassemia (0-3)
    
    # Prediction results
    prediction = models.CharField(max_length=20)  # 'No Heart Disease' or 'Heart Disease'
    confidence = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.prediction}"
    
    def get_features_dict(self):
        """Return all features as a dictionary for ML model"""
        return {
            'age': self.age,
            'sex': self.sex,
            'cp': self.cp,
            'trestbps': self.trestbps,
            'chol': self.chol,
            'fbs': self.fbs,
            'restecg': self.restecg,
            'thalach': self.thalach,
            'exang': self.exang,
            'oldpeak': self.oldpeak,
            'slope': self.slope,
            'ca': self.ca,
            'thal': self.thal,
        }