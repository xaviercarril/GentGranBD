from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PAGE_SIZE = landscape(A4)
PAGE_MARGIN = 12 * mm
TABLE_COLUMN_WIDTHS = [60 * mm, 52 * mm, 25 * mm, 22 * mm, 20 * mm, 88 * mm]


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ActivitiesTitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
        )
    )
    styles.add(
        ParagraphStyle(
            "ActivitiesSubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "ActivitiesHeader",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            "ActivitiesCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=9.5,
        )
    )
    styles.add(
        ParagraphStyle(
            "ActivitiesCellCenter",
            parent=styles["ActivitiesCell"],
            alignment=TA_CENTER,
        )
    )
    return styles


def _paragraph(value, style):
    return Paragraph(escape(str(value if value is not None else "")), style)


def _build_activities_table(actividades: list[dict], styles):
    headers = ["Activitat", "Professor/a", "Preu", "Inscrits", "Màx.", "Descripció"]
    data = [[_paragraph(header, styles["ActivitiesHeader"]) for header in headers]]
    for actividad in actividades:
        data.append(
            [
                _paragraph(actividad.get("nombre", ""), styles["ActivitiesCell"]),
                _paragraph(actividad.get("personal_nombre", ""), styles["ActivitiesCell"]),
                _paragraph(actividad.get("precio_matricula", ""), styles["ActivitiesCellCenter"]),
                _paragraph(actividad.get("inscritos", ""), styles["ActivitiesCellCenter"]),
                _paragraph(actividad.get("numMaxAlumnos", "") or "", styles["ActivitiesCellCenter"]),
                _paragraph(actividad.get("descripcion", "") or "", styles["ActivitiesCell"]),
            ]
        )

    table = Table(
        data,
        colWidths=TABLE_COLUMN_WIDTHS,
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.9, 0.78)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def generar_pdf_actividades_curso(curso_nombre: str, actividades: list[dict], ruta_pdf: str):
    styles = _build_styles()
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=PAGE_SIZE,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
    )

    logo_path = Path(__file__).resolve().parents[1] / "extra" / "logo.png"
    logo = Image(str(logo_path), width=25 * mm, height=18 * mm) if logo_path.exists() else ""
    header = Table(
        [[logo, Paragraph("ASSOCIACIÓ GENT GRAN CASTELLDEFELS", styles["ActivitiesTitle"]), ""]],
        colWidths=[40 * mm, 187 * mm, 40 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ]
        )
    )

    title = "LLISTAT D'ACTIVITATS"
    subtitle = f"CURS {curso_nombre}" if curso_nombre else "TOTS ELS CURSOS"
    story = [
        header,
        Spacer(1, 3 * mm),
        _paragraph(title, styles["ActivitiesSubtitle"]),
        Spacer(1, 2 * mm),
        _paragraph(subtitle, styles["ActivitiesSubtitle"]),
        Spacer(1, 6 * mm),
    ]

    story.append(_build_activities_table(actividades, styles))
    doc.build(story)
