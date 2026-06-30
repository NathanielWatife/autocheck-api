from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from .models import *
from .serializers import *
from .services.validators import is_valid_vin
from .services.nhtsa import NHTSAService
from .services.interpol import InterpolService
from .services.cache_service import VehicleCacheService
from .tasks import enrich_vehicle_data

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def lookup_vin(request, vin):
    """
    Free VIN lookup – returns basic info + risk flags.
    If cached, returns immediately. Otherwise, triggers background enrichment.
    """
    vin = vin.upper().strip()

    # 1. Validate VIN format
    if not is_valid_vin(vin):
        return Response({"error": "Invalid VIN format. Must be 17 alphanumeric characters."},
                        status=status.HTTP_400_BAD_REQUEST)

    # 2. Check cache
    cached_report = VehicleCacheService.get_vehicle_report(vin)
    if cached_report:
        return Response(cached_report)

    # 3. Check if vehicle exists in DB
    try:
        vehicle = Vehicle.objects.get(vin=vin)
        # Check if we have a recent full check (within 7 days)
        if vehicle.last_full_check and (timezone.now() - vehicle.last_full_check).days < 7:
            # Assemble report from DB
            from .tasks import assemble_full_report
            report = assemble_full_report(vin)
            VehicleCacheService.set_vehicle_report(vin, report)
            return Response(report)
    except Vehicle.DoesNotExist:
        vehicle = None

    # 4. Not in cache/DB – trigger background enrichment and return basic NHTSA data
    # Add to queue
    queue_entry, created = VehicleEnrichmentQueue.objects.get_or_create(
        vin=vin,
        defaults={'status': 'pending', 'priority': 0}
    )
    if queue_entry.status in ['pending', 'failed']:
        # Trigger Celery task
        enrich_vehicle_data.delay(vin)

    # 5. Return basic NHTSA data (fast, no DB save yet)
    nhtsa_data = NHTSAService.decode_vin(vin)
    interpol_data = InterpolService.check_vehicle(vin)

    # Save basic vehicle record if we have minimal data
    if not vehicle and nhtsa_data.get("make"):
        vehicle = Vehicle.objects.create(
            vin=vin,
            make=nhtsa_data.get("make"),
            model=nhtsa_data.get("model"),
            year=nhtsa_data.get("model_year"),
            body_type=nhtsa_data.get("body_class"),
            fuel_type=nhtsa_data.get("fuel_type"),
            transmission=nhtsa_data.get("transmission"),
            is_stolen=interpol_data.get("is_stolen", False),
        )

    response_data = {
        "vin": vin,
        "status": "processing",
        "estimated_time_seconds": 45,
        "basic_info": {
            "make": nhtsa_data.get("make"),
            "model": nhtsa_data.get("model"),
            "year": nhtsa_data.get("model_year"),
            "body_type": nhtsa_data.get("body_class"),
        },
        "stolen_check": interpol_data,
        "message": "Full report is being generated. Check back in 60 seconds or use the /full/ endpoint."
    }

    # Cache processing status for 5 minutes (to avoid repeated triggers)
    VehicleCacheService.set_vehicle_report(vin, response_data, ttl_seconds=300)

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def full_vehicle_report(request, vin):
    """
    Get full vehicle report (requires authentication).
    Waits for enrichment to complete or returns cached.
    """
    vin = vin.upper().strip()

    if not is_valid_vin(vin):
        return Response({"error": "Invalid VIN format."}, status=status.HTTP_400_BAD_REQUEST)

    # Check cache first
    cached = VehicleCacheService.get_vehicle_report(vin)
    if cached and "status" in cached and cached["status"] == "completed":
        return Response(cached)

    # Check if vehicle exists and is fully enriched
    try:
        vehicle = Vehicle.objects.get(vin=vin)
        if vehicle.last_full_check:
            from .tasks import assemble_full_report
            report = assemble_full_report(vin)
            VehicleCacheService.set_vehicle_report(vin, report)
            return Response(report)
    except Vehicle.DoesNotExist:
        pass

    # If not ready, trigger enrichment if not already queued
    queue_entry, created = VehicleEnrichmentQueue.objects.get_or_create(
        vin=vin,
        defaults={'status': 'pending', 'priority': 1}  # higher priority for paid users
    )
    if queue_entry.status in ['pending', 'failed']:
        enrich_vehicle_data.delay(vin)

    return Response({
        "vin": vin,
        "status": "pending",
        "message": "Report is being generated. Please wait 60 seconds.",
        "poll_url": f"/api/v1/vehicles/lookup/{vin}/"
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([AllowAny])
def plate_to_vin(request, plate):
    """
    Convert Nigerian plate number to VIN (mock for MVP).
    In production, integrate with FRSC NVIS API.
    """
    # Mock: return a fake VIN for demo purposes
    # In reality, you would query FRSC NVIS or a local mapping
    mock_vin = "1HGCM82633A123456"  # Example
    return Response({
        "plate_number": plate,
        "vin": mock_vin,
        "note": "Plate-to-VIN mapping requires FRSC integration. This is a mock response."
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_vehicles(request):
    """
    Search vehicles by make/model/year (authenticated).
    Query params: ?make=Toyota&model=Camry&year=2020
    """
    queryset = Vehicle.objects.all()
    make = request.query_params.get('make')
    model = request.query_params.get('model')
    year = request.query_params.get('year')

    if make:
        queryset = queryset.filter(make__icontains=make)
    if model:
        queryset = queryset.filter(model__icontains=model)
    if year:
        queryset = queryset.filter(year=year)

    serializer = VehicleSerializer(queryset[:50], many=True)  # Limit results
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_enrich(request, vin):
    """
    Admin/staff endpoint to manually trigger full enrichment.
    """
    vin = vin.upper().strip()
    if not is_valid_vin(vin):
        return Response({"error": "Invalid VIN"}, status=status.HTTP_400_BAD_REQUEST)

    # Invalidate cache
    VehicleCacheService.invalidate_vehicle(vin)

    # Trigger task
    enrich_vehicle_data.delay(vin)
    return Response({"message": f"Enrichment triggered for {vin}"})