import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vin = models.CharField(max_length=17, unique=True, validators=[MinValueValidator(17), MaxValueValidator(17)])
    plate_number = models.CharField(max_length=10, unique=True, null=True, blank=True)
    make = models.CharField(max_length=50, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1886), MaxValueValidator(2100)])
    trim = models.CharField(max_length=50, null=True, blank=True)
    engine_number = models.CharField(max_length=50, null=False, blank=False)
    chasis_number = models.CharField(max_length=50, null=False, blank=False)
    original_color = models.CharField(max_length=30, null=True, blank=True)
    current_color = models.CharField(max_length=30, null=True, blank=True)
    body_type = models.CharField(max_length=50, null=True, blank=True)
    fuel_type = models.CharField(max_length=50, null=True, blank=True)
    transmission = models.CharField(max_length=50, null=True, blank=True)
    is_stolen = models.BooleanField(default=False)
    interpol_stolen_date = models.DateField(null=True, blank=True)
    last_full_check = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['plate_number']),
            models.Index(fields=['make', 'model', 'year']),
        ]
    def __str__(self):
        return f"({self.year}) {self.make} {self.model} - {self.vin}"


class ImportRecord(models.Model):
    PORT_CHOICES = [
        ('PTML', 'Port of Lagos'),
        ('Apapa', 'Apapa Port Lagos'),
        ('Tin Can', 'Tin Can Island Port Lagos'),
        ('Onne', 'Onne Port Rivers State'),
        ('Calabar', 'Calabar Port Cross River State'),
        ('Warri', 'Warri Port Delta State'),
        ('Port Harcourt', 'Port Harcourt Port Rivers State'),
        ('Kano', 'Kano Port Kano State'),
        ('Kaduna', 'Kaduna Port Kaduna State'),
        ('Abuja', 'Abuja Port FCT'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='import_records')
    form_m_number = models.CharField(max_length=50, unique=True)
    port_of_entry = models.CharField(max_length=100, choices=PORT_CHOICES)
    date_of_import = models.DateField()
    cif_value_usd = models.DecimalField(max_digits=10, decimal_places=2)
    duty_paid_ngn = models.DecimalField(max_digits=15, decimal_places=2)
    custom_agent_name = models.CharField(max_length=100)
    custom_agent_contact = models.CharField(max_length=15)
    first_owner_name = models.CharField(max_length=100)

    class Meta:
        indexes = [
            models.Index(fields=['form_m_number']),
            models.Index(fields=['vehicle']),
        ]

    def __str__(self):
        return f"Import Record for {self.form_m_number} - {self.vehicle.vin[:8]}"

class DamageReport(models.Model):
    DAMAGE_TYPES = [
        ('Flood', 'Flood Damage'),
        ('Fire', 'Fire Damage'),
        ('Collision', 'Collision'),
        ('Theft', 'Theft Recovery'),
        ('Structural', 'Structural Damage'),
        ('Hail', 'Hail Damage'),
    ]

    SEVERITY_LEVELS = [
        ('Minor', 'Minor'),
        ('Major', 'Major'),
        ('Salvage', 'Salvage'),
        ('Total_Loss', 'Total Loss'),
    ]

    SOURCES = [
        ('US_Export', 'US Export (Copart/IAAI)'),
        ('Local_Insurance', 'Local Insurance Claim'),
        ('FRSC', 'FRSC Inspection Report'),
        ('User_Report', 'User Reported'),
        ('Interpol', 'Interpol Stolen Vehicle Report'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='damage_reports')
    damage_type = models.CharField(max_length=20, choices=DAMAGE_TYPES)
    source = models.CharField(max_length=20, choices=SOURCES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    description = models.TextField(blank=True)
    reported_date = models.DateField()
    source_url = models.URLField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle']),
        ]

    def __str__(self):
        return f"{self.damage_type} ({self.severity}) - {self.vehicle.vin[:8]}"



class MileageLog(models.Model):
    SOURCES = [
        ('Customs_Entry', 'Customs Declaration'),
        ('MOT_Center', 'MOT Inspection'),
        ('Insurance_Claim', 'Insurance Claim'),
        ('User_Input', 'User Uploaded'),
        ('Service_Record', 'Service Record'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='mileage_logs')
    recorded_at = models.DateTimeField()
    mileage = models.IntegerField(help_text="Mileage in kilometers")
    source = models.CharField(max_length=20, choices=SOURCES)
    source_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vehicle']),
            models.Index(fields=['recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.mileage} km on {self.recorded_at} - {self.vehicle.vin[:8]}"


class OwnershipTrace(models.Model):
    SOURCES = [
        ('FRSC', 'FRSC Records'),
        ('User_Upload', 'User Uploaded'),
        ('Dealer_Input', 'Dealer Input'),
        ('Customs', 'Customs Declaration'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='ownership_traces')
    owner_name = models.CharField(max_length=100)
    owner_phone = models.CharField(max_length=15, blank=True)
    registration_date = models.DateField()
    transfer_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    source = models.CharField(max_length=50, choices=SOURCES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vehicle']),
        ]
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.owner_name} - {self.vehicle.vin[:8]}"



class VehicleEnrichmentQueue(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vin = models.CharField(max_length=17, unique=True)
    priority = models.IntegerField(default=0, help_text="Lower number means higher priority")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    retry_count =  models.IntegerField(default=0, help_text="Number of times this VIN has been retried for enrichment")
    error_message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    

    class Meta:
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['status']),
        ]
        ordering = ['-requested_at']

    def __str__(self):
        return f"Enrichment Queue for {self.vin} - {self.status}"