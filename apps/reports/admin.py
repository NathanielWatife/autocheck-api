from django.contrib import admin
from .models import Report

# Register your models here.
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'user', 'report_type', 'status', 'created_at', 'pdf_url')
    list_filter = ('status', 'report_type')
    search_fields = ('vehicle__vin', 'user__username')
    readonly_fields = ('created_at', 'updated_at')