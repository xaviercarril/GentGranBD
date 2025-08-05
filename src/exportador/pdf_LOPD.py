from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import utils
import os
from datetime import date

def generar_pdf_lopd(nombre_completo: str, dni: str, ruta_salida: str, logo_path="/Users/xavier.carril/Desktop/Gent Gran BD/src/extra/logo.png"):
    c = canvas.Canvas(ruta_salida, pagesize=A4)
    width, height = A4

    margen = 2 * cm
    texto_inicio_y = height - margen

    # Insertar logo en esquina superior derecha
    if os.path.exists(logo_path):
        img = utils.ImageReader(logo_path)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        logo_width = 4 * cm
        logo_height = logo_width * aspect
        c.drawImage(logo_path, width - logo_width - margen, height - logo_height - margen,
                    width=logo_width, height=logo_height, mask='auto')
    else:
        print(f"Advertencia: No s'ha trobat el logo a {logo_path}. S'està generant sense logo.")

    # Título centrado
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, texto_inicio_y, "DOCUMENT DE CONSENTIMENT - LOPD")

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
    c.showPage()
    c.save()

    import sys
    if sys.platform.startswith("darwin"):
        os.system(f'open "{ruta_salida}"')
    elif sys.platform.startswith("win"):
        os.startfile(ruta_salida)
    else:
        os.system(f'xdg-open "{ruta_salida}"')
