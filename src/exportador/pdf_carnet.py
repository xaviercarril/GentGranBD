from reportlab.platypus import (
    SimpleDocTemplate, Image, Paragraph, Spacer,
    Table, TableStyle
)
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
import io
from models import Socio

# ──────────────────────────────────────────────────────
#   CONSTANTS
# ──────────────────────────────────────────────────────
CARD_W, CARD_H = 80 * mm, 50 * mm          # targeta 8 × 5 cm
FOTO_W, FOTO_H = 20 * mm, 24 * mm          # miniatura foto
MARGE       = 5 * mm                       # marges laterals/verticals


# ──────────────────────────────────────────────────────
#   HELPERS
# ──────────────────────────────────────────────────────
def _resize_photo(blob):
    img = PILImage.open(io.BytesIO(blob))
    # càlcul de píxels corresponents a 40×48 mm a 300 dpi
    px_w = int((FOTO_W / mm) / 25.4 * 300 * 2)    # ×2
    px_h = int((FOTO_H / mm) / 25.4 * 300 * 2)
    img = img.resize((px_w, px_h), PILImage.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _fons(c: canvas.Canvas, logo_path: str | None):
    """Dibuixa fons verd pastel (#c5d6a1), franja gris i logo top-right."""
    # Fons principal
    c.setFillColor(colors.HexColor("#c5d6a1"))        # verd pastel
    c.rect(0, 0, CARD_W, CARD_H, fill=1, stroke=0)

    # Franja inferior gris
    c.setFillColor(colors.lightgrey)
    c.rect(0, 0, CARD_W, 8 * mm, fill=1, stroke=0)
    c.setFont("Helvetica", 6)
    c.setFillColor(colors.black)
    c.drawCentredString(
        CARD_W / 2,
        2.5 * mm,
        "Associació Gent Gran · www.gentgrancastelldefels.com · Telf: 644 042 557"
    )

    # Logo opcional a dalt dreta
    if logo_path:
        try:
            logo_w, logo_h = 18 * mm, 10 * mm
            x_logo = CARD_W - logo_w - 2 * mm        # 2 mm marge dret
            y_logo = CARD_H - logo_h - 2 * mm        # 2 mm marge top
            c.drawImage(
                logo_path, x_logo, y_logo,
                width=logo_w, height=logo_h, mask="auto"
            )
        except Exception:
            pass  # si hi ha error en el logo, el carnet igualment es genera


# ──────────────────────────────────────────────────────
#   FUNCIÓ PRINCIPAL
# ──────────────────────────────────────────────────────
def generar_carnet_socio(
    session,
    socioID: int,
    ruta_pdf: str,
    logo_path: str | None = None
):
    """
    Genera un carnet (8×5 cm) d'un soci:
      • fons verd pastel (#c5d6a1)
      • foto i text en taula horitzontal
      • logo a la cantonada superior dreta
      • franja inferior amb text de contacte
    Sempre cap en **una sola pàgina**.
    """
    soci = session.get(Socio, socioID)     # API moderna SQLAlchemy
    if not soci:
        raise ValueError("Soci no trobat")

    # ─── Estils de text ─────────────────────────────────────────────
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "NomSoci",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9
    ))

    # ─── DocTemplate: marges reduïts ────────────────────────────────
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=(CARD_W, CARD_H),
        rightMargin=MARGE,
        leftMargin=MARGE,
        topMargin=MARGE,
        bottomMargin=MARGE,
    )

    # ─── Foto (si existeix) ────────────────────────────────────────
    foto_flow = Spacer(0, 0)  # placeholder
    if soci.foto:
        foto_buf = _resize_photo(soci.foto)
        foto_flow = Image(foto_buf, width=FOTO_W, height=FOTO_H)

    # ─── Bloc de text (nom, núm, alta) ────────────────────────────
    nom_complet = f"{soci.nombre} {soci.apellido1 or ''} {soci.apellido2 or ''}".strip()
    text_flow = [
        Paragraph(nom_complet, styles["NomSoci"]),
        Spacer(1, 1 * mm),
        Paragraph(f"Núm. Soci: <b>{soci.id:06d}</b>", styles["Normal"]),
        Paragraph(f"Alta: {soci.fechaAlta:%d/%m/%Y}", styles["Normal"]),
    ]

    # ─── Taula 2 columnes: [FOTO | TEXT] ───────────────────────────
    table = Table(
        [[foto_flow, text_flow]],
        colWidths=[FOTO_W + 2 * mm, CARD_W - FOTO_W - 3 * MARGE],
        hAlign="LEFT"
    )
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'TOP'),     # Foto a dalt
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),  # Text centrat verticalment
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    # ─── Story: Spacer per baixar lleugerament + taula ─────────────
    story = [
        Spacer(1, 6 * mm),   # baixa tot el bloc 6 mm
        table
    ]

    # ─── Construir PDF ─────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=lambda c, _: _fons(c, logo_path),
        onLaterPages=lambda c, _: _fons(c, logo_path),
    )