from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
    return styles


def generar_pdf_actividades_curso(curso_nombre: str, actividades: list[dict], ruta_pdf: str):
    styles = _build_styles()
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    logo_path = Path(__file__).resolve().parents[1] / "extra" / "logo.png"
    logo = Image(str(logo_path), width=25 * mm, height=18 * mm) if logo_path.exists() else ""
    header = Table(
        [[logo, Paragraph("ASSOCIACIÓ GENT GRAN CASTELLDEFELS", styles["ActivitiesTitle"]), ""]],
        colWidths=[35 * mm, 115 * mm, 35 * mm],
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
        Paragraph(title, styles["ActivitiesSubtitle"]),
        Spacer(1, 2 * mm),
        Paragraph(subtitle, styles["ActivitiesSubtitle"]),
        Spacer(1, 6 * mm),
    ]

    data = [["Activitat", "Professor/a", "Preu", "Inscrits", "Màx.", "Descripció"]]
    for actividad in actividades:
        data.append([
            actividad.get("nombre", ""),
            actividad.get("personal_nombre", ""),
            actividad.get("precio_matricula", ""),
            str(actividad.get("inscritos", "")),
            str(actividad.get("numMaxAlumnos", "") or ""),
            actividad.get("descripcion", "") or "",
        ])

    table = Table(
        data,
        colWidths=[43 * mm, 38 * mm, 20 * mm, 18 * mm, 15 * mm, 51 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.9, 0.78)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (2, 1), (4, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    doc.build(story)
