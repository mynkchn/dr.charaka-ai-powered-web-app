from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
import pickle
import numpy as np
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from accounts.models import Patient
from .models import BreastCancerPrediction, PredictionReport
from .forms import PatientSelectionForm, BreastCancerPredictionForm
from sklearn.preprocessing import StandardScaler


def prediction(request):
    return render(request,'predictions/predictors.html')


@login_required
def select_patient(request):
    if request.method == 'POST':
        form = PatientSelectionForm(doctor=request.user, data=request.POST)
        if form.is_valid():
            patient_id = form.cleaned_data['patient'].id
            return redirect('predictor:breast_cancer_prediction', patient_id=patient_id)
    else:
        form = PatientSelectionForm(doctor=request.user)

    return render(request, 'predictions/select_patient.html', {'form': form})


@login_required
def breast_cancer_prediction(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    if request.method == 'POST':
        form = BreastCancerPredictionForm(request.POST)
        if form.is_valid():
            prediction_obj = form.save(commit=False)
            prediction_obj.patient = patient
            prediction_obj.doctor = request.user

            try:
                # Load model
                model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'breast_cancer', 'breast_cancer_prediction_xgb_model.pkl')
                with open(model_path, 'rb') as f:
                    model = pickle.load(f) 

                # Prepare features
                features = list(prediction_obj.get_features_dict().values())
                features_array = np.array(features).reshape(1, -1).astype(float)  # Use float if needed
                # scaler=StandardScaler()
                # scaled_features = scaler.fit_transform(features_array)

                # Make prediction
                pred = model.predict(features_array)[0]
                prob = model.predict_proba(features_array)[0]

                prediction_obj.prediction = 'Malignant' if pred == 1 else 'Benign'
                prediction_obj.confidence = round(max(prob) * 100, 2)
                prediction_obj.save()

                # Save report
                PredictionReport.objects.create(
                    patient=patient,
                    doctor=request.user,
                    prediction_type='breast_cancer',
                    prediction_data={
                        'prediction': str(prediction_obj.prediction),
                        'confidence': int(prediction_obj.confidence),
                        'prediction_id': int(prediction_obj.id)
                    }
                )

                return redirect('predictor:prediction_result', prediction_id=prediction_obj.id)

            except Exception as e:
                messages.error(request, f'Prediction failed: {str(e)}')

    else:
        form = BreastCancerPredictionForm()

    return render(request, 'predictions/breast_cancer_form.html', {
        'form': form,
        'patient': patient
    })


@login_required
def prediction_result(request, prediction_id):
    prediction = get_object_or_404(BreastCancerPrediction, id=prediction_id, doctor=request.user)
    return render(request, 'predictions/result.html', {'prediction': prediction})


@login_required
def generate_pdf_and_email(request, prediction_id):
    prediction = get_object_or_404(BreastCancerPrediction, id=prediction_id, doctor=request.user)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # PDF Content
    p.drawString(100, 750, "Medical Prediction Report")
    p.drawString(100, 720, f"Patient: {prediction.patient.first_name} {prediction.patient.last_name}")
    p.drawString(100, 700, f"Date: {prediction.created_at.strftime('%Y-%m-%d')}")
    p.drawString(100, 680, "Test: Breast Cancer Screening")
    p.drawString(100, 660, f"Result: {prediction.prediction}")
    p.drawString(100, 640, f"Confidence: {prediction.confidence:.2f}%")
    p.drawString(100, 620, f"Doctor: Dr. {request.user.first_name} {request.user.last_name}")

    p.showPage()
    p.save()

    # Email PDF
    if prediction.patient.email:
        try:
            email = EmailMessage(
                subject=f'Medical Report - {prediction.patient.first_name}',
                body=(
                    f'Dear {prediction.patient.first_name},\n\n'
                    f'Please find your medical report attached.\n\n'
                    f'Best regards,\nDr. {request.user.first_name}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[prediction.patient.email]
            )

            buffer.seek(0)
            email.attach(f'medical_report_{prediction.id}.pdf', buffer.read(), 'application/pdf')
            email.send()

            # Update report status
            report = PredictionReport.objects.filter(
                prediction_data__prediction_id=prediction.id
            ).first()
            if report:
                report.pdf_generated = True
                report.email_sent = True
                report.save()

            messages.success(request, 'PDF generated and emailed successfully!')

        except Exception as e:
            messages.error(request, f'Email failed: {str(e)}')
    else:
        messages.warning(request, 'Patient email not available')

    # Return PDF for download
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{prediction.id}.pdf"'
    return response
