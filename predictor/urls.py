from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'predictor'

urlpatterns = [
    # Breast Cancer Prediction
    path('prediction/', views.prediction, name='prediction'),
    path('select-patient/', views.select_patient, name='select_patient'),
    path('predict/<int:patient_id>/', views.breast_cancer_prediction, name='breast_cancer_prediction'),
    path('result/<int:prediction_id>/', views.prediction_result, name='prediction_result'),
    path('generate-pdf/<int:prediction_id>/', views.generate_pdf_and_email, name='generate_pdf_email'),
    path('reports/', views.reports_view, name='reports_view'),

    # Liver Disease Prediction

    # Form for liver disease prediction
    path('liver-predict/<int:patient_id>/', views.liver_disease_prediction, name='liver_prediction'),

    # Result view for liver disease prediction
    path('liver-result/<int:prediction_id>/', views.liver_prediction_result, name='liver_prediction_result'),

    # PDF generation & Email for liver disease prediction
    path('liver-generate-pdf/<int:prediction_id>/', views.generate_liver_pdf_and_email, name='generate_liver_pdf_and_email'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
