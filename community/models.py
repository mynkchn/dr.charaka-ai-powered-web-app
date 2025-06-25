# community/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class CaseConsultation(models.Model):
    URGENCY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    SPECIALIZATION_CHOICES = [
        ('Cardiology', 'Cardiology'),
        ('Neurology', 'Neurology'),
        ('Pediatrics', 'Pediatrics'),
        ('General Medicine', 'General Medicine'),
        ('Surgery', 'Surgery'),
        ('Orthopedics', 'Orthopedics'),
        ('Dermatology', 'Dermatology'),
    ]
    
    # Case details
    title = models.CharField(max_length=200)
    description = models.TextField()
    patient_age = models.IntegerField()
    patient_gender = models.CharField(max_length=10,choices=GENDER_CHOICES)
    symptoms = models.TextField()
    medical_history = models.TextField(blank=True, null=True)
    current_medications = models.TextField(blank=True, null=True)
    
    # Case management
    submitting_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_cases')
    required_specialization = models.CharField(max_length=100, blank=True, null=True,choices=SPECIALIZATION_CHOICES)
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Case: {self.title} ({self.get_urgency_display()})"
    def mark_resolved(self):
        """Helper method to mark case as resolved"""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.save()
    
    def reopen(self):
        """Helper method to reopen a resolved case"""
        self.status = 'OPEN'
        self.resolved_at = None
        self.save()

class CaseResponse(models.Model):
    case = models.ForeignKey(CaseConsultation, on_delete=models.CASCADE, related_name='responses')
    responding_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='case_responses')
    response_text = models.TextField()
    is_helpful = models.BooleanField(default=False)  # Marked by case submitter
    helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-helpful_votes', '-created_at']
    
    def __str__(self):
        return f"Response to {self.case.title} by Dr. {self.responding_doctor.last_name}"

class CaseVote(models.Model):
    response = models.ForeignKey(CaseResponse, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['response', 'voter']