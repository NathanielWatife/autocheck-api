from django.contrib import admin
from .models import Vehicle, ImportRecord, DamageReport, MileageLog, OwnershipTrace, VehicleEnrichmentQueue


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vin', 'make', 'model', 'year', 'plate_number', 'is_stolen', 'created_at')
    search_fields = ('vin', 'plate_number', 'make', 'model')
    list_filter = ('make', 'year', 'is_stolen')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('vin', 'plate_number')}),
        ('Vehicle Details', {'fields': ('make', 'model', 'year', 'trim', 'body_type', 'fuel_type', 'transmission')}),
        ('Physical Attributes', {'fields': ('original_color', 'current_color', 'engine_number', 'chassis_number')}),
        ('Security', {'fields': ('is_stolen', 'interpol_stolen_date')}),
        ('Metadata', {'fields': ('last_full_check', 'created_at', 'updated_at')}),
    )


@admin.register(ImportRecord)
class ImportRecordAdmin(admin.ModelAdmin):
    list_display = ('form_m_number', 'vehicle', 'port_of_entry', 'date_of_import', 'cif_value_usd', 'duty_paid_ngn')
    search_fields = ('form_m_number', 'vehicle__vin')
    list_filter = ('port_of_entry', 'date_of_import')


@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'damage_type', 'severity', 'source', 'reported_date', 'verified')
    list_filter = ('damage_type', 'severity', 'source', 'verified')
    search_fields = ('vehicle__vin', 'description')


@admin.register(MileageLog)
class MileageLogAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'mileage', 'recorded_at', 'source')
    list_filter = ('source',)
    search_fields = ('vehicle__vin',)


@admin.register(OwnershipTrace)
class OwnershipTraceAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'owner_name', 'registration_date', 'transfer_date', 'is_current')
    list_filter = ('is_current', 'source')
    search_fields = ('owner_name', 'vehicle__vin')


@admin.register(VehicleEnrichmentQueue)
class VehicleEnrichmentQueueAdmin(admin.ModelAdmin):
    list_display = ('vin', 'status', 'priority', 'retry_count', 'created_at', 'processed_at')
    list_filter = ('status', 'priority')
    search_fields = ('vin',)
    readonly_fields = ('created_at', 'processed_at')