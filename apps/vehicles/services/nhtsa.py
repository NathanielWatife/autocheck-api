import requests
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class NHTSAService:
    BASE_URL = os.getenv("NHTSA_API_URL")

    @staticmethod
    def _extract_value(results, variable_name):
        for item in results:
            if item.get('Variable') == variable_name:
                return item.get('Value')
        return None

    @classmethod
    def decode_vin(cls, vin: str) -> dict:
        """
        Decode VIN using NHTSA vPIC API.
        Returns dict with make, model, year, etc.
        """
        cache_key = f"nhtsa:{vin}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        url = f"{cls.BASE_URL}/decodevin/{vin}?format=json"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            results = data.get("Results", [])

            result = {
                "make": cls._extract_value(results, "Make"),
                "model": cls._extract_value(results, "Model"),
                "model_year": cls._extract_value(results, "ModelYear"),
                "body_class": cls._extract_value(results, "BodyClass"),
                "engine_cylinders": cls._extract_value(results, "EngineCylinders"),
                "fuel_type": cls._extract_value(results, "FuelTypePrimary"),
                "transmission": cls._extract_value(results, "TransmissionStyle"),
                "plant_city": cls._extract_value(results, "PlantCity"),
                "plant_country": cls._extract_value(results, "PlantCountry"),
                "trim": cls._extract_value(results, "Trim"),
                "vehicle_type": cls._extract_value(results, "VehicleType"),
            }
            # Cache for 90 days
            cache.set(cache_key, result, timeout=60*60*24*90)
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"NHTSA API error for VIN {vin}: {e}")
            return {"error": str(e)}