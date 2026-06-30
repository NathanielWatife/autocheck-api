from rest_framework import serializers
from .models import Report
from apps.vehicles.serializers import VehicleSerializer

class ReportSerializer(serializers.ModelSerializer):
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    
    class Meta:
        model = Report
        fields = (
            'id', 'vehicle', 'vehicle_details', 'user', 'report_type', 'status',
            'pdf_url', 'pdf_filename', 'expires_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'status', 'pdf_url', 'pdf_filename')


class ReportRequestSerializer(serializers.Serializer):
    vin = serializers.CharField(max_length=17, required=True)
    report_type = serializers.ChoiceField(choices=[('free', 'Free'), ('paid', 'Paid')], default='paid')