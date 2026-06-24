import requests
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class InterpolService:
    BASE_URL = os.getenv("INTERPOL_API_URL")
    @classmethod
    def check_vehicle(cls, vin: str) -> dict:
        """
        Check if VIN is reported stolen via INTERPOL public API.
        Returns: { is_stolen: bool, stolen_date: str, interpol_id: str }
        """
        cache_key = f"interpol:{vin}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        url = f"{cls.BASE_URL}/stolen-vehicles"
        params = {"vin": vin}
        try:
            response = requests.get(url, params=params, timeout=20)
            if response.status_code == 404:
                # No records found
                result = {"is_stolen": False}
            elif response.status_code == 200:
                data = response.json()
                items = data.get("data", [])
                if items:
                    first = items[0]
                    result = {
                        "is_stolen": True,
                        "stolen_date": first.get("dateOfTheft"),
                        "interpol_id": first.get("id"),
                        "description": first.get("description"),
                        "country": first.get("country"),
                    }
                else:
                    result = {"is_stolen": False}
            else:
                result = {"is_stolen": False, "error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"INTERPOL API error for VIN {vin}: {e}")
            result = {"is_stolen": False, "error": str(e)}

        # Cache for 7 days (INTERPOL data changes slowly)
        cache.set(cache_key, result, timeout=60*60*24*7)
        return result