from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from exportador.pdf_carnet import CARD_H, CARD_W, dibujar_carnet_socio
from exportador.pdf_ficha_socio import FICHA_H, FICHA_W, dibujar_ficha_socio
from models import Socio


PAGE_W, PAGE_H = A4
CUT_MARK = 6 * mm
CUT_GAP = 1.5 * mm


def _draw_cut_guides(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    sides: tuple[str, ...],
):
    c.saveState()
    c.setStrokeColor(colors.HexColor("#777777"))
    c.setLineWidth(0.35)
    c.setDash(2, 2)
    if "left" in sides:
        c.line(x, y, x, y + height)
    if "right" in sides:
        c.line(x + width, y, x + width, y + height)
    if "bottom" in sides:
        c.line(x, y, x + width, y)
    if "top" in sides:
        c.line(x, y + height, x + width, y + height)

    c.setDash()
    c.setLineWidth(0.45)
    marks = []
    if "bottom" in sides:
        marks.extend([
            (max(0, x - CUT_MARK), y, max(0, x - CUT_GAP), y),
            (min(PAGE_W, x + width + CUT_GAP), y, min(PAGE_W, x + width + CUT_MARK), y),
        ])
    if "top" in sides:
        marks.extend([
            (max(0, x - CUT_MARK), y + height, max(0, x - CUT_GAP), y + height),
            (min(PAGE_W, x + width + CUT_GAP), y + height, min(PAGE_W, x + width + CUT_MARK), y + height),
        ])
    if "left" in sides:
        marks.extend([
            (x, max(0, y - CUT_MARK), x, max(0, y - CUT_GAP)),
            (x, min(PAGE_H, y + height + CUT_GAP), x, min(PAGE_H, y + height + CUT_MARK)),
        ])
    if "right" in sides:
        marks.extend([
            (x + width, max(0, y - CUT_MARK), x + width, max(0, y - CUT_GAP)),
            (x + width, min(PAGE_H, y + height + CUT_GAP), x + width, min(PAGE_H, y + height + CUT_MARK)),
        ])
    for x1, y1, x2, y2 in marks:
        if x1 != x2 or y1 != y2:
            c.line(x1, y1, x2, y2)
    c.restoreState()


def generar_hoja_ficha_carnet_socio(
    session,
    socioID: int,
    ruta_pdf: str,
    logo_path: str | None = None,
):
    """Genera una hoja A4 imprimible con la ficha y el carnet del socio."""
    soci = session.get(Socio, socioID)
    if not soci:
        raise ValueError("Soci no trobat")

    c = canvas.Canvas(ruta_pdf, pagesize=A4)
    c.setTitle(f"Fitxa i carnet soci {soci.id:06d}")

    ficha_x = 0
    ficha_y = PAGE_H - FICHA_H
    carnet_x = PAGE_W - CARD_W
    carnet_y = 0

    dibujar_ficha_socio(c, soci, ficha_x, ficha_y, logo_path=logo_path)
    dibujar_carnet_socio(c, soci, carnet_x, carnet_y, logo_path=logo_path)

    _draw_cut_guides(c, ficha_x, ficha_y, FICHA_W, FICHA_H, ("right", "bottom"))
    _draw_cut_guides(c, carnet_x, carnet_y, CARD_W, CARD_H, ("left", "top"))

    c.showPage()
    c.save()
