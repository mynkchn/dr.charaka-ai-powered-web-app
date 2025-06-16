from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache
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
from .models import BreastCancerPrediction, PredictionReport
from .forms import PatientSelectionForm, BreastCancerPredictionForm
from datetime import datetime
import logging

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
                # Use cached model for faster prediction
                model = get_cached_model()

                # Prepare features efficiently
                features = np.array(list(prediction_obj.get_features_dict().values()), dtype=np.float32).reshape(1, -1)

                # Make prediction
                pred = model.predict(features)[0]
                prob = model.predict_proba(features)[0]

                prediction_obj.prediction = 'Malignant' if pred == 1 else 'Benign'
                prediction_obj.confidence = round(max(prob) * 100, 2)
                prediction_obj.save()

                # Create report entry
                PredictionReport.objects.create(
                    patient=patient,
                    doctor=request.user,
                    prediction_type='breast_cancer',
                    prediction_data={
                        'prediction': str(prediction_obj.prediction),
                        'confidence': float(prediction_obj.confidence),
                        'prediction_id': prediction_obj.id,
                        'features': prediction_obj.get_features_dict()
                    }
                )

                return redirect('predictor:prediction_result', prediction_id=prediction_obj.id)

            except Exception as e:
                logger.error(f"Prediction failed for patient {patient_id}: {str(e)}")
                messages.error(request, f'Analysis failed. Please try again.')

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
    
    # Clinical Parameters Analyzed
    story.append(Paragraph("CLINICAL PARAMETERS ANALYZED", header_style))
    features_dict = prediction.get_features_dict()
    
    # Group parameters logically
    param_groups = {
        'Nuclear Characteristics': ['radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean', 'smoothness_mean'],
        'Cellular Morphology': ['compactness_mean', 'concavity_mean', 'concave_points_mean', 'symmetry_mean', 'fractal_dimension_mean'],
        'Variability Measures (SE)': [k for k in features_dict.keys() if '_se' in k],
        'Extreme Values (Worst)': [k for k in features_dict.keys() if '_worst' in k]
    }
    
    for group_name, params in param_groups.items():
        if params:
            story.append(Paragraph(f"<b>{group_name}:</b>", 
                                 ParagraphStyle('subheader', parent=normal_style, fontSize=12, 
                                              textColor=colors.HexColor('#2E8B57'), spaceAfter=8)))
            
            group_data = []
            for param in params:
                if param in features_dict:
                    param_display = param.replace('_', ' ').title()
                    value = features_dict[param]
                    group_data.append([param_display, f"{value:.4f}"])
            
            if group_data:
                param_table = Table(group_data, colWidths=[3*inch, 1.5*inch])
                param_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F8F0')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                ]))
                story.append(param_table)
                story.append(Spacer(1, 10))
    
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
        
        # Return PDF for download
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="DrCharaka_Report_{prediction.patient.last_name}_{prediction.id}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"PDF generation failed for prediction {prediction_id}: {str(e)}")
        messages.error(request, 'Report generation failed. Please try again.')
        return redirect('predictor:prediction_result', prediction_id=prediction_id)