"""Generació del document de consentiment LOPD."""

from __future__ import annotations

import io
import os
from datetime import date
from pathlib import Path

from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - pillow is an optional dependency at runtime
    Image = ImageOps = None


def _resolve_logo_path(logo_path: str | None) -> str | None:
    if logo_path:
        return logo_path
    cand = Path("extra") / "logo.png"
    if cand.exists():
        return str(cand)
    return None


def generar_pdf_lopd(
    nombre_completo: str,
    dni: str,
    ruta_salida: str,
    logo_path: str | None = None,
    firma: bytes | str | Path | None = None,
    fecha_firma: date | None = None,
    abrir: bool = True,
) -> None:
    """Genera el PDF del consentiment LOPD.

    Parameters
    ----------
    nombre_completo: str
        Nom complet del soci.
    dni: str
        Document identificador que es mostrarà al text.
    ruta_salida: str
        Lloc on es guardarà el PDF.
    logo_path: str | None
        Ruta opcional cap al logo a incrustar.
    firma: bytes | str | Path | None
        Imatge de la signatura (PNG recomanat). Accepta ``bytes`` o un path.
    fecha_firma: date | None
        Data que s'imprimirà al document (per defecte, avui).
    abrir: bool
        Si ``True`` (per defecte) obrirà el PDF amb el visor per defecte.
    """

    logo_path = _resolve_logo_path(logo_path)
    data_firma = fecha_firma or date.today()

    c = canvas.Canvas(ruta_salida, pagesize=A4)
    width, height = A4

    margen = 2 * cm
    texto_inicio_y = height - margen

    if logo_path and os.path.exists(logo_path):
        img = utils.ImageReader(logo_path)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        logo_width = 4 * cm
        logo_height = logo_width * aspect
        c.drawImage(
            logo_path,
            width - logo_width - margen,
            height - logo_height - margen,
            width=logo_width,
            height=logo_height,
            mask="auto",
        )

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, texto_inicio_y, "DOCUMENT DE CONSENTIMENT - LOPD")

    cuerpo = f"""
D./Dª {nombre_completo}, amb DNI {dni}, 

MANIFESTA:

Que ha estat informat/da i entèn plenament la finalitat i l'ús de les seves dades personals recollides per part de l'Associació Gent Gran de Castelldefels, en compliment de la Llei Orgànica de Protecció de Dades Personals i garantia dels drets digitals (LOPDGDD) i del Reglament (UE) 2016/679 (RGPD).

AUTORITZA:

La incorporació de les seves dades personals als fitxers titularitat de l'associació, per tal de gestionar les activitats, serveis i comunicacions relacionades amb la seva condició de soci/a.

Drets: podrà exercir els seus drets d'accés, rectificació, supressió, oposició, limitació i portabilitat del tractament de les seves dades dirigint-se a l'associació.

Data: {data_firma.strftime('%d/%m/%Y')}

Signatura del/de la soci/a:

___________________________________________
"""

    textobject = c.beginText(margen, texto_inicio_y - 2 * cm)
    leading = 15
    textobject.setLeading(leading)
    textobject.setFont("Helvetica", 11)

    import textwrap

    signature_line_y: float | None = None
    blank_leading = leading

    for paragraph in cuerpo.strip().split("\n"):
        if not paragraph:
            textobject.textLine("")
            continue
        for line in textwrap.wrap(paragraph, width=95):
            trimmed = line.strip()
            textobject.textLine(line)
            if signature_line_y is None and trimmed.startswith("________________________________"):
                # textobject.getY() is the position of the next line; add leading to obtain the line just written
                signature_line_y = textobject.getY() + blank_leading
        textobject.textLine("")

    c.drawText(textobject)

    if firma is not None:
        firma_reader = None
        source_image = None

        if Image is not None:
            try:
                if isinstance(firma, (str, Path)):
                    source_image = Image.open(str(firma))
                else:
                    source_image = Image.open(io.BytesIO(firma))
                source_image = source_image.convert("RGBA")

                alpha = source_image.split()[-1]
                bbox = alpha.getbbox()
                if bbox:
                    source_image = source_image.crop(bbox)

                padding = max(6, int(0.03 * max(source_image.size)))
                if padding:
                    source_image = ImageOps.expand(source_image, border=padding, fill=(255, 255, 255, 0))

                firma_reader = utils.ImageReader(source_image)
            except Exception:
                firma_reader = None

        if firma_reader is None:
            if isinstance(firma, (str, Path)):
                firma_reader = utils.ImageReader(str(firma))
            else:
                firma_reader = utils.ImageReader(io.BytesIO(firma))

        fw, fh = firma_reader.getSize()
        aspect = fh / float(fw) if fw else 1.0
        firma_width = min(8 * cm, width - 2 * margen)
        firma_height = firma_width * aspect
        max_height = 2.5 * cm
        if firma_height > max_height and firma_height > 0:
            scale = max_height / firma_height
            firma_height = max_height
            firma_width *= scale

        firma_x = margen + (width - 2 * margen - firma_width) / 2
        base_line = signature_line_y if signature_line_y is not None else (margen + 4.5 * cm)
        firma_y = base_line + 0.08 * cm
        c.drawImage(
            firma_reader,
            firma_x,
            firma_y,
            width=firma_width,
            height=firma_height,
            mask="auto",
            preserveAspectRatio=True,
            anchor="sw",
        )

    c.showPage()
    c.save()

    if not abrir:
        return

    import sys

    if sys.platform.startswith("darwin"):
        os.system(f'open "{ruta_salida}"')
    elif sys.platform.startswith("win"):
        os.startfile(ruta_salida)  # type: ignore[attr-defined]
    else:
        os.system(f'xdg-open "{ruta_salida}"')
