# drug_checker/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from .models import DrugInteractionCheck

# Common drug interactions database (simplified)
DRUG_INTERACTIONS = {
    'warfarin': {
        'interacts_with': ['aspirin', 'ibuprofen', 'naproxen', 'diclofenac'],
        'severity': 'HIGH',
        'description': 'Increased bleeding risk when combined with NSAIDs'
    },
    'metformin': {
        'interacts_with': ['alcohol', 'furosemide', 'hydrochlorothiazide'],
        'severity': 'MODERATE',
        'description': 'May increase risk of lactic acidosis'
    },
    'digoxin': {
        'interacts_with': ['furosemide', 'hydrochlorothiazide', 'spironolactone'],
        'severity': 'HIGH',
        'description': 'Diuretics can increase digoxin toxicity risk'
    },
    'simvastatin': {
        'interacts_with': ['amiodarone', 'diltiazem', 'verapamil'],
        'severity': 'MODERATE',
        'description': 'Increased risk of muscle damage (myopathy)'
    },
    'lisinopril': {
        'interacts_with': ['spironolactone', 'amiloride', 'triamterene'],
        'severity': 'MODERATE',
        'description': 'Risk of hyperkalemia (high potassium)'
    }
}

@login_required
def drug_checker_home(request):
    if not request.user.is_doctor:
        messages.error(request, 'Access denied. This feature is for doctors only.')
        return redirect('core:home')
    
    recent_checks = DrugInteractionCheck.objects.filter(doctor=request.user)[:10]
    return render(request, 'drug_checker/home.html', {'recent_checks': recent_checks})

@login_required
def check_interactions(request):
    if request.method == 'POST':
        drugs = request.POST.getlist('drugs')
        patient_name = request.POST.get('patient_name', '')
        
        # Clean and normalize drug names
        drugs = [drug.strip().lower() for drug in drugs if drug.strip()]
        
        if len(drugs) < 2:
            messages.error(request, 'Please enter at least 2 drugs to check for interactions.')
            return redirect('drug_checker:home')
        
        interactions_found = []
        highest_severity = 'LOW'
        
        # Check for interactions
        for i, drug1 in enumerate(drugs):
            for drug2 in drugs[i+1:]:
                interaction = check_drug_pair(drug1, drug2)
                if interaction:
                    interactions_found.append(interaction)
                    if get_severity_level(interaction['severity']) > get_severity_level(highest_severity):
                        highest_severity = interaction['severity']
        
        # Save the check to database
        check_record = DrugInteractionCheck.objects.create(
            doctor=request.user,
            patient_name=patient_name,
            drugs_checked=drugs,
            interaction_found=len(interactions_found) > 0,
            severity_level=highest_severity if interactions_found else 'LOW',
            interaction_details=interactions_found
        )
        
        return render(request, 'drug_checker/results.html', {
            'drugs': drugs,
            'patient_name': patient_name,
            'interactions': interactions_found,
            'highest_severity': highest_severity,
            'check_record': check_record
        })
    
    return redirect('drug_checker:home')

def check_drug_pair(drug1, drug2):
    """Check if two drugs interact"""
    # Check both directions
    if drug1 in DRUG_INTERACTIONS:
        if drug2 in DRUG_INTERACTIONS[drug1]['interacts_with']:
            return {
                'drug1': drug1.title(),
                'drug2': drug2.title(),
                'severity': DRUG_INTERACTIONS[drug1]['severity'],
                'description': DRUG_INTERACTIONS[drug1]['description']
            }
    
    if drug2 in DRUG_INTERACTIONS:
        if drug1 in DRUG_INTERACTIONS[drug2]['interacts_with']:
            return {
                'drug1': drug2.title(),
                'drug2': drug1.title(),
                'severity': DRUG_INTERACTIONS[drug2]['severity'],
                'description': DRUG_INTERACTIONS[drug2]['description']
            }
    
    return None

def get_severity_level(severity):
    """Convert severity to numeric level for comparison"""
    levels = {'LOW': 1, 'MODERATE': 2, 'HIGH': 3, 'SEVERE': 4}
    return levels.get(severity, 1)

@login_required
def drug_info(request):
    """Get drug information from OpenFDA API"""
    drug_name = request.GET.get('drug', '')
    
    if not drug_name:
        return JsonResponse({'error': 'No drug name provided'})
    
    try:
        # OpenFDA API call
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}&limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                drug_data = data['results'][0]
                return JsonResponse({
                    'success': True,
                    'drug_name': drug_name,
                    'brand_name': drug_data.get('openfda', {}).get('brand_name', []),
                    'generic_name': drug_data.get('openfda', {}).get('generic_name', []),
                    'manufacturer': drug_data.get('openfda', {}).get('manufacturer_name', []),
                    'warnings': drug_data.get('warnings', ['No warnings available'])[:3]  # Limit to 3
                })
        
        return JsonResponse({'error': 'Drug information not found'})
    
    except Exception as e:
        return JsonResponse({'error': 'Failed to fetch drug information'})

@login_required
def interaction_history(request):
    """View interaction check history"""
    checks = DrugInteractionCheck.objects.filter(doctor=request.user).order_by('-created_at')
    return render(request, 'drug_checker/history.html', {'checks': checks})
