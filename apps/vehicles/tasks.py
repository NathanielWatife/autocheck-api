from celery import shared_task
from django.db import transaction
import logging
from .models import Vehicle, DamageReport, MileageLog, VehicleEnrichmentQueue
from .services.nhtsa import NHTSAService
from .services.interpol import InterpolService
from .services.copart import CopartScraper
from .services.customs import CustomsService
from .services.cache_service import VehicleCacheService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def enrich_vehicle_data(self, vin: str, force_refresh: bool = False):
    """
    Full vehicle enrichment: NHTSA + INTERPOL + Copart + Customs.
    Saves/updates the Vehicle and related records.
    """
    try:
        # Update queue status
        queue_entry, _ = VehicleEnrichmentQueue.objects.get_or_create(vin=vin)
        queue_entry.status = 'processing'
        queue_entry.save()

        # 1. Get or create Vehicle
        vehicle, created = Vehicle.objects.get_or_create(vin=vin)

        # 2. NHTSA Decode
        nhtsa_data = NHTSAService.decode_vin(vin)
        if "error" not in nhtsa_data:
            vehicle.make = nhtsa_data.get("make") or vehicle.make
            vehicle.model = nhtsa_data.get("model") or vehicle.model
            vehicle.year = nhtsa_data.get("model_year") or vehicle.year
            vehicle.body_type = nhtsa_data.get("body_class") or vehicle.body_type
            vehicle.fuel_type = nhtsa_data.get("fuel_type") or vehicle.fuel_type
            vehicle.transmission = nhtsa_data.get("transmission") or vehicle.transmission
            vehicle.trim = nhtsa_data.get("trim") or vehicle.trim

        # 3. INTERPOL stolen check
        interpol_data = InterpolService.check_vehicle(vin)
        if interpol_data.get("is_stolen"):
            vehicle.is_stolen = True
            vehicle.interpol_stolen_date = interpol_data.get("stolen_date")
            # Also create/update a DamageReport
            DamageReport.objects.update_or_create(
                vehicle=vehicle,
                source='Interpol',
                damage_type='Theft',
                defaults={
                    'severity': 'Major',
                    'reported_date': interpol_data.get("stolen_date") or "2025-01-01",
                    'description': f"Reported stolen via INTERPOL. ID: {interpol_data.get('interpol_id')}",
                    'verified': True,
                }
            )
        else:
            vehicle.is_stolen = False

        # 4. Copart scrape (salvage history)
        copart_data = CopartScraper.check_vin(vin)
        if copart_data.get("found"):
            damage_type = copart_data.get("damage_type", "Collision")
            severity = "Total_Loss" if "TOTAL LOSS" in copart_data.get("title_status", "") else "Salvage"
            DamageReport.objects.update_or_create(
                vehicle=vehicle,
                source='US_Export',
                damage_type=damage_type,
                defaults={
                    'severity': severity,
                    'reported_date': "2025-01-01",  # Copart doesn't give exact date easily
                    'description': f"Copart listing: {copart_data.get('title_status')}",
                    'source_url': copart_data.get("url"),
                    'verified': True,
                }
            )

        # 5. Customs data (mock or DB)
        customs_data = CustomsService.fetch_import_record(vin)
        if customs_data and "note" not in customs_data:
            # Save import record if we have real data
            from .models import ImportRecord
            ImportRecord.objects.update_or_create(
                vehicle=vehicle,
                form_m_number=customs_data.get("form_m_number"),
                defaults={
                    'port_of_entry': customs_data.get("port_of_entry", "PTML"),
                    'date_of_import': customs_data.get("date_of_import"),
                    'cif_value_usd': customs_data.get("cif_value_usd", 0),
                    'duty_paid_ngn': customs_data.get("duty_paid_ngn", 0),
                    'customs_agent_name': customs_data.get("customs_agent_name", ""),
                    'first_owner_name': customs_data.get("first_owner_name", ""),
                }
            )

        # 6. Save vehicle
        vehicle.last_full_check = timezone.now()
        vehicle.save()

        # 7. Cache the full report
        full_report = assemble_full_report(vin)
        VehicleCacheService.set_vehicle_report(vin, full_report)

        # 8. Update queue status
        queue_entry.status = 'completed'
        queue_entry.processed_at = timezone.now()
        queue_entry.save()

        return {"status": "success", "vin": vin}

    except Exception as e:
        logger.error(f"Enrichment failed for VIN {vin}: {str(e)}", exc_info=True)
        # Update queue with error
        try:
            queue_entry = VehicleEnrichmentQueue.objects.get(vin=vin)
            queue_entry.status = 'failed'
            queue_entry.error_message = str(e)
            queue_entry.retry_count += 1
            queue_entry.save()
        except VehicleEnrichmentQueue.DoesNotExist:
            pass

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {"status": "failed", "vin": vin, "error": str(e)}


def assemble_full_report(vin: str) -> dict:
    """Assemble all data for a VIN into a single dict."""
    from .serializers import VehicleSerializer, ImportRecordSerializer, DamageReportSerializer, MileageLogSerializer, OwnershipTraceSerializer

    try:
        vehicle = Vehicle.objects.get(vin=vin)
    except Vehicle.DoesNotExist:
        return {"error": "Vehicle not found"}

    return {
        "vehicle": VehicleSerializer(vehicle).data,
        "import_records": ImportRecordSerializer(vehicle.import_records.all(), many=True).data,
        "damage_reports": DamageReportSerializer(vehicle.damage_reports.all(), many=True).data,
        "mileage_logs": MileageLogSerializer(vehicle.mileage_logs.all(), many=True).data,
        "ownership_traces": OwnershipTraceSerializer(vehicle.ownership_traces.all(), many=True).data,
        "risk_summary": {
            "stolen": vehicle.is_stolen,
            "has_damage": vehicle.damage_reports.exists(),
            "total_damages": vehicle.damage_reports.count(),
            "latest_mileage": vehicle.mileage_logs.first().mileage if vehicle.mileage_logs.exists() else None,
        },
        "stolen_check": {
            "is_stolen": vehicle.is_stolen,
            "interpol_date": vehicle.interpol_stolen_date,
        },
        "scrape_status": "completed",
    }