from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "SociosTitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
        )
    )
    styles.add(
        ParagraphStyle(
            "SociosSubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "SociosCell",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Helvetica",
            fontSize=6.5,
            leading=7.5,
            splitLongWords=True,
        )
    )
    styles.add(
        ParagraphStyle(
            "SociosHeaderCell",
            parent=styles["SociosCell"],
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
    )
    return styles


def _fmt_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _truncate(text: str, max_chars: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _cell(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def generar_pdf_socios_tabla(
    socios: list[dict],
    ruta_pdf: str,
    *,
    titulo: str = "LLISTAT DE SOCIS",
) -> None:
    styles = _build_styles()
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    logo_path = Path(__file__).resolve().parents[1] / "extra" / "logo.png"
    logo = Image(str(logo_path), width=25 * mm, height=18 * mm) if logo_path.exists() else ""
    header = Table(
        [[logo, _cell("ASSOCIACIÓ GENT GRAN CASTELLDEFELS", styles["SociosTitle"]), ""]],
        colWidths=[35 * mm, 211 * mm, 35 * mm],
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

    story = [
        header,
        Spacer(1, 3 * mm),
        _cell(titulo, styles["SociosSubtitle"]),
        Spacer(1, 1.5 * mm),
        _cell(f"TOTAL: {len(socios)}", styles["SociosSubtitle"]),
        Spacer(1, 5 * mm),
    ]

    columns = [
        ("Num Soci", "id", 13 * mm, 8),
        ("Primer Cognom", "apellido1", 25 * mm, 22),
        ("Segon Cognom", "apellido2", 25 * mm, 22),
        ("Nom", "nombre", 24 * mm, 22),
        ("DNI", "dniNie", 21 * mm, 14),
        ("Telf. Movil", "telefonoMovil", 20 * mm, 14),
        ("Telf. Fixe", "telefonoFijo", 20 * mm, 14),
        ("Adreça", "direccion", 40 * mm, 36),
        ("Data alta", "fechaAlta", 18 * mm, 10),
        ("Data naix.", "fechaNacimiento", 21 * mm, 10),
        ("Grup dif.", "grupoDifusion", 21 * mm, 18),
        ("Email", "email", 33 * mm, 30),
    ]

    data = [[_cell(label, styles["SociosHeaderCell"]) for label, _key, _width, _max_chars in columns]]
    for socio in socios:
        data.append(
            [
                _cell(_truncate(_fmt_value(socio.get(key)), max_chars), styles["SociosCell"])
                for _label, key, _width, max_chars in columns
            ]
        )

    table = Table(
        data,
        colWidths=[width for _label, _key, width, _max_chars in columns],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.9, 0.78)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(table)
    doc.build(story)
