from celery import shared_task
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from .models import Report
from .pdf_generator import PDFGenerator
from apps.vehicles.tasks import assemble_full_report
from apps.vehicles.services.cache_service import VehicleCacheService
from supabase import create_client

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_report_pdf(self, report_id: str):
    """
    Generate PDF for a Report instance, upload to Supabase Storage, and update report.
    """
    try:
        report = Report.objects.get(id=report_id)
        report.status = 'processing'
        report.save(update_fields=['status'])

        # 1. Get full vehicle data
        vehicle = report.vehicle
        vin = vehicle.vin
        vehicle_data = assemble_full_report(vin)
        if "error" in vehicle_data:
            raise Exception(f"Vehicle data error: {vehicle_data['error']}")

        # 2. Generate PDF bytes
        pdf_bytes = PDFGenerator.generate_report(vehicle_data, str(report.id))

        # 3. Upload to Supabase Storage
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY  # Use service role for upload
        )

        filename = f"reports/{report.id}.pdf"
        # Upload file
        res = supabase.storage.from_('reports').upload(
            filename,
            pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )
        if hasattr(res, 'error') and res.error:
            raise Exception(f"Supabase upload error: {res.error}")

        # 4. Get public URL
        public_url = supabase.storage.from_('reports').get_public_url(filename)

        # 5. Update report
        report.pdf_url = public_url
        report.pdf_filename = filename
        report.status = 'completed'
        report.save(update_fields=['pdf_url', 'pdf_filename', 'status'])

        # 6. Optionally send email to user
        if report.user and report.user.email:
            send_report_email.delay(report.id)

        # 7. Cache the report data with PDF URL
        cached = VehicleCacheService.get_vehicle_report(vin) or {}
        cached['pdf_url'] = public_url
        VehicleCacheService.set_vehicle_report(vin, cached)

        return {"status": "completed", "report_id": str(report.id), "pdf_url": public_url}

    except Exception as e:
        logger.error(f"PDF generation failed for report {report_id}: {str(e)}", exc_info=True)
        try:
            report = Report.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = str(e)
            report.save(update_fields=['status', 'error_message'])
        except Report.DoesNotExist:
            pass
        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {"status": "failed", "report_id": report_id, "error": str(e)}


@shared_task
def send_report_email(report_id: str):
    """Send email to user with PDF link."""
    try:
        report = Report.objects.select_related('user', 'vehicle').get(id=report_id)
        if not report.user or not report.user.email:
            return
        subject = "Your AutoCheck Naija Vehicle Report is Ready"
        context = {
            'user': report.user,
            'vehicle': report.vehicle,
            'pdf_url': report.pdf_url,
            'report_id': report.id,
        }
        html_message = render_to_string('emails/report_ready.html', context)
        plain_message = render_to_string('emails/report_ready.txt', context)
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [report.user.email],
            html_message=html_message,
        )
    except Exception as e:
        logger.error(f"Failed to send email for report {report_id}: {e}")