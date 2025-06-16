# urls.py
from django.urls import path
from . import views

app_name='predictor'

urlpatterns = [
    path('prediction/',views.prediction,name='prediction'),
    path('select-patient/', views.select_patient, name='select_patient'),
    path('predict/<int:patient_id>/', views.breast_cancer_prediction, name='breast_cancer_prediction'),
    path('result/<int:prediction_id>/', views.prediction_result, name='prediction_result'),
    path('generate-pdf/<int:prediction_id>/', views.generate_pdf_and_email, name='generate_pdf_email'),
]