# community/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import CaseConsultation, CaseResponse, CaseVote
from .forms import CaseConsultationForm, CaseResponseForm
import time
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

@login_required
def community_home(request):
    # Get recent cases based on user's specialization
    if request.user.specialization:
        cases = CaseConsultation.objects.filter(
            Q(required_specialization=request.user.specialization) | 
            Q(required_specialization__isnull=True),
            status='OPEN'
        )[:10]
    else:
        cases = CaseConsultation.objects.filter(status='OPEN')[:10]
    
    # Get user's submitted cases
    my_cases = CaseConsultation.objects.filter(submitting_doctor=request.user)[:5]
    
    context = {
        'recent_cases': cases,
        'my_cases': my_cases,
    }
    return render(request, 'community/home.html', context)

@login_required
def case_list(request):
    cases = CaseConsultation.objects.filter(status='OPEN')
    
    # Filter by specialization
    specialization = request.GET.get('specialization')
    if specialization:
        cases = cases.filter(required_specialization=specialization)
    
    # Filter by urgency
    urgency = request.GET.get('urgency')
    if urgency:
        cases = cases.filter(urgency=urgency)
    
    context = {
        'cases': cases,
        'specializations': ['Cardiology', 'Neurology', 'Pediatrics', 'General Medicine', 'Surgery'],
        'urgency_choices': CaseConsultation.URGENCY_CHOICES,
    }
    return render(request, 'community/case_list.html', context)

@login_required
def case_detail(request, case_id):
    case = get_object_or_404(CaseConsultation, id=case_id)
    responses = CaseResponse.objects.filter(case=case)
    
    if request.method == 'POST':
        form = CaseResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.case = case
            response.responding_doctor = request.user
            response.save()
            messages.success(request, 'Your response has been submitted!')
            return redirect('case_detail', case_id=case.id)
    else:
        form = CaseResponseForm()
    
    context = {
        'case': case,
        'responses': responses,
        'form': form,
    }
    return render(request, 'community/case_detail.html', context)

@login_required
def submit_case(request):
    if request.method == 'POST':
        form = CaseConsultationForm(request.POST)
        if form.is_valid():
            case = form.save(commit=False)
            case.submitting_doctor = request.user
            case.save()
            messages.success(request, 'Case submitted successfully!')
            return redirect('case_detail', case_id=case.id)
    else:
        form = CaseConsultationForm()
    
    return render(request, 'community/submit_case.html', {'form': form})
@login_required
def my_cases(request):
    """
    Display user's submitted cases with proper statistics
    """
    # Get all cases for the current user
    cases = CaseConsultation.objects.filter(submitting_doctor=request.user).prefetch_related('responses')
    
    # Calculate statistics
    total_cases = cases.count()
    open_cases_count = cases.filter(status='OPEN').count()
    resolved_cases_count = cases.filter(status='RESOLVED').count()
    closed_cases_count = cases.filter(status='CLOSED').count()
    
    # Calculate total responses across all cases
    total_responses = sum(case.responses.count() for case in cases)
    
    # Alternative way to calculate total responses using aggregation (more efficient for large datasets)
    # total_responses = cases.aggregate(
    #     total=Count('responses')
    # )['total'] or 0
    
    context = {
        'cases': cases,
        'total_cases': total_cases,
        'open_cases_count': open_cases_count,
        'resolved_cases_count': resolved_cases_count,
        'closed_cases_count': closed_cases_count,
        'total_responses': total_responses,
    }
    
    return render(request, 'community/my_cases.html', context)


# Additional helper view for getting statistics via AJAX if needed
@login_required
def case_statistics(request):
    """
    Return case statistics as JSON
    """
    cases = CaseConsultation.objects.filter(submitting_doctor=request.user)
    
    stats = {
        'total_cases': cases.count(),
        'open_cases': cases.filter(status='OPEN').count(),
        'resolved_cases': cases.filter(status='RESOLVED').count(),
        'closed_cases': cases.filter(status='CLOSED').count(),
        'total_responses': sum(case.responses.count() for case in cases),
        'cases_by_urgency': {
            'low': cases.filter(urgency='LOW').count(),
            'medium': cases.filter(urgency='MEDIUM').count(),
            'high': cases.filter(urgency='HIGH').count(),
            'critical': cases.filter(urgency='CRITICAL').count(),
        }
    }
    
    return JsonResponse(stats)

@login_required
def vote_response(request):
    if request.method == 'POST':
        response_id = request.POST.get('response_id')
        is_helpful = request.POST.get('is_helpful') == 'true'
        
        response = get_object_or_404(CaseResponse, id=response_id)
        
        # Check if user already voted
        vote, created = CaseVote.objects.get_or_create(
            response=response,
            voter=request.user,
            defaults={'is_helpful': is_helpful}
        )
        
        if not created:
            # Update existing vote
            vote.is_helpful = is_helpful
            vote.save()
        
        # Update helpful votes count
        helpful_count = CaseVote.objects.filter(response=response, is_helpful=True).count()
        response.helpful_votes = helpful_count
        response.save()
        
        return JsonResponse({'success': True, 'helpful_votes': helpful_count})
    
    return JsonResponse({'success': False})


# @login_required
# @require_http_methods(["POST"])
# @csrf_protect
# def resolve_case(request, case_id):
#     """
#     Mark a case as resolved via AJAX
#     """
#     try:
#         # Get the case and ensure it belongs to the current user
#         case = get_object_or_404(CaseConsultation, id=case_id, submitting_doctor=request.user)
        
#         # Check if case is already resolved
#         if case.status == 'RESOLVED':
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Case is already resolved'
#             }, status=400)
        
#         # Update case status
#         case.status = 'RESOLVED'
#         case.resolved_at = time.time()  # Add this field to your model if you want to track when it was resolved
#         case.save()
        
#         return redirect(my_cases)
        
#     except CaseConsultation.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'message': 'Case not found or access denied'
#         }, status=404)
    
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': 'An error occurred while resolving the case'
#         }, status=500)


@require_http_methods(['POST'])
@login_required
def resolve_case(request, case_id):
    case = get_object_or_404(CaseConsultation, id=case_id, submitting_doctor=request.user)

    if case.status != 'OPEN':
        return JsonResponse({'success': False, 'message': 'Case is not open.'}, status=400)

    case.status = 'RESOLVED'
    case.save()
    return JsonResponse({'success': True})


@require_http_methods(['POST'])
@login_required
def reopen_case(request, case_id):
    case = get_object_or_404(CaseConsultation, id=case_id, submitting_doctor=request.user)

    if case.status != 'RESOLVED':
        return JsonResponse({'success': False, 'message': 'Case is not resolved.'}, status=400)

    case.status = 'OPEN'
    case.save()
    return JsonResponse({'success': True})