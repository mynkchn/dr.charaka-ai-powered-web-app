# drug_checker/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

class DrugInteractionCheck(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MODERATE', 'Moderate Risk'),
        ('HIGH', 'High Risk'),
        ('SEVERE', 'Severe Risk'),
    ]
    
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='drug_checks')
    patient_name = models.CharField(max_length=200, blank=True)
    drugs_checked = models.JSONField()  # Store list of drugs checked
    interaction_found = models.BooleanField(default=False)
    severity_level = models.CharField(max_length=10, choices=SEVERITY_CHOICES, blank=True)
    interaction_details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Drug Check - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
