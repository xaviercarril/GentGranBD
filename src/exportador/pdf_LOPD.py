from __future__ import annotations

from datetime import date
import os

from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def generar_pdf_lopd(
    nombre_completo: str,
    dni: str,
    ruta_salida: str,
    logo_path: str = "./extra/logo.png",
    firma_path: str | None = None,
) -> None:
    """Genera el document PDF de consentiment LOPD.

    Parameters
    ----------
    nombre_completo:
        Nom i cognoms del soci.
    dni:
        Document d'identitat del soci.
    ruta_salida:
        Fitxer on es desarà el PDF generat.
    logo_path:
        Ruta del logotip que es mostrarà al document.
    firma_path:
        Ruta a la imatge de la signatura. Si es proporciona, es
        dibuixa a la zona de signatura del document.
    """

    c = canvas.Canvas(ruta_salida, pagesize=A4)
    width, height = A4

    margen = 2 * cm
    texto_inicio_y = height - margen

    # --- Logo ---
    if os.path.exists(logo_path):
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
    else:
        print(
            f"Advertencia: No s'ha trobat el logo a {logo_path}. S'està generant sense logo."
        )

    # --- Títol ---
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, texto_inicio_y, "DOCUMENT DE CONSENTIMENT - LOPD")

    # --- Cos del text ---
    c.setFont("Helvetica", 12)
    texto = f"""
D./Dª {nombre_completo}, amb DNI {dni},

MANIFESTA:

Que ha estat informat/da i entèn plenament la finalitat i l'ús de les seves dades personals recollides per part de l'Associació Gent Gran de Castelldefels, en compliment de la Llei Orgànica de Protecció de Dades Personals i garantia dels drets digitals (LOPDGDD) i del Reglament (UE) 2016/679 (RGPD).

AUTORITZA:

La incorporació de les seves dades personals als fitxers titularitat de l'associació, per tal de gestionar les activitats, serveis i comunicacions relacionades amb la seva condició de soci/a.

Drets: podrà exercir els seus drets d'accés, rectificació, supressió, oposició, limitació i portabilitat del tractament de les seves dades dirigint-se a l'associació.

Data: {date.today().strftime('%d/%m/%Y')}

Signatura del/de la soci/a:


___________________________________________
"""

    textobject = c.beginText(margen, texto_inicio_y - 2 * cm)
    textobject.setTextOrigin(margen, texto_inicio_y - 2 * cm)
    textobject.setLeading(15)
    textobject.setWordSpace(0.1)
    textobject.setCharSpace(0.0)
    textobject.setHorizScale(100)
    textobject.setFont("Helvetica", 11)

    import textwrap

    for paragraph in texto.strip().split("\n"):
        for line in textwrap.wrap(paragraph, width=95):
            textobject.textLine(line)
        textobject.textLine("")

    c.drawText(textobject)

    # --- Signatura ---
    if firma_path and os.path.exists(firma_path):
        firma_width = 6 * cm
        firma_height = 3 * cm
        c.drawImage(
            firma_path,
            margen,
            3.5 * cm,
            width=firma_width,
            height=firma_height,
            mask="auto",
        )

    c.showPage()
    c.save()

    import sys

    if sys.platform.startswith("darwin"):
        os.system(f'open "{ruta_salida}"')
    elif sys.platform.startswith("win"):
        os.startfile(ruta_salida)
    else:
        os.system(f'xdg-open "{ruta_salida}"')

