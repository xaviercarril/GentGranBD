from __future__ import annotations

import io

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import Socio


FICHA_W, FICHA_H = 150 * mm, 100 * mm
MARGE = 7 * mm
FOTO_W, FOTO_H = 28 * mm, 32 * mm


def _image_from_blob(blob, width, height):
    img = PILImage.open(io.BytesIO(blob))
    px_w = int((width / mm) / 25.4 * 300 * 2)
    px_h = int((height / mm) / 25.4 * 300 * 2)
    img.thumbnail((px_w, px_h), PILImage.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _draw_background(c: canvas.Canvas, logo_path: str | None):
    c.setFillColor(colors.white)
    c.rect(0, 0, FICHA_W, FICHA_H, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#c5d6a1"))
    c.rect(0, FICHA_H - 18 * mm, FICHA_W, 18 * mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGE, FICHA_H - 11.5 * mm, "Fitxa de soci")

    if logo_path:
        try:
            logo_w, logo_h = 31 * mm, 16 * mm
            c.drawImage(
                logo_path,
                FICHA_W - logo_w - MARGE,
                FICHA_H - logo_h - 1.2 * mm,
                width=logo_w,
                height=logo_h,
                mask="auto",
            )
        except Exception:
            pass


def _fmt_date(value):
    return value.strftime("%d/%m/%Y") if value else ""


def _value(value):
    return str(value) if value not in (None, "") else "-"


def _blank_value(value):
    return str(value) if value not in (None, "") else ""


def generar_ficha_socio(
    session,
    socioID: int,
    ruta_pdf: str,
    logo_path: str | None = None,
):
    """Genera una ficha de socio en PDF de 15 x 10 cm."""
    soci = session.get(Socio, socioID)
    if not soci:
        raise ValueError("Soci no trobat")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "TitleFicha",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=12,
        textColor=colors.black,
    ))
    styles.add(ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8,
    ))
    styles.add(ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8,
    ))
    styles.add(ParagraphStyle(
        "Obs",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=8.4,
    ))

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=(FICHA_W, FICHA_H),
        rightMargin=MARGE,
        leftMargin=MARGE,
        topMargin=18 * mm,
        bottomMargin=4 * mm,
    )

    apellidos = f"{soci.apellido1 or ''} {soci.apellido2 or ''}".strip()
    nom_complet = f"{apellidos}, {soci.nombre}".strip(", ")
    foto_flow = Paragraph("Sense foto", styles["Value"])
    if soci.foto:
        foto_flow = Image(_image_from_blob(soci.foto, FOTO_W, FOTO_H), width=FOTO_W, height=FOTO_H)

    rows = [
        ("N. Soci", f"{soci.id:06d}", "DNI/NIE", soci.dniNie),
        ("Data naixement", _fmt_date(soci.fechaNacimiento), "Grup difusio", soci.grupoDifusion),
        ("Adreca", soci.direccion, "Email", soci.email),
        ("Telefon fix", soci.telefonoFijo, "Mobil", soci.telefonoMovil),
        ("Data alta", _fmt_date(soci.fechaAlta), "Data baixa", _fmt_date(soci.fechaBaja)),
    ]
    data_table = Table(
        [
            [
                Paragraph(label1, styles["Label"]),
                Paragraph(_value(value1), styles["Value"]),
                Paragraph(label2, styles["Label"]),
                Paragraph(_value(value2), styles["Value"]),
            ]
            for label1, value1, label2, value2 in rows
        ],
        colWidths=[18 * mm, 25 * mm, 18 * mm, 38 * mm],
        hAlign="LEFT",
    )
    data_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f5eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    right_flow = [
        Paragraph(nom_complet, styles["TitleFicha"]),
        Spacer(1, 1 * mm),
        data_table,
    ]
    header_table = Table(
        [[foto_flow, right_flow]],
        colWidths=[FOTO_W + 5 * mm, FICHA_W - 2 * MARGE - FOTO_W - 5 * mm],
        hAlign="LEFT",
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.4, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    obs_text = _blank_value(soci.observaciones)
    if not obs_text:
        obs_text = "&nbsp;"
    obs_table = Table(
        [[Paragraph("Observacions", styles["Label"])], [Paragraph(obs_text, styles["Obs"])]],
        colWidths=[FICHA_W - 2 * MARGE],
        rowHeights=[6 * mm, 22 * mm],
        hAlign="LEFT",
    )
    obs_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f2f5eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story = [
        header_table,
        Spacer(1, 1 * mm),
        obs_table,
    ]

    doc.build(
        story,
        onFirstPage=lambda c, _: _draw_background(c, logo_path),
        onLaterPages=lambda c, _: _draw_background(c, logo_path),
    )
