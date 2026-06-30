from rest_framework import serializers
from .models import *

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class ImportRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRecord
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class DamageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DamageReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class MileageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MileageLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class OwnershipTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnershipTrace
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class VehicleEnrichmentQueueSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    import_records = ImportRecordSerializer(many=True, read_only=True)
    damage_reports = DamageReportSerializer(many=True, read_only=True)
    mileage_logs = MileageLogSerializer(many=True, read_only=True)
    ownership_traces = OwnershipTraceSerializer(many=True, read_only=True)
    risk_summary = serializers.DictField()
    stolen_check = serializers.DictField()
    scrape_status = serializers.DictField()