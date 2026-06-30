import uuid
from django.db import models
from django.conf import settings
from apps.vehicles.models import Vehicle

# Create your models here.
class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('progressing', 'Progressing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    report_type = models.CharField(max_length=20, choices=[('free', 'Free'), ('paid', 'Paid')], default='paid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    pdf_url = models.URLField(max_length=1000, null=True, blank=True)
    pdf_filename = models.CharField(max_length=255, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['user']), 
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Report for {self.vehicle.vin} - {self.status}"