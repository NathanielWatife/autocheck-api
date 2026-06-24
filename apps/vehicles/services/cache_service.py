import json
from django.core.cache import cache

class VehicleCacheService:
    @staticmethod
    def get_vehicle_report(vin: str) -> dict | None:
        """Retrieve cached full report for a VIN."""
        cache_key = f"vehicle_report:{vin}"
        data = cache.get(cache_key)
        if data:
            return json.loads(data) if isinstance(data, str) else data
        return None

    @staticmethod
    def set_vehicle_report(vin: str, data: dict, ttl_seconds: int = 60*60*24*30):
        """Cache full vehicle report for 30 days."""
        cache_key = f"vehicle_report:{vin}"
        cache.set(cache_key, json.dumps(data), timeout=ttl_seconds)

    @staticmethod
    def invalidate_vehicle(vin: str):
        """Invalidate all caches for a VIN."""
        patterns = [
            f"nhtsa:{vin}",
            f"interpol:{vin}",
            f"copart:{vin}",
            f"customs:{vin}",
            f"vehicle_report:{vin}",
        ]
        for key in patterns:
            cache.delete(key)