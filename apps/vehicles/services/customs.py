import logging
from django.core.cache import cache
from ..models import ImportRecord

logger = logging.getLogger(__name__)

class CustomsService:
    """
    Nigeria Customs integration.
    For MVP: checks local database or returns mock data.
    Production: integrate with Nigeria Trade Hub API (requires MOU).
    """

    @classmethod
    def fetch_import_record(cls, vin: str, form_m_number: str = None) -> dict:
        """
        Fetch import record for a vehicle.
        If form_m_number provided, try to find in DB.
        Otherwise, return mock for demonstration.
        """
        cache_key = f"customs:{vin}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 1. Try database first
        try:
            vehicle = Vehicle.objects.get(vin=vin)
            import_rec = ImportRecord.objects.filter(vehicle=vehicle).first()
            if import_rec:
                result = {
                    "form_m_number": import_rec.form_m_number,
                    "port_of_entry": import_rec.port_of_entry,
                    "date_of_import": import_rec.date_of_import.isoformat(),
                    "cif_value_usd": float(import_rec.cif_value_usd),
                    "duty_paid_ngn": float(import_rec.duty_paid_ngn),
                    "customs_agent_name": import_rec.customs_agent_name,
                    "first_owner_name": import_rec.first_owner_name,
                }
                cache.set(cache_key, result, timeout=60*60*24*30)
                return result
        except Vehicle.DoesNotExist:
            pass

        # 2. Mock data for MVP (in production, call Nigeria Trade Hub API)
        # Placeholder - in real scenario, you would call:
        # response = requests.get(f"https://api.trade.gov.ng/v1/customs/declaration?form_m={form_m_number}")
        result = {
            "form_m_number": form_m_number or "MF-2025-XXXXXX",
            "port_of_entry": "PTML Lagos",
            "date_of_import": "2025-01-15",
            "cif_value_usd": 8500.00,
            "duty_paid_ngn": 1850000.00,
            "customs_agent_name": "Bashir Clearing Agency",
            "first_owner_name": "Bashir Motors LTD",
            "note": "Mock data - integrate with Nigeria Trade Hub API for production"
        }
        cache.set(cache_key, result, timeout=60*60*24*7)
        return result