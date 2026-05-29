from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database import SessionLocal
from models import Actividad


MESOS_CAT = {
    1: "GENER",
    2: "FEBRER",
    3: "MARÇ",
    4: "ABRIL",
    5: "MAIG",
    6: "JUNY",
    7: "JULIOL",
    8: "AGOST",
    9: "SETEMBRE",
    10: "OCTUBRE",
    11: "NOVEMBRE",
    12: "DESEMBRE",
}

DIES_CAT = {
    0: "DILLUNS",
    1: "DIMARTS",
    2: "DIMECRES",
    3: "DIJOUS",
    4: "DIVENDRES",
    5: "DISSABTE",
    6: "DIUMENGE",
}

MAX_DATE_COLS = 16
MIN_STUDENT_ROWS = 20


def _fmt_time(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "time"):
        value = value.time()
    return value.strftime("%H:%M")


def _nom_personal(actividad: Actividad) -> str:
    if not actividad.personal:
        return "SENSE PERSONAL"
    parts = [
        actividad.personal.nombre or "",
        actividad.personal.apellido1 or "",
        actividad.personal.apellido2 or "",
    ]
    return " ".join(part for part in parts if part).upper()


def _nom_soci(socio) -> str:
    parts = [socio.nombre or "", socio.apellido1 or "", socio.apellido2 or ""]
    return " ".join(part for part in parts if part).upper()


def _nom_trimestre(trimestre) -> str:
    if not trimestre:
        return "Sense trimestre"
    nombre = getattr(trimestre, "nombre", "")
    return getattr(nombre, "value", nombre) or "Sense trimestre"


def _is_inscrit(inscripcion) -> bool:
    estado = getattr(inscripcion.estado, "value", inscripcion.estado)
    return estado == "INSCRIT"


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "TopLine",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "SheetTitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
        )
    )
    styles.add(
        ParagraphStyle(
            "Info",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            "InfoCenter",
            parent=styles["Info"],
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "FooterLegend",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
        )
    )
    return styles


def _build_header(actividad: Actividad, clases, total_alumnos: int, styles):
    curso = actividad.curso.nombre if actividad.curso else "Sense curs"
    primera_clase = clases[0]
    dia = DIES_CAT.get(primera_clase.fecha.weekday(), "")
    hora_inicio = _fmt_time(primera_clase.horaInicio)
    hora_fin = _fmt_time(primera_clase.horaFin)
    horario = dia
    if hora_inicio and hora_fin:
        horario = f"{horario} DE {hora_inicio} A {hora_fin}"

    centro = actividad.lugar.nombre if actividad.lugar else "Centre Frederic Mompou"
    inicio = primera_clase.fecha.strftime("%d/%m/%Y")
    trimestre = _nom_trimestre(primera_clase.trimestre)
    logo_path = Path(__file__).resolve().parents[1] / "extra" / "logo.png"
    logo = Image(str(logo_path), width=28 * mm, height=20 * mm) if logo_path.exists() else ""

    title_block = [
        [Paragraph(f"CURS {curso} &nbsp;&nbsp; ASSOCIACIÓ GENT GRAN CASTELLDEFELS", styles["TopLine"])],
        [Spacer(1, 9)],
        [Paragraph("ASSOCIACIÓ GENT GRAN DE CASTELLDEFELS", styles["SheetTitle"])],
    ]
    title_table = Table(title_block, colWidths=[128 * mm])
    title_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))

    top = Table(
        [[logo, title_table, Paragraph(f"INICI CURS : {inicio}<br/>TRIMESTRE : {trimestre}", styles["Info"])]],
        colWidths=[42 * mm, 135 * mm, 76 * mm],
    )
    top.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "LEFT"),
            ]
        )
    )

    activity_info = Table(
        [
            [
                Paragraph(actividad.nombre.upper(), styles["Info"]),
                Paragraph(horario, styles["InfoCenter"]),
                Paragraph(f"Nº Alumnes: {total_alumnos}", styles["Info"]),
            ],
            [
                Paragraph(f"Profesor/a : {_nom_personal(actividad)}", styles["Info"]),
                Paragraph(centro, styles["InfoCenter"]),
                "",
            ],
        ],
        colWidths=[76 * mm, 112 * mm, 65 * mm],
    )
    activity_info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    return [top, Spacer(1, 5), activity_info, Spacer(1, 4)]


def _month_spans(dates: list) -> tuple[list[str], list[tuple]]:
    row = ["", ""]
    spans = []
    current_month = None
    month_start = 2
    for index, dt in enumerate(dates, start=2):
        month = MESOS_CAT[dt.month]
        if month != current_month:
            if current_month is not None and index - 1 > month_start:
                spans.append(("SPAN", (month_start, 0), (index - 1, 0)))
            row.append(month)
            current_month = month
            month_start = index
        else:
            row.append("")
    if current_month is not None and len(row) - 1 > month_start:
        spans.append(("SPAN", (month_start, 0), (len(row) - 1, 0)))
    return row, spans


def _build_attendance_table(actividad: Actividad, clases, inscripciones, date_col_width: float):
    dates = [clase.fecha for clase in clases]
    month_row, spans = _month_spans(dates)
    day_row = ["", "Nom i Cognoms"] + [str(dt.day) for dt in dates]
    data = [month_row, day_row]

    clases_por_fecha = {clase.fecha: clase for clase in clases}
    asistencia_por_clase_socio = {
        (asistencia.claseID, asistencia.socioID): asistencia
        for clase in clases
        for asistencia in clase.asistencias
    }

    rows_needed = max(MIN_STUDENT_ROWS, len(inscripciones))
    for idx in range(rows_needed):
        if idx < len(inscripciones):
            socio = inscripciones[idx].socio
            row = [str(idx + 1), _nom_soci(socio)]
            for dt in dates:
                clase = clases_por_fecha[dt]
                asistencia = asistencia_por_clase_socio.get((clase.id, socio.id))
                row.append("X" if asistencia and asistencia.presente else "")
        else:
            row = [str(idx + 1), ""] + [""] * len(dates)
        data.append(row)

    col_widths = [7 * mm, 68 * mm] + [date_col_width] * len(dates)
    table = Table(data, colWidths=col_widths, repeatRows=2)
    table.setStyle(
        TableStyle(
            [
                *spans,
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.black),
                ("LINEBELOW", (0, 1), (-1, 1), 1.1, colors.black),
                ("LINEAFTER", (1, 0), (1, -1), 1.1, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 2), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                ("FONTNAME", (1, 2), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 1), 8),
                ("FONTSIZE", (0, 2), (-1, -1), 8),
                ("FONTSIZE", (2, 2), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ("LEFTPADDING", (1, 0), (1, -1), 2),
                ("RIGHTPADDING", (1, 0), (1, -1), 2),
                ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.Color(0.94, 0.94, 0.94)]),
            ]
        )
    )
    return table


def generar_pdf_parrilla_asistencias(actividadID: int, trimestreID: int, ruta_pdf: str):
    """Genera una hoja de asistencia imprimible, similar a la plantilla manual."""
    with SessionLocal() as session:
        actividad = session.get(Actividad, actividadID)
        if not actividad:
            raise ValueError("Activitat no trobada.")

        clases = sorted(
            [clase for clase in actividad.clases if clase.trimestreID == trimestreID],
            key=lambda clase: (clase.fecha, clase.horaInicio),
        )
        if not clases:
            raise ValueError("No hi ha cap classe registrada per aquest trimestre.")

        inscripciones = sorted(
            [ins for ins in actividad.inscripciones if ins.socioID and _is_inscrit(ins)],
            key=lambda ins: (
                ins.socio.apellido1 or "",
                ins.socio.apellido2 or "",
                ins.socio.nombre or "",
            ),
        )

        page_w, _ = landscape(A4)
        left_margin = 8 * mm
        right_margin = 8 * mm
        usable_w = page_w - left_margin - right_margin
        fixed_w = 7 * mm + 68 * mm

        styles = _build_styles()
        doc = SimpleDocTemplate(
            ruta_pdf,
            pagesize=landscape(A4),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=7 * mm,
            bottomMargin=8 * mm,
        )

        story = []
        for idx in range(0, len(clases), MAX_DATE_COLS):
            clases_bloc = clases[idx : idx + MAX_DATE_COLS]
            if idx:
                story.append(PageBreak())
            date_col_width = (usable_w - fixed_w) / len(clases_bloc)
            story.extend(_build_header(actividad, clases_bloc, len(inscripciones), styles))
            story.append(_build_attendance_table(actividad, clases_bloc, inscripciones, date_col_width))
            story.append(Spacer(1, 4))
            story.append(Paragraph("Assi: X&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Falta: F&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Viatge: V&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Malaltia: M", styles["FooterLegend"]))

        doc.build(story)
