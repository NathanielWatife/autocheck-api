import io
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class PDFGenerator:
    @classmethod
    def generate_report(cls, vehicle_data: dict, report_id: str) -> bytes:
        """
        Generate a PDF report for a vehicle.
        vehicle_data: dict containing all vehicle info (from assemble_full_report)
        returns: bytes of PDF
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1A3B5C'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1A3B5C'),
            spaceAfter=12,
            spaceBefore=18,
        )
        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=8,
        )
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
        )
        risk_style = ParagraphStyle(
            'RiskStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            alignment=TA_CENTER,
            backColor=colors.HexColor('#2ECC71'),  # will be overridden
            spaceAfter=12,
        )

        # Build story
        story = []

        # === Title ===
        story.append(Paragraph("AutoCheck Naija – Vehicle History Report", title_style))
        story.append(Spacer(1, 0.2*inch))

        # === Report Metadata ===
        meta_data = [
            ["Report ID:", report_id],
            ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]
        meta_table = Table(meta_data, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.3*inch))

        # === Overall Risk Section ===
        risk_data = cls._get_risk_summary(vehicle_data)
        risk_color = risk_data['color']
        risk_text = f"<font color='white'><b>{risk_data['label']}</b></font>"
        risk_para = Paragraph(risk_text, ParagraphStyle(
            'RiskBox',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.white,
            alignment=TA_CENTER,
            backColor=colors.HexColor(risk_color),
            spaceAfter=12,
            borderPadding=8,
        ))
        story.append(risk_para)
        story.append(Spacer(1, 0.1*inch))

        # === Vehicle Basic Info ===
        vehicle = vehicle_data.get('vehicle', {})
        story.append(Paragraph("Vehicle Identification", heading2_style))
        info_table_data = [
            ["VIN", vehicle.get('vin', 'N/A')],
            ["Make", vehicle.get('make', 'N/A')],
            ["Model", vehicle.get('model', 'N/A')],
            ["Year", vehicle.get('year', 'N/A')],
            ["Body Type", vehicle.get('body_type', 'N/A')],
            ["Fuel Type", vehicle.get('fuel_type', 'N/A')],
            ["Transmission", vehicle.get('transmission', 'N/A')],
            ["Original Color", vehicle.get('original_color', 'N/A')],
            ["Current Color", vehicle.get('current_color', 'N/A')],
        ]
        info_table = Table(info_table_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))

        # === Import History ===
        import_records = vehicle_data.get('import_records', [])
        if import_records:
            story.append(Paragraph("Import History", heading2_style))
            import_data = [["Field", "Value"]]
            for rec in import_records:
                import_data.append(["Form M", rec.get('form_m_number', 'N/A')])
                import_data.append(["Port of Entry", rec.get('port_of_entry', 'N/A')])
                import_data.append(["Date of Import", rec.get('date_of_import', 'N/A')])
                import_data.append(["CIF Value (USD)", f"${rec.get('cif_value_usd', 0):,.2f}"])
                import_data.append(["Duty Paid (₦)", f"₦{rec.get('duty_paid_ngn', 0):,.2f}"])
                import_data.append(["First Owner", rec.get('first_owner_name', 'N/A')])
            import_table = Table(import_data, colWidths=[2*inch, 4*inch])
            import_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A3B5C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(import_table)
            story.append(Spacer(1, 0.3*inch))

        # === Damage Reports ===
        damages = vehicle_data.get('damage_reports', [])
        if damages:
            story.append(Paragraph("Damage & Accident History", heading2_style))
            damage_data = [["Date", "Type", "Severity", "Source"]]
            for dmg in damages:
                damage_data.append([
                    dmg.get('reported_date', 'N/A'),
                    dmg.get('damage_type', 'N/A'),
                    dmg.get('severity', 'N/A'),
                    dmg.get('source', 'N/A'),
                ])
            damage_table = Table(damage_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
            damage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(damage_table)
            story.append(Spacer(1, 0.3*inch))

        # === Mileage Logs ===
        mileage_logs = vehicle_data.get('mileage_logs', [])
        if mileage_logs:
            story.append(Paragraph("Mileage History", heading2_style))
            mileage_data = [["Date", "Mileage (km)", "Source"]]
            for log in mileage_logs:
                mileage_data.append([
                    log.get('recorded_at', 'N/A'),
                    f"{log.get('mileage', 0):,}",
                    log.get('source', 'N/A'),
                ])
            mileage_table = Table(mileage_data, colWidths=[2*inch, 2*inch, 3*inch])
            mileage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(mileage_table)
            story.append(Spacer(1, 0.3*inch))

        # === Ownership Chain ===
        ownership = vehicle_data.get('ownership_traces', [])
        if ownership:
            story.append(Paragraph("Ownership Chain", heading2_style))
            owner_data = [["Owner", "Registered", "Transferred", "Current"]]
            for own in ownership:
                owner_data.append([
                    own.get('owner_name', 'N/A'),
                    own.get('registration_date', 'N/A'),
                    own.get('transfer_date', 'N/A') or 'Still owns',
                    "✓" if own.get('is_current') else "",
                ])
            owner_table = Table(owner_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
            owner_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A3B5C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(owner_table)
            story.append(Spacer(1, 0.3*inch))

        # === Stolen Check ===
        stolen_info = vehicle_data.get('stolen_check', {})
        if stolen_info:
            story.append(Paragraph("Stolen Vehicle Check", heading2_style))
            stolen_text = "✅ CLEAN" if not stolen_info.get('is_stolen') else "⚠️ STOLEN"
            stolen_color = colors.green if not stolen_info.get('is_stolen') else colors.red
            stolen_para = Paragraph(f"<font color='{stolen_color}'><b>{stolen_text}</b></font>", normal_style)
            story.append(stolen_para)
            if stolen_info.get('is_stolen'):
                story.append(Paragraph(f"Date of theft: {stolen_info.get('interpol_date', 'Unknown')}", normal_style))
            story.append(Spacer(1, 0.2*inch))

        # === Footer ===
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        footer_text = f"AutoCheck Naija – Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Confidential"
        story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _get_risk_summary(data: dict) -> dict:
        """Return risk label and color based on data."""
        vehicle = data.get('vehicle', {})
        stolen = data.get('stolen_check', {}).get('is_stolen', False)
        damages = data.get('damage_reports', [])
        has_damage = len(damages) > 0

        if stolen:
            return {'label': '⚠️ CRITICAL – VEHICLE REPORTED STOLEN', 'color': '#E74C3C'}
        elif has_damage:
            # Check if any severe damage
            severe = any(d.get('severity') in ['Major', 'Salvage', 'Total_Loss'] for d in damages)
            if severe:
                return {'label': '⚠️ HIGH RISK – Major Damage History', 'color': '#E67E22'}
            else:
                return {'label': 'ℹ️ MODERATE RISK – Minor Damage Reported', 'color': '#F1C40F'}
        else:
            return {'label': '✅ LOW RISK – No Red Flags Found', 'color': '#2ECC71'}