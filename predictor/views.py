from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache
import json
from django.urls import reverse
import pickle
import numpy as np
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from accounts.models import Patient
from .models import BreastCancerPrediction, PredictionReport,DiabetesPrediction,HeartDiseasePrediction
from .forms import PatientSelectionForm, BreastCancerPredictionForm,DiabetesPredictionForm,HeartDiseasePredictionForm
from datetime import datetime
import logging
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import LiverDiseasePrediction
from .forms import LiverDiseasePredictionForm
import joblib

logger = logging.getLogger(__name__)

# Cache model loading for performance
def get_cached_model():
    """Load and cache the ML model for better performance"""
    model = cache.get('breast_cancer_model')
    if model is None:
        try:
            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'breast_cancer', 'breast_cancer_prediction_xgb_model.pkl')
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            cache.set('breast_cancer_model', model, 3600)  # Cache for 1 hour
        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            raise
    return model

def prediction(request):
    return render(request, 'predictions/predictors.html')

@login_required
def select_patient(request):
    if request.method == 'POST':
        form = PatientSelectionForm(doctor=request.user, data=request.POST)
        if form.is_valid():
            patient_id = form.cleaned_data['patient'].id
            return redirect('predictor:liver_prediction', patient_id=patient_id)
    else:
        form = PatientSelectionForm(doctor=request.user)
    return render(request, 'predictions/select_patient.html', {'form': form})

import numpy as np

def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj

def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, (np.ndarray, )):
        return obj.tolist()
    return obj

@login_required
def breast_cancer_prediction(request, patient_id=None):
    """
    Handle breast cancer prediction with patient selection and analysis
    """
    # Get all patients for the dropdown
    patients = Patient.objects.filter(doctor=request.user).order_by('first_name', 'last_name')
    
    # Get selected patient if patient_id provided
    selected_patient = None
    if patient_id:
        try:
            selected_patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        except:
            selected_patient = None

    if request.method == 'POST':
        # Handle form submission with patient selection
        try:
            # Get patient from form data
            form_patient_id = request.POST.get('patient_id')
            if not form_patient_id:
                error_message = 'Patient selection is required'
                
                # Handle AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_message}, status=400)
                
                messages.error(request, error_message)
                return render(request, 'predictions/breast_cancer_form.html', {
                    'form': BreastCancerPredictionForm(),
                    'patients': patients,
                    'selected_patient': selected_patient,
                })
            
            # Get the selected patient
            try:
                patient = get_object_or_404(Patient, id=form_patient_id, doctor=request.user)
            except:
                error_message = 'Invalid patient selection'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_message}, status=400)
                
                messages.error(request, error_message)
                return render(request, 'predictions/breast_cancer_form.html', {
                    'form': BreastCancerPredictionForm(),
                    'patients': patients,
                    'selected_patient': selected_patient,
                })
            
            # Validate the form
            form = BreastCancerPredictionForm(request.POST)
            if form.is_valid():
                # Create prediction object
                prediction_obj = form.save(commit=False)
                prediction_obj.patient = patient
                prediction_obj.doctor = request.user
                
                try:
                    # Use cached model for faster prediction
                    model = get_cached_model()  # Specify model type
                    if model is None:
                        raise Exception("Breast cancer prediction model not available")
                    
                    # Prepare features efficiently
                    features_dict = prediction_obj.get_features_dict()
                    features = np.array(list(features_dict.values()), dtype=np.float32).reshape(1, -1)
                    print(features)
                    
                    # Validate features (handle missing values)
                    if np.any(np.isnan(features)) or np.any(np.isinf(features)):
                        # Log warning about missing values
                        logger.warning(f"Missing values detected in prediction for patient {patient.id}")
                        # Handle missing values by replacing with 0 or median values
                        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
                    
                    # Make prediction
                    pred = model.predict(features)[0]
                    prob = model.predict_proba(features)[0]
                    
                    # Store prediction results
                    prediction_obj.prediction = 'Malignant' if pred == 1 else 'Benign'
                    prediction_obj.confidence = float(round(max(prob) * 100, 2))
                    
                    # Store individual probabilities if your model has them
                    if len(prob) > 1:
                        prediction_obj.malignant_probability = float(round(prob[1] * 100, 2))
                        prediction_obj.benign_probability = float(round(prob[0] * 100, 2))
                    
                    # Save the prediction
                    prediction_obj.save()

                    features_dict = convert_numpy_types(features_dict)

                    
                    # Create comprehensive report entry
                    report_data = {
                        'prediction': str(prediction_obj.prediction),
                        'confidence': float(prediction_obj.confidence),
                        'prediction_id': prediction_obj.id,
                        'features': features_dict,
                        'patient_info': {
                            'name': patient.first_name,
                            'gender': patient.gender,
                        }
                    }
                    
                    # Add probability details if available
                    if hasattr(prediction_obj, 'malignant_probability'):
                        report_data['malignant_probability'] = float(prediction_obj.malignant_probability)
                        report_data['benign_probability'] = float(prediction_obj.benign_probability)

                    report_data_clean=make_json_serializable(report_data)
                    report_data_json=json.dumps(report_data_clean)
                    
                    # Create prediction report
                    PredictionReport.objects.create(
                        patient=patient,
                        doctor=request.user,
                        prediction_type='breast_cancer',
                        prediction_data=report_data_json
                    )
                    
                    # Handle AJAX request
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'redirect_url': reverse('predictor:prediction_result', kwargs={'prediction_id': prediction_obj.id}),
                            'prediction': prediction_obj.prediction,
                            'confidence': prediction_obj.confidence
                        })
                    
                    # Add success message
                    messages.success(
                        request, 
                        f'Breast cancer analysis completed for {patient.get_full_name()}. '
                        f'Prediction: {prediction_obj.prediction} ({prediction_obj.confidence}% confidence)'
                    )
                    
                    # Redirect to results page
                    return redirect('predictor:prediction_result', prediction_id=prediction_obj.id)
                    
                except Exception as e:
                    logger.error(f"Prediction failed for patient {patient.id}: {str(e)}")
                    
                    error_message = 'Analysis failed. Please check your input data and try again.'
                    
                    # Handle AJAX request
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': error_message}, status=500)
                    
                    messages.error(request, f'Analysis failed: {str(e)}. Please check your input data and try again.')
                    
                    # Return form with error and maintain patient selection
                    return render(request, 'predictions/breast_cancer_form.html', {
                        'form': form,
                        'patients': patients,
                        'selected_patient': patient,
                    })
            else:
                # Form validation failed
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Invalid form data',
                        'errors': dict(form.errors)
                    }, status=400)
                
                # Get patient for form re-display
                patient = None
                if form_patient_id:
                    try:
                        patient = get_object_or_404(Patient, id=form_patient_id, doctor=request.user)
                    except:
                        pass
                
                messages.error(request, 'Please correct the form errors below.')
                return render(request, 'predictions/breast_cancer_form.html', {
                    'form': form,
                    'patients': patients,
                    'selected_patient': patient,
                })
                
        except Exception as e:
            logger.error(f"Breast cancer prediction error: {str(e)}")
            
            error_message = 'An unexpected error occurred. Please try again.'
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_message}, status=500)
            
            messages.error(request, error_message)
            return render(request, 'predictions/breast_cancer_form.html', {
                'form': BreastCancerPredictionForm(),
                'patients': patients,
                'selected_patient': selected_patient,
            })
    
    else:
        # GET request - show the form
        form = BreastCancerPredictionForm()
        
        # If patient_id provided in URL, pre-select that patient
        if patient_id and selected_patient:
            messages.info(request, f'Selected patient: {selected_patient.get_full_name()}')
    
    return render(request, 'predictions/breast_cancer_form.html', {
        'form': form,
        'patients': patients,
        'selected_patient': selected_patient,
    })


def save_pdf_to_media(buffer, filename, subfolder='reports'):
    """
    Save PDF buffer into MEDIA_ROOT/subfolder and return the relative file path.
    """
    file_path = os.path.join(subfolder, filename)
    default_storage.save(file_path, ContentFile(buffer.read()))
    return file_path

@login_required
def prediction_result(request, prediction_id):
    prediction = get_object_or_404(BreastCancerPrediction, id=prediction_id, doctor=request.user)
    return render(request, 'predictions/result.html', {'prediction': prediction})

def generate_dr_charaka_pdf(prediction, doctor_name):
    """Generate comprehensive Dr. Charaka themed medical report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2E8B57')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#1B4D3E')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Build PDF content
    story = []
    
    # Header with Dr. Charaka branding
    story.append(Paragraph(" DR. CHARAKA MEDICAL AI DIAGNOSTICS", title_style))
    story.append(Paragraph("<i>Ancient Wisdom • Modern Technology • Precise Healthcare</i>", 
                          ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=12, 
                                       alignment=TA_CENTER, textColor=colors.grey, spaceAfter=20)))
    
    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", header_style))
    patient_data = [
        ['Patient Name:', f"{prediction.patient.first_name} {prediction.patient.last_name}"],
        ['Patient ID:', f"DC-{prediction.patient.id:06d}"],
        ['Date of Analysis:', prediction.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Attending Physician:', f"Dr. {doctor_name}"],
        ['Test Type:', 'Breast Cancer Risk Assessment'],
        ['Report ID:', f"BC-{prediction.id:08d}"]
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0E7D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # About Breast Cancer
    story.append(Paragraph("UNDERSTANDING BREAST CANCER", header_style))
    story.append(Paragraph(
        "Breast cancer occurs when cells in breast tissue grow uncontrollably. Early detection through "
        "advanced AI analysis of cellular characteristics significantly improves treatment outcomes. "
        "Our Dr. Charaka AI system analyzes multiple cellular parameters to assess malignancy risk.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # # Clinical Parameters Analyzed
    # story.append(Paragraph("CLINICAL PARAMETERS ANALYZED", header_style))
    # features_dict = prediction.get_features_dict()
    
    # # Group parameters logically
    # param_groups = {
    #     'Nuclear Characteristics': ['radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean', 'smoothness_mean'],
    #     'Cellular Morphology': ['compactness_mean', 'concavity_mean', 'concave_points_mean', 'symmetry_mean', 'fractal_dimension_mean'],
    #     'Variability Measures (SE)': [k for k in features_dict.keys() if '_se' in k],
    #     'Extreme Values (Worst)': [k for k in features_dict.keys() if '_worst' in k]
    # }
    
    # for group_name, params in param_groups.items():
    #     if params:
    #         story.append(Paragraph(f"<b>{group_name}:</b>", 
    #                              ParagraphStyle('subheader', parent=normal_style, fontSize=12, 
    #                                           textColor=colors.HexColor('#2E8B57'), spaceAfter=8)))
            
    #         group_data = []
    #         for param in params:
    #             if param in features_dict:
    #                 param_display = param.replace('_', ' ').title()
    #                 value = features_dict[param]
    #                 group_data.append([param_display, f"{value:.4f}"])
            
    #         if group_data:
    #             param_table = Table(group_data, colWidths=[3*inch, 1.5*inch])
    #             param_table.setStyle(TableStyle([
    #                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F8F0')),
    #                 ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    #                 ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    #                 ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    #                 ('FONTSIZE', (0, 0), (-1, -1), 9),
    #                 ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
    #             ]))
    #             story.append(param_table)
    #             story.append(Spacer(1, 10))
    
    # Analysis Results
    story.append(Paragraph("ANALYSIS RESULTS", header_style))
    
    result_color = colors.HexColor('#228B22') if prediction.prediction == 'Benign' else colors.HexColor('#DC143C')
    result_bg = colors.HexColor('#F0FFF0') if prediction.prediction == 'Benign' else colors.HexColor('#FFF0F0')
    
    result_data = [
        ['Assessment Result:', prediction.prediction],
        ['Confidence Level:', f"{prediction.confidence:.1f}%"],
        ['Risk Category:', 'Low Risk' if prediction.prediction == 'Benign' else 'High Risk - Requires Further Evaluation']
    ]
    
    result_table = Table(result_data, colWidths=[2.5*inch, 3.5*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), result_bg),
        ('TEXTCOLOR', (1, 0), (1, 0), result_color),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0D0D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 20))
    
    # Clinical Interpretation
    story.append(Paragraph("CLINICAL INTERPRETATION", header_style))
    
    if prediction.prediction == 'Benign':
        interpretation = (
            f"Based on the comprehensive analysis of cellular characteristics, the tissue sample shows "
            f"<b>benign patterns</b> with {prediction.confidence:.1f}% confidence. The analyzed parameters "
            f"including nuclear morphology, cellular texture, and structural features are consistent with "
            f"non-malignant tissue. This indicates a lower likelihood of cancerous cells."
        )
    else:
        interpretation = (
            f"The analysis reveals <b>malignant characteristics</b> with {prediction.confidence:.1f}% confidence. "
            f"The cellular parameters show patterns associated with cancerous tissue, including irregular "
            f"nuclear features and abnormal cellular architecture. <b>Immediate consultation with an oncologist "
            f"is strongly recommended for further evaluation and treatment planning.</b>"
        )
    
    story.append(Paragraph(interpretation, normal_style))
    story.append(Spacer(1, 15))
    
    # Recommendations
    story.append(Paragraph("RECOMMENDATIONS", header_style))
    if prediction.prediction == 'Benign':
        recommendations = [
            "Continue regular screening as per standard guidelines",
            "Maintain healthy lifestyle with balanced diet and exercise",
            "Follow up with routine mammography as recommended by your physician",
            "Monitor for any changes and report unusual symptoms promptly"
        ]
    else:
        recommendations = [
            "URGENT: Schedule immediate consultation with oncologist",
            "Additional imaging studies (MRI, CT) may be required",
            "Multidisciplinary team evaluation recommended",
            "Discuss treatment options including surgery, chemotherapy, or radiation",
            "Genetic counseling may be beneficial",
            "Emotional support and counseling services available"
        ]
    
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", normal_style))
    
    story.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    story.append(Paragraph("=" * 80, footer_style))
    story.append(Paragraph(
        f"Report generated by Dr. Charaka AI System • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • "
        f"This report should be interpreted by qualified medical professionals only",
        footer_style
    ))
    
    # Build PDF
    doc.build(story)
    return buffer

@login_required
def generate_pdf_and_email(request, prediction_id):
    prediction = get_object_or_404(BreastCancerPrediction, id=prediction_id, doctor=request.user)
    doctor_name = f"{request.user.first_name} {request.user.last_name}"
    
    try:
        # Generate comprehensive PDF
        buffer = generate_dr_charaka_pdf(prediction, doctor_name)
        
        # Send email if patient email exists
        if prediction.patient.email:
            try:
                # Create beautiful HTML email
                email_context = {
                    'patient_name': prediction.patient.first_name,
                    'doctor_name': doctor_name,
                    'result': prediction.prediction,
                    'confidence': prediction.confidence,
                    'date': prediction.created_at.strftime('%B %d, %Y'),
                    'is_benign': prediction.prediction == 'Benign'
                }
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #2E8B57, #228B22); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .result-box {{ background: {'#e8f5e8' if prediction.prediction == 'Benign' else '#ffe8e8'}; 
                                      border-left: 5px solid {'#228B22' if prediction.prediction == 'Benign' else '#DC143C'}; 
                                      padding: 20px; margin: 20px 0; }}
                        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
                        .logo {{ font-size: 24px; font-weight: bold; }}
                        .highlight {{ color: {'#228B22' if prediction.prediction == 'Benign' else '#DC143C'}; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">DR. CHARAKA</div>
                            <p>Medical AI Diagnostics</p>
                        </div>
                        <div class="content">
                            <h2>Dear {prediction.patient.first_name},</h2>
                            <p>Your breast cancer screening analysis has been completed by our advanced AI diagnostic system.</p>
                            
                            <div class="result-box">
                                <h3>Analysis Results</h3>
                                <p><strong>Result:</strong> <span class="highlight">{prediction.prediction}</span></p>
                                <p><strong>Confidence:</strong> {prediction.confidence:.1f}%</p>
                                <p><strong>Analysis Date:</strong> {prediction.created_at.strftime('%B %d, %Y')}</p>
                                <p><strong>Attending Physician:</strong> Dr. {doctor_name}</p>
                            </div>
                            
                            <p>Please find your detailed medical report attached to this email. The report contains comprehensive analysis of all parameters and clinical recommendations.</p>
                            
                            <p>{'We are pleased to inform you that the analysis indicates benign tissue characteristics.' if prediction.prediction == 'Benign' else 'The analysis requires immediate attention. Please contact your physician urgently to discuss the results and next steps.'}</p>
                            
                            <p><strong>Important:</strong> This analysis should be reviewed with your healthcare provider for proper medical interpretation and follow-up care.</p>
                            
                            <p>If you have any questions, please don't hesitate to contact our clinic.</p>
                            
                            <p>Best regards,<br>
                            <strong>Dr. {doctor_name}</strong><br>
                            Dr. Charaka Medical AI Diagnostics</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message from Dr. Charaka AI System.<br>
                            Please do not reply to this email. Contact your healthcare provider for medical questions.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                email = EmailMessage(
                    subject=f'Dr. Charaka - Medical Analysis Report for {prediction.patient.first_name}',
                    body=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[prediction.patient.email]
                )
                email.content_subtype = "html"
                
                buffer.seek(0)
                email.attach(f'DrCharaka_Report_{prediction.patient.last_name}_{prediction.id}.pdf', 
                           buffer.read(), 'application/pdf')
                email.send()
                
                # Update report status
                report = PredictionReport.objects.filter(
                    prediction_data__prediction_id=prediction.id
                ).first()
                if report:
                    report.pdf_generated = True
                    report.email_sent = True
                    report.save()
                
                messages.success(request, 'Professional medical report generated and emailed successfully!')
                
            except Exception as e:
                logger.error(f"Email failed for prediction {prediction_id}: {str(e)}")
                messages.error(request, 'Report generated but email delivery failed. Please check patient email.')
        else:
            messages.warning(request, 'Report generated but patient email not available for delivery.')
        
        # Save PDF to media storage
        buffer.seek(0)
        filename = f'DrCharaka_Report_{prediction.patient.last_name}_{prediction.id}.pdf'
        saved_file_path = save_pdf_to_media(buffer, filename)

        # Update PredictionReport with saved PDF path
        report = PredictionReport.objects.filter(prediction_data__prediction_id=prediction.id).first()
        if report:
         report.pdf_file.name = saved_file_path
         report.save()
       
        # Return PDF for download
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="DrCharaka_Report_{prediction.patient.last_name}_{prediction.id}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"PDF generation failed for prediction {prediction_id}: {str(e)}")
        messages.error(request, 'Report generation failed. Please try again.')
        return redirect('predictor:prediction_result', prediction_id=prediction_id)
    


@login_required
def reports_view(request):
    """
    Display all prediction reports with filtering capabilities
    """
    # Get all reports for the current doctor
    reports = PredictionReport.objects.filter(doctor=request.user).order_by('-created_at')
    
    # Get all patients for filter dropdown
    patients = Patient.objects.filter(
        Q(prediction_reports__doctor=request.user) |
        Q(breast_cancer_predictions__doctor=request.user)
    ).distinct().order_by('first_name', 'last_name')
    
    # Apply filters
    patient_filter = request.GET.get('patient')
    prediction_type_filter = request.GET.get('prediction_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if patient_filter:
        reports = reports.filter(patient_id=patient_filter)
    
    if prediction_type_filter:
        reports = reports.filter(prediction_type=prediction_type_filter)
    
    if date_from:
        reports = reports.filter(created_at__date__gte=date_from)
    
    if date_to:
        reports = reports.filter(created_at__date__lte=date_to)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        reports = reports.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__email__icontains=search_query) |
            Q(prediction_type__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(reports, 10)  # Show 10 reports per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get prediction types for filter
    prediction_types = PredictionReport.PREDICTION_TYPES
    
    # Statistics
    total_reports = reports.count()
    total_patients = patients.count()
    
    # Reports by type count
    reports_by_type = {}
    for pred_type, display_name in prediction_types:
        count = reports.filter(prediction_type=pred_type).count()
        if count > 0:
            reports_by_type[display_name] = count
    
    context = {
        'reports': page_obj,
        'patients': patients,
        'prediction_types': prediction_types,
        'total_reports': total_reports,
        'total_patients': total_patients,
        'reports_by_type': reports_by_type,
        'current_filters': {
            'patient': patient_filter,
            'prediction_type': prediction_type_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search_query,
        }
    }
    
    return render(request, 'predictions/reports.html', context)

@login_required
def get_report_details(request, report_id):
    """
    AJAX endpoint to get detailed report information
    """
    try:
        report = get_object_or_404(PredictionReport, id=report_id, doctor=request.user)
        
        # Parse prediction data
        prediction_data = report.prediction_data
        
        response_data = {
            'success': True,
            'report': {
                'id': report.id,
                'patient_name': f"{report.patient.first_name} {report.patient.last_name}",
                'patient_email': report.patient.email,
                'prediction_type': report.get_prediction_type_display(),
                'prediction_data': prediction_data,
                'created_at': report.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'pdf_generated': report.pdf_generated,
                'email_sent': report.email_sent,
                'pdf_url': report.pdf_file.url if report.pdf_file else None
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
 
def get_cached_liver_model():
    """Load and cache the liver disease ML model for better performance"""
    model = cache.get('liver_disease_model')
    if model is None:
        try:
            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'liver_disease_predictor', 'predictor_done.pkl')
            
            # Load the dictionary containing model and scaler
            with open(model_path, "rb") as f:
                data = joblib.load(f)
            
            # Extract model from dictionary and cache it
            model = data["model"]
            cache.set('liver_disease_model', model, 3600)  # Cache for 1 hour
            
            logger.info("Liver disease model loaded and cached successfully")
            
        except Exception as e:
            logger.error(f"Liver model loading failed: {str(e)}")
            raise
    return model

def get_cached_liver_model_with_scaler():
    """Load model and scaler if available"""
    model = cache.get('liver_disease_model')
    scaler = cache.get('liver_disease_scaler')
    
    if model is None:
        try:
            model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'liver_disease_predictor', 'predictor_done.pkl')
            
            # Load the dictionary containing model and scaler
            with open(model_path, "rb") as f:
                data = joblib.load(f)
            
            # Extract model and scaler from dictionary
            model = data["model"]
            scaler = data.get("scaler")  # Optional, if you saved it
            
            cache.set('liver_disease_model', model, 3600)
            if scaler:
                cache.set('liver_disease_scaler', scaler, 3600)
                
        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            raise
    
    return model, scaler

# Remove the complex prediction function - keeping it simple and matching your original pattern
@login_required
def liver_disease_prediction(request, patient_id=None):
    # If no patient_id is provided, show patient selection
    if not patient_id:
        patients = Patient.objects.filter(doctor=request.user).order_by('-created_at')
        
        if request.method == 'POST' and 'select_patient' in request.POST:
            selected_patient_id = request.POST.get('patient_id')
            if selected_patient_id:
                return redirect('predictor:liver_prediction', patient_id=selected_patient_id)
        
        return render(request, 'predictions/liver_form.html', {
            'patients': patients,
            'show_patient_selection': True
        })
    
    # If patient_id is provided, show the prediction form
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    
    if request.method == 'POST' and 'predict' in request.POST:
        form = LiverDiseasePredictionForm(request.POST)
        if form.is_valid():
            prediction_obj = form.save(commit=False)
            prediction_obj.patient = patient
            prediction_obj.doctor = request.user
            
            try:
                model, scaler = get_cached_liver_model_with_scaler()
                
                # Prepare features in the correct order
                features = np.array([
                    float(prediction_obj.age),
                    1.0 if prediction_obj.gender == 'Male' else 0.0,
                    float(prediction_obj.total_bilirubin),
                    float(prediction_obj.direct_bilirubin),
                    float(prediction_obj.alkaline_phosphotase),
                    float(prediction_obj.alamine_aminotransferase),
                    float(prediction_obj.aspartate_aminotransferase),
                    float(prediction_obj.total_protiens),
                    float(prediction_obj.albumin),
                    float(prediction_obj.albumin_and_globulin_ratio)
                ], dtype=np.float32).reshape(1, -1)
                
                # Apply scaling if scaler exists
                if scaler:
                    features = scaler.transform(features)
                
                # Make prediction
                prediction = model.predict(features)
                result = 'Disease' if prediction[0] == 1 else 'No Disease'
                
                # Get probabilities with threshold logic
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features)[0]
                    disease_probability = proba[1]
                    no_disease_probability = proba[0]
                    
                    # Apply 0.6/0.4 threshold logic
                    if disease_probability >= 0.6:
                        final_prediction = 'Disease'
                        confidence = round(disease_probability * 100, 2)
                    elif no_disease_probability >= 0.6:
                        final_prediction = 'No Disease'
                        confidence = round(no_disease_probability * 100, 2)
                    else:
                        final_prediction = result
                        confidence = round(max(proba) * 100, 2)
                else:
                    final_prediction = result
                    confidence = 85.0 if result == 'Disease' else 80.0
                    proba = [0.2, 0.8] if result == 'Disease' else [0.8, 0.2]
                
                prediction_obj.prediction = final_prediction
                prediction_obj.confidence = confidence
                prediction_obj.save()
                
                # Create report entry
                PredictionReport.objects.create(
                    patient=patient,
                    doctor=request.user,
                    prediction_type='liver_disease',
                    prediction_data={
                        'prediction': str(prediction_obj.prediction),
                        'confidence': float(prediction_obj.confidence),
                        'prediction_id': prediction_obj.id,
                        'raw_probabilities': proba.tolist() if hasattr(model, 'predict_proba') else proba,
                        'features': dict(zip([
                            'age', 'gender', 'total_bilirubin', 'direct_bilirubin',
                            'alkaline_phosphotase', 'alamine_aminotransferase',
                            'aspartate_aminotransferase', 'total_protiens',
                            'albumin', 'albumin_and_globulin_ratio'
                        ], features.flatten().tolist()))
                    }
                )
                
                return redirect('predictor:liver_prediction_result', prediction_id=prediction_obj.id)
                
            except Exception as e:
                logger.error(f"Liver prediction failed for patient {patient_id}: {str(e)}")
                messages.error(request, 'Liver analysis failed. Please try again.')
    else:
        form = LiverDiseasePredictionForm()
    
    return render(request, 'predictions/liver_form.html', {
        'form': form,
        'patient': patient,
        'show_patient_selection': False
    })

def test_liver_model_with_known_healthy_data():
    """Test with obviously healthy values"""
    try:
        model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'liver_disease_predictor', 'predictor_done.pkl')
        
        # Load the dictionary containing model and scaler
        with open(model_path, "rb") as f:
            data = joblib.load(f)
        
        # Get model and scaler
        model = data["model"]
        scaler = data.get("scaler")  # Optional, if you saved it
        
        # Obviously healthy values (matching your test pattern)
        healthy_data = np.array([[
            30,    # Age
            1,     # Male
            0.5,   # Normal total bilirubin
            0.1,   # Normal direct bilirubin
            85,    # Normal alkaline phosphatase
            20,    # Normal ALT
            22,    # Normal AST
            7.0,   # Normal total proteins
            4.5,   # Normal albumin
            1.5    # Normal A/G ratio
        ]], dtype=np.float32)
        
        # Apply scaling if scaler exists
        if scaler:
            test_data = scaler.transform(healthy_data)
        else:
            test_data = healthy_data
        
        # Predict
        prediction = model.predict(test_data)
        result = 'Liver Disease Detected' if prediction[0] == 1 else 'Disease NOT Detected'
        
        print(f"Healthy test data prediction: {prediction[0]}")
        print(f"Result: {result}")
        
        # If you want probability
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(test_data)
            print(f"Probabilities: {proba}")
        
        return prediction[0], result
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return None, None

@login_required
def liver_prediction_result(request, prediction_id):
    prediction = get_object_or_404(LiverDiseasePrediction, id=prediction_id, doctor=request.user)
    return render(request, 'predictions/liver_result.html', {'prediction': prediction})

def generate_liver_pdf(prediction, doctor_name):
    """Generate comprehensive Dr. Charaka themed liver disease report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4169E1')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Build PDF content
    story = []
    
    # Header with Dr. Charaka branding
    story.append(Paragraph("🏥 DR. CHARAKA LIVER HEALTH ASSESSMENT", title_style))
    story.append(Paragraph("<i>Advanced AI Diagnostics • Liver Function Analysis • Comprehensive Care</i>", 
                          ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=12, 
                                       alignment=TA_CENTER, textColor=colors.grey, spaceAfter=20)))
    
    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", header_style))
    patient_data = [
        ['Patient Name:', f"{prediction.patient.first_name} {prediction.patient.last_name}"],
        ['Patient ID:', f"DC-{prediction.patient.id:06d}"],
        ['Date of Analysis:', prediction.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Attending Physician:', f"Dr. {doctor_name}"],
        ['Test Type:', 'Liver Disease Risk Assessment'],
        ['Report ID:', f"LD-{prediction.id:08d}"],
        ['Age:', f"{prediction.age} years"],
        ['Gender:', prediction.gender]
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F2FF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0E7FF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # About Liver Disease
    story.append(Paragraph("UNDERSTANDING LIVER DISEASE", header_style))
    story.append(Paragraph(
        "Liver disease encompasses various conditions affecting liver function, including hepatitis, "
        "cirrhosis, fatty liver disease, and other hepatic disorders. Early detection through "
        "comprehensive laboratory analysis is crucial for effective treatment and management. "
        "Our Dr. Charaka AI system analyzes multiple liver function parameters to assess disease risk.",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # # Laboratory Parameters
    # story.append(Paragraph("LABORATORY PARAMETERS ANALYZED", header_style))
    # features_dict = prediction.get_features_dict()
    
    # # Group parameters logically
    # param_groups = {
    #     'Bilirubin Levels': ['total_bilirubin', 'direct_bilirubin'],
    #     'Liver Enzymes': ['alkaline_phosphotase', 'alamine_aminotransferase', 'aspartate_aminotransferase'],
    #     'Protein Markers': ['total_protiens', 'albumin', 'albumin_and_globulin_ratio'],
    #     'Demographics': ['age', 'gender']
    # }
    
    # for group_name, params in param_groups.items():
    #     if params:
    #         story.append(Paragraph(f"<b>{group_name}:</b>", 
    #                              ParagraphStyle('subheader', parent=normal_style, fontSize=12, 
    #                                           textColor=colors.HexColor('#4169E1'), spaceAfter=8)))
            
    #         group_data = []
    #         for param in params:
    #             if param in features_dict:
    #                 param_display = param.replace('_', ' ').title()
    #                 value = features_dict[param]
    #                 if param == 'gender':
    #                     group_data.append([param_display, str(value)])
    #                 else:
    #                     group_data.append([param_display, f"{value:.2f}"])
            
    #         if group_data:
    #             param_table = Table(group_data, colWidths=[3*inch, 1.5*inch])
    #             param_table.setStyle(TableStyle([
    #                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F8FF')),
    #                 ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    #                 ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    #                 ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    #                 ('FONTSIZE', (0, 0), (-1, -1), 9),
    #                 ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
    #             ]))
    #             story.append(param_table)
    #             story.append(Spacer(1, 10))
    
    # Analysis Results
    story.append(Paragraph("ANALYSIS RESULTS", header_style))
    
    result_color = colors.HexColor('#228B22') if prediction.prediction == 'No Disease' else colors.HexColor('#DC143C')
    result_bg = colors.HexColor('#F0FFF0') if prediction.prediction == 'No Disease' else colors.HexColor('#FFF0F0')
    
    result_data = [
        ['Assessment Result:', prediction.prediction],
        ['Confidence Level:', f"{prediction.confidence:.1f}%"],
        ['Risk Category:', 'Normal Liver Function' if prediction.prediction == 'No Disease' else 'Abnormal - Requires Medical Attention']
    ]
    
    result_table = Table(result_data, colWidths=[2.5*inch, 3.5*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), result_bg),
        ('TEXTCOLOR', (1, 0), (1, 0), result_color),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0D0D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 20))
    
    # Clinical Interpretation
    story.append(Paragraph("CLINICAL INTERPRETATION", header_style))
    
    if prediction.prediction == 'No Disease':
        interpretation = (
            f"Based on the comprehensive analysis of liver function parameters, the results indicate "
            f"<b>normal liver function</b> with {prediction.confidence:.1f}% confidence. The analyzed "
            f"laboratory values including bilirubin levels, liver enzymes, and protein markers are "
            f"within expected ranges, suggesting healthy liver function."
        )
    else:
        interpretation = (
            f"The analysis reveals <b>abnormal liver function patterns</b> with {prediction.confidence:.1f}% confidence. "
            f"The laboratory parameters show deviations from normal ranges that may indicate liver disease "
            f"or dysfunction. <b>Immediate medical consultation is strongly recommended for further "
            f"evaluation, additional testing, and appropriate treatment planning.</b>"
        )
    
    story.append(Paragraph(interpretation, normal_style))
    story.append(Spacer(1, 15))
    
    # Recommendations
    story.append(Paragraph("RECOMMENDATIONS", header_style))
    if prediction.prediction == 'No Disease':
        recommendations = [
            "Continue maintaining healthy lifestyle with balanced diet",
            "Regular monitoring of liver function as per physician's advice",
            "Avoid excessive alcohol consumption and hepatotoxic substances",
            "Maintain healthy weight and regular exercise routine",
            "Follow up with routine liver function tests as recommended"
        ]
    else:
        recommendations = [
            "URGENT: Schedule immediate consultation with hepatologist/gastroenterologist",
            "Additional liver function tests and imaging studies may be required",
            "Avoid alcohol and hepatotoxic medications until further evaluation",
            "Consider dietary modifications and lifestyle changes",
            "Monitor for symptoms like jaundice, abdominal pain, or fatigue",
            "Family history and genetic counseling may be beneficial"
        ]
    
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", normal_style))
    
    story.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    story.append(Paragraph("=" * 80, footer_style))
    story.append(Paragraph(
        f"Report generated by Dr. Charaka AI System • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • "
        f"This report should be interpreted by qualified medical professionals only",
        footer_style
    ))
    
    # Build PDF
    doc.build(story)
    return buffer

@login_required
def generate_liver_pdf_and_email(request, prediction_id):

    prediction = get_object_or_404(LiverDiseasePrediction, id=prediction_id, doctor=request.user)
    doctor_name = f"{request.user.first_name} {request.user.last_name}"
    
    try:
        # Generate comprehensive PDF
        buffer = generate_liver_pdf(prediction, doctor_name)
        
        # Send email if patient email exists
        if prediction.patient.email:
            try:
                # Create beautiful HTML email
                email_context = {
                    'patient_name': prediction.patient.first_name,
                    'doctor_name': doctor_name,
                    'result': prediction.prediction,
                    'confidence': prediction.confidence,
                    'date': prediction.created_at.strftime('%B %d, %Y'),
                    'is_normal': prediction.prediction == 'No Disease'
                }
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #4169E1, #1E90FF); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .result-box {{ background: {'#e8f5e8' if prediction.prediction == 'No Disease' else '#ffe8e8'}; 
                                      border-left: 5px solid {'#228B22' if prediction.prediction == 'No Disease' else '#DC143C'}; 
                                      padding: 20px; margin: 20px 0; }}
                        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
                        .logo {{ font-size: 24px; font-weight: bold; }}
                        .highlight {{ color: {'#228B22' if prediction.prediction == 'No Disease' else '#DC143C'}; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">🏥 DR. CHARAKA</div>
                            <p>Medical AI Diagnostics - Liver Health Assessment</p>
                        </div>
                        <div class="content">
                            <h2>Dear {prediction.patient.first_name},</h2>
                            <p>Your liver function screening analysis has been completed by our advanced AI diagnostic system.</p>
                            
                            <div class="result-box">
                                <h3>Analysis Results</h3>
                                <p><strong>Result:</strong> <span class="highlight">{prediction.prediction}</span></p>
                                <p><strong>Confidence:</strong> {prediction.confidence:.1f}%</p>
                                <p><strong>Analysis Date:</strong> {prediction.created_at.strftime('%B %d, %Y')}</p>
                                <p><strong>Attending Physician:</strong> Dr. {doctor_name}</p>
                            </div>
                            
                            <p>Please find your detailed liver function report attached to this email. The report contains comprehensive analysis of all laboratory parameters and clinical recommendations.</p>
                            
                            <p>{'Your liver function appears to be normal based on the analyzed parameters.' if prediction.prediction == 'No Disease' else 'The analysis indicates abnormal liver function patterns that require immediate medical attention. Please contact your physician urgently.'}</p>
                            
                            <p><strong>Important:</strong> This analysis should be reviewed with your healthcare provider for proper medical interpretation and follow-up care.</p>
                            
                            <p>If you have any questions, please don't hesitate to contact our clinic.</p>
                            
                            <p>Best regards,<br>
                            <strong>Dr. {doctor_name}</strong><br>
                            Dr. Charaka Medical AI Diagnostics</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message from Dr. Charaka AI System.<br>
                            Please do not reply to this email. Contact your healthcare provider for medical questions.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                email = EmailMessage(
                    subject=f'Dr. Charaka - Liver Function Analysis Report for {prediction.patient.first_name}',
                    body=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[prediction.patient.email]
                )
                email.content_subtype = "html"
                
                buffer.seek(0)
                email.attach(f'DrCharaka_LiverReport_{prediction.patient.last_name}_{prediction.id}.pdf', 
                           buffer.read(), 'application/pdf')
                email.send()
                
                # Update report status
                report = PredictionReport.objects.filter(
                    prediction_data__prediction_id=prediction.id,
                    prediction_type='liver_disease'
                ).first()
                if report:
                    report.pdf_generated = True
                    report.email_sent = True
                    report.save()
                
                messages.success(request, 'Professional liver function report generated and emailed successfully!')
                
            except Exception as e:
                logger.error(f"Email failed for liver prediction {prediction_id}: {str(e)}")
                messages.error(request, 'Report generated but email delivery failed. Please check patient email.')
        else:
            messages.warning(request, 'Report generated but patient email not available for delivery.')
        
        # Save PDF to media storage
        buffer.seek(0)
        filename = f'DrCharaka_LiverReport_{prediction.patient.last_name}_{prediction.id}.pdf'
        saved_file_path = save_pdf_to_media(buffer, filename, subfolder='liver_reports')

        # Update PredictionReport with saved PDF path
        report = PredictionReport.objects.filter(
            prediction_data__prediction_id=prediction.id,
            prediction_type='liver_disease'
        ).first()
        if report:
            report.pdf_file.name = saved_file_path
            report.save()
       
        # Return PDF for download
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="DrCharaka_LiverReport_{prediction.patient.last_name}_{prediction.id}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Liver PDF generation failed for prediction {prediction_id}: {str(e)}")
        messages.error(request, 'Report generation failed. Please try again.')
        return redirect('predictor:liver_prediction_result', prediction_id=prediction_id)
    
# Modified function for loading XGBoost model (no scaler needed)
def get_cached_diabetes_model():
    """Load diabetes XGBoost model from cache or file"""
    cache_key = 'diabetes_xgb_model'
    cached_model = cache.get(cache_key)
    
    if cached_model:
        return cached_model
    
    try:
        model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'diabetes predictor', 'diabetes_prediction_xgb_model.pkl')
        
        with open(model_path, "rb") as f:
            model = joblib.load(f)
        
        # Cache for 1 hour
        cache.set(cache_key, model, 3600)
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load diabetes model: {str(e)}")
        raise

@login_required
def diabetes_prediction(request):
    if request.method == 'POST':
        form = DiabetesPredictionForm(doctor=request.user, data=request.POST)
        if form.is_valid():
            prediction_obj = form.save(commit=False)
            prediction_obj.doctor = request.user
            
            try:
                model = get_cached_diabetes_model()  # No scaler needed for XGBoost
                
                # Prepare features in the correct order (no scaling needed)
                features = np.array([
                    float(prediction_obj.pregnancies),
                    float(prediction_obj.glucose),
                    float(prediction_obj.blood_pressure),
                    float(prediction_obj.skin_thickness),
                    float(prediction_obj.insulin),
                    float(prediction_obj.bmi),
                    float(prediction_obj.diabetes_pedigree_function),
                    float(prediction_obj.age)
                ], dtype=np.float32).reshape(1, -1)
                
                # Make prediction with XGBoost (no scaling required)
                prediction = model.predict(features)
                result = 'Diabetes' if prediction[0] == 1 else 'No Diabetes'
                
                # Get probabilities with threshold logic
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features)[0]
                    diabetes_probability = proba[1]  # Diabetes probability
                    no_diabetes_probability = proba[0]  # No diabetes probability
                    
                    # Apply 0.6/0.4 threshold logic
                    if diabetes_probability >= 0.6:
                        final_prediction = 'Diabetes'
                        confidence = round(diabetes_probability * 100, 2)
                    elif no_diabetes_probability >= 0.6:
                        final_prediction = 'No Diabetes'
                        confidence = round(no_diabetes_probability * 100, 2)
                    else:
                        # Borderline cases - use original prediction but flag as low confidence
                        final_prediction = result
                        confidence = round(max(proba) * 100, 2)
                else:
                    # Fallback if no predict_proba
                    final_prediction = result
                    confidence = 85.0 if result == 'Diabetes' else 80.0
                    proba = [0.2, 0.8] if result == 'Diabetes' else [0.8, 0.2]
                
                prediction_obj.prediction = final_prediction
                prediction_obj.confidence = confidence
                prediction_obj.save()
                
                # Create report entry
                PredictionReport.objects.create(
                    patient=prediction_obj.patient,
                    doctor=request.user,
                    prediction_type='diabetes',
                    prediction_data={
                        'prediction': str(prediction_obj.prediction),
                        'confidence': float(prediction_obj.confidence),
                        'prediction_id': prediction_obj.id,
                        'raw_probabilities': proba.tolist() if hasattr(model, 'predict_proba') else proba,
                        'features': dict(zip([
                            'pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
                            'insulin', 'bmi', 'diabetes_pedigree_function', 'age'
                        ], features.flatten().tolist()))
                    }
                )
                
                return redirect('predictor:diabetes_prediction_result', prediction_id=prediction_obj.id)
                
            except Exception as e:
                logger.error(f"Diabetes prediction failed: {str(e)}")
                print(f"Error details: {str(e)}")
                messages.error(request, f'Diabetes analysis failed. Please try again.')
    
    else:
        form = DiabetesPredictionForm(doctor=request.user)
    
    return render(request, 'predictions/diabetes_form.html', {
        'form': form
    })

@login_required
def diabetes_prediction_result(request, prediction_id):
    prediction = get_object_or_404(DiabetesPrediction, id=prediction_id, doctor=request.user)
    return render(request, 'predictions/diabetes_result.html', {'prediction': prediction})

def generate_diabetes_pdf(prediction, doctor_name):
    """Generate comprehensive Dr. Charaka themed diabetes report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4169E1')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Build PDF content
    story = []
    
    # Header with Dr. Charaka branding
    story.append(Paragraph("🏥 DR. CHARAKA DIABETES RISK ASSESSMENT", title_style))
    story.append(Paragraph("<i>Advanced AI Diagnostics • Diabetes Risk Analysis • Comprehensive Care</i>", 
                          ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=12, 
                                       alignment=TA_CENTER, textColor=colors.grey, spaceAfter=20)))
    
    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", header_style))
    patient_data = [
        ['Patient Name:', f"{prediction.patient.first_name} {prediction.patient.last_name}"],
        ['Patient ID:', f"DC-{prediction.patient.id:06d}"],
        ['Date of Analysis:', prediction.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Attending Physician:', f"Dr. {doctor_name}"],
        ['Test Type:', 'Diabetes Risk Assessment'],
        ['Report ID:', f"DB-{prediction.id:08d}"],
        ['Age:', f"{prediction.age} years"],
        ['BMI:', f"{prediction.bmi}"]
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F2FF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0E7FF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Analysis Results
    story.append(Paragraph("ANALYSIS RESULTS", header_style))
    
    result_color = colors.HexColor('#228B22') if prediction.prediction == 'No Diabetes' else colors.HexColor('#DC143C')
    result_bg = colors.HexColor('#F0FFF0') if prediction.prediction == 'No Diabetes' else colors.HexColor('#FFF0F0')
    
    result_data = [
        ['Assessment Result:', prediction.prediction],
        ['Confidence Level:', f"{prediction.confidence:.1f}%"],
        ['Risk Category:', 'Normal - Low Risk' if prediction.prediction == 'No Diabetes' else 'High Risk - Medical Attention Required']
    ]
    
    result_table = Table(result_data, colWidths=[2.5*inch, 3.5*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), result_bg),
        ('TEXTCOLOR', (1, 0), (1, 0), result_color),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0D0D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(story)
    return buffer

@login_required
def generate_diabetes_pdf_and_email(request, prediction_id):
    prediction = get_object_or_404(DiabetesPrediction, id=prediction_id, doctor=request.user)
    
    try:
        # Generate PDF
        pdf_buffer = generate_diabetes_pdf(prediction, request.user.get_full_name() or request.user.username)
        
        # Save PDF to model
        pdf_filename = f"diabetes_report_{prediction.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create report entry
        report, created = PredictionReport.objects.get_or_create(
            patient=prediction.patient,
            doctor=request.user,
            prediction_type='diabetes',
            defaults={
                'prediction_data': {
                    'prediction': prediction.prediction,
                    'confidence': prediction.confidence,
                    'prediction_id': prediction.id
                }
            }
        )
        
        # Save PDF file
        report.pdf_file.save(
            pdf_filename,
            ContentFile(pdf_buffer.getvalue())
        )
        report.pdf_generated = True
        report.save()
        
        messages.success(request, 'PDF report generated successfully!')
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
        
    except Exception as e:
        logger.error(f"PDF generation failed for diabetes prediction {prediction_id}: {str(e)}")
        messages.error(request, 'Failed to generate PDF report. Please try again.')
        return redirect('predictor:diabetes_prediction_result', prediction_id=prediction_id)


def get_cached_heart_disease_model():
    """Load heart disease model from cache or file"""
    cache_key = 'heart_disease_model'
    cached_model = cache.get(cache_key)
    
    if cached_model:
        return cached_model
    
    try:
        # Adjust this path according to your model location
        model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'heart_disease', 'heart_disease_random_forest_model.pkl')
        
        with open(model_path, "rb") as f:
            model = joblib.load(f)
        
        # Cache for 1 hour
        cache.set(cache_key, model, 3600)
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load heart disease model: {str(e)}")
        raise

@login_required
def heart_disease_prediction(request):
    if request.method == 'POST':
        form = HeartDiseasePredictionForm(doctor=request.user, data=request.POST)
        if form.is_valid():
            prediction_obj = form.save(commit=False)
            prediction_obj.doctor = request.user

            try:
                model = get_cached_heart_disease_model()

                # Extract raw form values (convert categorical string values to integers)
                age = float(prediction_obj.age)
                sex = int(prediction_obj.sex)
                cp = int(prediction_obj.cp)
                trestbps = float(prediction_obj.trestbps)
                chol = float(prediction_obj.chol)
                fbs = int(prediction_obj.fbs)
                restecg = int(prediction_obj.restecg)
                thalach = float(prediction_obj.thalach)
                exang = int(prediction_obj.exang)
                oldpeak = float(prediction_obj.oldpeak)
                slope = int(prediction_obj.slope)
                ca = float(prediction_obj.ca)
                thal = int(prediction_obj.thal)

                # Manual one-hot encoding
                cp_encoded = [1 if cp == i else 0 for i in range(4)]
                restecg_encoded = [1 if restecg == i else 0 for i in range(3)]
                slope_encoded = [1 if slope == i else 0 for i in range(3)]
                thal_encoded = [1 if thal == i else 0 for i in range(3)]

                # Prepare final feature array (numeric + encoded categorical)
                features = np.array([
                    age, sex, trestbps, chol, fbs, thalach, exang, oldpeak, ca
                ] + cp_encoded + restecg_encoded + slope_encoded + thal_encoded, dtype=np.float32).reshape(1, -1)

                # Sanity check - features shape must match model input
                assert features.shape[1] == 22, "Feature shape mismatch!"

                # Prediction
                prediction = model.predict(features)
                result = 'Heart Disease' if prediction[0] == 1 else 'No Heart Disease'

                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features)[0]
                    heart_disease_probability = proba[1]
                    no_heart_disease_probability = proba[0]

                    if heart_disease_probability >= 0.6:
                        final_prediction = 'Heart Disease'
                        confidence = round(heart_disease_probability * 100, 2)
                    elif no_heart_disease_probability >= 0.6:
                        final_prediction = 'No Heart Disease'
                        confidence = round(no_heart_disease_probability * 100, 2)
                    else:
                        final_prediction = result
                        confidence = round(max(proba) * 100, 2)
                else:
                    final_prediction = result
                    confidence = 85.0 if result == 'Heart Disease' else 80.0
                    proba = [0.2, 0.8] if result == 'Heart Disease' else [0.8, 0.2]

                prediction_obj.prediction = final_prediction
                prediction_obj.confidence = confidence
                prediction_obj.save()

                # Create report
                PredictionReport.objects.create(
                    patient=prediction_obj.patient,
                    doctor=request.user,
                    prediction_type='heart_disease',
                    prediction_data={
                        'prediction': str(prediction_obj.prediction),
                        'confidence': float(prediction_obj.confidence),
                        'prediction_id': prediction_obj.id,
                        'raw_probabilities': proba.tolist() if hasattr(model, 'predict_proba') else proba,
                        'features': {
                            'age': age,
                            'sex': sex,
                            'trestbps': trestbps,
                            'chol': chol,
                            'fbs': fbs,
                            'thalach': thalach,
                            'exang': exang,
                            'oldpeak': oldpeak,
                            'ca': ca,
                            'cp': cp,
                            'restecg': restecg,
                            'slope': slope,
                            'thal': thal
                        }
                    }
                )

                return redirect('predictor:heart_disease_prediction_result', prediction_id=prediction_obj.id)

            except Exception as e:
                logger.error(f"Heart disease prediction failed: {str(e)}")
                print(f"Error details: {str(e)}")
                messages.error(request, f'Heart disease analysis failed. Please try again.')

    else:
        form = HeartDiseasePredictionForm(doctor=request.user)

    return render(request, 'predictions/heart_disease_form.html', {
        'form': form
    })

@login_required
def heart_disease_prediction_result(request, prediction_id):
    prediction = get_object_or_404(HeartDiseasePrediction, id=prediction_id, doctor=request.user)
    return render(request, 'predictions/heart_disease_result.html', {'prediction': prediction})

def generate_heart_disease_pdf(prediction, doctor_name):
    """Generate comprehensive Dr. Charaka themed heart disease report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4169E1')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Build PDF content
    story = []
    
    # Header with Dr. Charaka branding
    story.append(Paragraph("DR. CHARAKA HEART DISEASE RISK ASSESSMENT", title_style))
    story.append(Paragraph("<i>Advanced AI Diagnostics • Cardiovascular Risk Analysis • Comprehensive Care</i>", 
                          ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=12, 
                                       alignment=TA_CENTER, textColor=colors.grey, spaceAfter=20)))
    
    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", header_style))
    patient_data = [
        ['Patient Name:', f"{prediction.patient.first_name} {prediction.patient.last_name}"],
        ['Patient ID:', f"DC-{prediction.patient.id:06d}"],
        ['Date of Analysis:', prediction.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Attending Physician:', f"Dr. {doctor_name}"],
        ['Test Type:', 'Heart Disease Risk Assessment'],
        ['Report ID:', f"HD-{prediction.id:08d}"],
        ['Age:', f"{prediction.age} years"],
        ['Gender:', 'Male' if prediction.sex == 1 else 'Female'],
        ['Max Heart Rate:', f"{prediction.thalach} bpm"],
        ['Cholesterol:', f"{prediction.chol} mg/dl"]
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F2FF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0E7FF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Analysis Results
    story.append(Paragraph("ANALYSIS RESULTS", header_style))
    
    result_color = colors.HexColor('#228B22') if prediction.prediction == 'No Heart Disease' else colors.HexColor('#DC143C')
    result_bg = colors.HexColor('#F0FFF0') if prediction.prediction == 'No Heart Disease' else colors.HexColor('#FFF0F0')
    
    result_data = [
        ['Assessment Result:', prediction.prediction],
        ['Confidence Level:', f"{prediction.confidence:.1f}%"],
        ['Risk Category:', 'Normal - Low Risk' if prediction.prediction == 'No Heart Disease' else 'High Risk - Medical Attention Required']
    ]
    
    result_table = Table(result_data, colWidths=[2.5*inch, 3.5*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), result_bg),
        ('TEXTCOLOR', (1, 0), (1, 0), result_color),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D0D0D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(story)
    return buffer

@login_required
def generate_heart_disease_pdf_and_email(request, prediction_id):
    prediction = get_object_or_404(HeartDiseasePrediction, id=prediction_id, doctor=request.user)
    
    try:
        # Generate PDF
        pdf_buffer = generate_heart_disease_pdf(prediction, request.user.get_full_name() or request.user.username)
        
        # Save PDF to model
        pdf_filename = f"heart_disease_report_{prediction.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create report entry
        report, created = PredictionReport.objects.get_or_create(
            patient=prediction.patient,
            doctor=request.user,
            prediction_type='heart_disease',
            defaults={
                'prediction_data': {
                    'prediction': prediction.prediction,
                    'confidence': prediction.confidence,
                    'prediction_id': prediction.id
                }
            }
        )
        
        # Save PDF file
        report.pdf_file.save(
            pdf_filename,
            ContentFile(pdf_buffer.getvalue())
        )
        report.pdf_generated = True
        report.save()
        
        messages.success(request, 'PDF report generated successfully!')
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
        
    except Exception as e:
        logger.error(f"PDF generation failed for heart disease prediction {prediction_id}: {str(e)}")
        messages.error(request, 'Failed to generate PDF report. Please try again.')
        return redirect('predictor:heart_disease_prediction_result', prediction_id=prediction_id)