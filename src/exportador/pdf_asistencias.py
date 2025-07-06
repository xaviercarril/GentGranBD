from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak
)
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import date

from controladores.actividades import consultar_curso_academico
from models import Actividad

# ─────────────────────────────────────────────────────────────
# Diccionari de noms de mes en català (MAJÚSCULES)
# ─────────────────────────────────────────────────────────────
MESOS_CAT = {
    1: "GENER",     2: "FEBRER",   3: "MARÇ",
    4: "ABRIL",     5: "MAIG",     6: "JUNY",
    7: "JULIOL",    8: "AGOST",    9: "SETEMBRE",
    10: "OCTUBRE", 11: "NOVEMBRE", 12: "DESEMBRE"
}

# Màxim de columnes de dates per pàgina (34 dates + 1 col. nom soci = 35)
MAX_DATE_COLS = 30


# ─────────────────────────────────────────────────────────────
# Funció principal
# ─────────────────────────────────────────────────────────────
def generar_pdf_parrilla_asistencias(session, actividad_id: int, ruta_pdf: str):
    """Genera la parrilla d’assistències (PDF) d’una activitat en català."""

    # 1. Validació i càrrega
    actividad = session.query(Actividad).filter_by(id=actividad_id).first()
    if not actividad:
        raise ValueError("Activitat no trobada.")

    inscripciones = actividad.inscripciones
    socios_noms = [
        f"{i.socio.nombre} {i.socio.apellido1 or ''}".strip()
        for i in inscripciones
    ]

    # 2. Recollir totes les dates (obj. date) d’assistències registrades
    dates = sorted({
        a.fecha.fecha
        for ins in inscripciones
        for a in (ins.asistencias or [])
        if a and a.fecha
    })
    if not dates:
        raise ValueError("No hi ha assistències registrades.")

    # 3. Agrupar per mesos
    mesos: dict[str, list[int]] = {}
    for d in dates:
        mesos.setdefault(MESOS_CAT[d.month], []).append(d.day)

    # 4. Encapçalaments globals
    fila_mesos = [""]
    fila_dies  = ["SOCI / DIA"]
    for mes, dies in mesos.items():
        fila_mesos += [mes] + [""] * (len(dies) - 1)
        fila_dies  += [str(d) for d in dies]

    total_date_cols = len(fila_dies) - 1

    # 5. Dividir en blocs si supera el límit
    dies_per_bloc = (
        fila_dies[1:]
        if total_date_cols <= MAX_DATE_COLS
        else [
            fila_dies[1:][i:i + MAX_DATE_COLS]
            for i in range(0, total_date_cols, MAX_DATE_COLS)
        ]
    )
    # Normalitzem a llista de llistes
    if isinstance(dies_per_bloc[0], str):
        dies_per_bloc = [dies_per_bloc]

    # 6. Preparar document
    nom_personal = actividad.personal.nombre + " " + actividad.personal.apellido1 if actividad.personal else "Sense personal"
    curs_academic = consultar_curso_academico(session, actividad.id) or "Sense curs acadèmic" 
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(ruta_pdf, pagesize=landscape(A4))
    story = [
        Paragraph(
            "<para align='center'>ASSOCIACIÓ GENT GRAN DE CASTELLDEFELS</para>", 
            styles["Title"]
        ),
        Spacer(1, 6),
        Paragraph(
            f"<para align='center'>Centre Municipal Frederic Mompou. Curs:  {curs_academic}  ASSISTÈNCIA</para>", 
            styles["Heading2"]
        ),
        Spacer(1, 6),
        Paragraph(
            f"{actividad.nombre}: {nom_personal} \b Horari: {getattr(actividad, 'descripcion_fecha', 'Sense horari')}", 
            styles["Heading3"]
        ),
        Spacer(1, 12),
    ]

    # 7. Processar cada bloc
    for bloc_idx, dies_bloc in enumerate(dies_per_bloc):
        # 7.1 Encapçalaments del bloc
        fila_mesos_bloc = [""]
        fila_dies_bloc  = ["SOCI / DIA"]
        spans_bloc = []
        col_ptr = 1

        for mes, dies in mesos.items():
            dies_present_bloc = [d for d in dies if str(d) in dies_bloc]
            if not dies_present_bloc:
                continue
            fila_mesos_bloc += [mes] + [""] * (len(dies_present_bloc) - 1)
            fila_dies_bloc  += [str(d) for d in dies_present_bloc]
            if len(dies_present_bloc) > 1:
                spans_bloc.append(
                    ('SPAN', (col_ptr, 0), (col_ptr + len(dies_present_bloc) - 1, 0))
                )
            col_ptr += len(dies_present_bloc)

        # 7.2 Dataframe de la taula
        data_bloc = [fila_mesos_bloc, fila_dies_bloc]
        cols_dates_bloc = len(fila_dies_bloc) - 1

        # Llista objectes date en l'ordre del bloc
        dates_bloc_objects: list[date] = [
            dt for dt in dates if str(dt.day) in dies_bloc
        ]

        # Omplir cada soci
        for ins in inscripciones:
            fila = [f"{ins.socio.nombre} {ins.socio.apellido1 or ''}".strip()]
            for dt in dates_bloc_objects:
                present = any(
                    a.presente and a.fecha and a.fecha.fecha == dt
                    for a in (ins.asistencias or [])
                )
                fila.append("✗" if present else "")
            # Completar per si falten columnes (si hi ha menys de MAX_DATE_COLS)
            while len(fila) < cols_dates_bloc + 1:
                fila.append("")
            data_bloc.append(fila)

        # 7.3 Amplades dinàmiques (landscape)
        page_w, _ = landscape(A4)
        margin = 40 * mm
        usable_w = page_w - margin
        first_col_w = 45 * mm
        remaining_w = usable_w - first_col_w
        col_w = remaining_w / cols_dates_bloc if cols_dates_bloc else remaining_w
        col_widths = [first_col_w] + [col_w] * cols_dates_bloc

        # 7.4 Construir la taula
        tabla = Table(data_bloc, colWidths=col_widths, repeatRows=2)
        tabla.setStyle(TableStyle([
            *spans_bloc,
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('BACKGROUND', (0,1), (-1,1), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0,2), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
        ]))

        story.append(tabla)
        if bloc_idx < len(dies_per_bloc) - 1:
            story.append(PageBreak())

    # 8. Generar PDF
    doc.build(story)

# ─────────────────────────────────────────────────────────────
# Exemple ràpid (requereix sessió SQLAlchemy):
# generar_pdf_parrilla_asistencias(session, 1, "parrilla.pdf")
# ─────────────────────────────────────────────────────────────