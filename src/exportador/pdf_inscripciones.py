from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, object_session

from database import SessionLocal
from models import Actividad, EstadoPago, InscripcionSocio, Pago, TipoActividadEnum


HEADER_BLOCK_HEIGHT = 34 * mm
HEADER_ROW_HEIGHT = 5.8 * mm
DATA_ROW_HEIGHT = 6.3 * mm
RESERVA_TITLE_HEIGHT = 6 * mm
MIN_RESERVA_ROWS = 1


def _estado_value(value) -> str:
    return getattr(value, "value", value) or ""


def _fmt_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _fmt_money(value) -> str:
    if value is None:
        return ""
    return f"{float(value):.0f} €"


def _nom_personal(actividad: Actividad) -> str:
    if not actividad.personal:
        return "SENSE ASSIGNAR"
    parts = [actividad.personal.nombre, actividad.personal.apellido1, actividad.personal.apellido2]
    return " ".join(part for part in parts if part).upper()


def _nom_soci(inscripcion: InscripcionSocio) -> str:
    socio = inscripcion.socio
    if not socio:
        parts = [inscripcion.noSocioNombre, inscripcion.noSocioApellido1, inscripcion.noSocioApellido2]
        return " ".join(part for part in parts if part)
    parts = [socio.nombre, socio.apellido1, socio.apellido2]
    return " ".join(part for part in parts if part)


def _dni_soci(inscripcion: InscripcionSocio) -> str:
    socio = inscripcion.socio
    if not socio:
        return inscripcion.noSocioDni or ""
    return socio.dniNie or ""


def _es_soci(inscripcion: InscripcionSocio) -> str:
    return "Sí" if inscripcion.socioID else "No"


def _telefon_soci(inscripcion: InscripcionSocio) -> str:
    socio = inscripcion.socio
    if not socio:
        return inscripcion.noSocioTelefono or ""
    return socio.telefonoMovil or socio.telefonoFijo or ""


def _is_inscrit(inscripcion: InscripcionSocio) -> bool:
    return _estado_value(inscripcion.estado) == "INSCRIT"


def _is_reserva(inscripcion: InscripcionSocio) -> bool:
    return _estado_value(inscripcion.estado) == "RESERVA"


def _ultimo_pago(inscripcion: InscripcionSocio):
    pagos = list(inscripcion.matriculas or [])
    session = object_session(inscripcion)
    if session is not None and inscripcion.id is not None:
        pagos.extend(
            session.query(Pago)
            .filter(Pago.inscripcionID == inscripcion.id)
            .all()
        )
    pagos = list({pago.id: pago for pago in pagos if pago.id is not None}.values())
    if not pagos:
        return None
    return sorted(pagos, key=lambda pago: (pago.fecha, pago.id or 0))[-1]


def _pago_text(pago) -> str:
    if not pago:
        return "No"
    estado = _estado_value(pago.estado)
    return "Sí" if estado in {EstadoPago.PAGAT.value, "PAGADO", "PAGAT"} else estado


def _is_viatge(actividad: Actividad) -> bool:
    return _estado_value(actividad.tipo) == TipoActividadEnum.VIATGE.value


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
            "Info",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=11.5,
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
            "Cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
        )
    )
    return styles


def _first_class(actividad: Actividad):
    clases = sorted(actividad.clases or [], key=lambda clase: (clase.fecha, clase.horaInicio))
    return clases[0] if clases else None


def _horario(actividad: Actividad) -> str:
    clase = _first_class(actividad)
    if not clase:
        return ""
    dies = ["DILLUNS", "DIMARTS", "DIMECRES", "DIJOUS", "DIVENDRES", "DISSABTE", "DIUMENGE"]
    dia = dies[clase.fecha.weekday()]
    inicio = clase.horaInicio.strftime("%H:%M") if clase.horaInicio else ""
    fin = clase.horaFin.strftime("%H:%M") if clase.horaFin else ""
    return f"{dia} DE {inicio} A {fin}" if inicio and fin else dia


def _inicio_curso(actividad: Actividad) -> str:
    clase = _first_class(actividad)
    if clase:
        return _fmt_date(clase.fecha)
    if actividad.curso:
        return _fmt_date(actividad.curso.fechaInicio)
    return ""


def _build_header(actividad: Actividad, total_inscrits: int, styles):
    curso = actividad.curso.nombre if actividad.curso else ""
    is_viatge = _is_viatge(actividad)
    logo_path = Path(__file__).resolve().parents[1] / "extra" / "logo.png"
    logo = Image(str(logo_path), width=25 * mm, height=18 * mm) if logo_path.exists() else ""

    top = Table(
        [[logo, Paragraph(f"CURS {curso} &nbsp;&nbsp;&nbsp; ASSOCIACIÓ GENT GRAN CASTELLDEFELS", styles["TopLine"]), ""]],
        colWidths=[42 * mm, 174 * mm, 42 * mm],
    )
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    info = Table(
        [
            [
                Paragraph(actividad.nombre.upper(), styles["Info"]),
                Paragraph(_horario(actividad), styles["InfoCenter"]),
                Paragraph(
                    f"{'INICI VIATGE' if is_viatge else 'INICI CURS'}: {_inicio_curso(actividad)}",
                    styles["Info"],
                ),
                Paragraph(f"Nº {'Participants' if is_viatge else 'Alumnes'}: {total_inscrits}", styles["Info"]),
            ],
            [
                Paragraph(f"{'Responsable' if is_viatge else 'Profesor/a'} : {_nom_personal(actividad)}", styles["Info"]),
                "",
                Paragraph(f"{'Preu viatge' if is_viatge else 'Matrícula'} : {_fmt_money(actividad.precio_matricula)}", styles["Info"]),
                "",
            ],
        ],
        colWidths=[86 * mm, 72 * mm, 48 * mm, 52 * mm],
    )
    info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return [top, Spacer(1, 8), info, Spacer(1, 5)]


def _empty_row(include_dni: bool):
    return ["", "", "", "", "", "", "", "", ""] if include_dni else ["", "", "", "", "", "", "", ""]


def _row_for_inscripcion(number: int | str, inscripcion: InscripcionSocio, cell_style, include_dni: bool):
    pago = _ultimo_pago(inscripcion)
    row = [
        str(number),
        Paragraph(_nom_soci(inscripcion), cell_style),
    ]
    if include_dni:
        row.append(_dni_soci(inscripcion))
    row.extend(
        [
            _es_soci(inscripcion),
            _telefon_soci(inscripcion),
            _pago_text(pago),
            _fmt_date(pago.fecha) if pago else "",
            inscripcion.observaciones
            or (pago.observaciones if pago and pago.observaciones else None)
            or inscripcion.noSocioObservaciones
            or "",
            "",
        ]
    )
    return row


def _build_table(inscripciones: list[InscripcionSocio], row_count: int, numbered: bool, include_dni: bool):
    cell_style = _build_styles()["Cell"]
    headers = [
        "",
        "Nom i Cognoms",
    ]
    if include_dni:
        headers.append("DNI")
    headers.extend(["Soci", "Telèfon", "Pagat", "Data Pagam.", "Modificacions/Comentaris", "Data Modif."])
    data = [headers]
    for idx in range(row_count):
        if idx < len(inscripciones):
            number = idx + 1 if numbered else ""
            data.append(_row_for_inscripcion(number, inscripciones[idx], cell_style, include_dni))
        else:
            row = _empty_row(include_dni)
            row[0] = str(idx + 1) if numbered else ""
            data.append(row)

    col_widths = (
        [7 * mm, 70 * mm, 24 * mm, 13 * mm, 25 * mm, 13 * mm, 23 * mm, 58 * mm, 25 * mm]
        if include_dni
        else [7 * mm, 92 * mm, 13 * mm, 28 * mm, 13 * mm, 25 * mm, 55 * mm, 25 * mm]
    )
    table = Table(
        data,
        colWidths=col_widths,
        rowHeights=[HEADER_ROW_HEIGHT] + [DATA_ROW_HEIGHT] * row_count,
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("BOX", (0, 0), (-1, -1), 1.1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.8),
                ("FONTSIZE", (0, 1), (-1, -1), 8.2),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (2, 0), (6 if include_dni else 5, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.94, 0.94, 0.94)]),
            ]
        )
    )
    return table


def _inscrit_row_count(actividad: Actividad, inscrits: list[InscripcionSocio]) -> int:
    max_alumnes = actividad.numMaxAlumnos or 0
    return max(max_alumnes, len(inscrits))


def _reserva_row_count(actividad: Actividad, inscrits: list[InscripcionSocio], reserves: list[InscripcionSocio]) -> int:
    page_w, page_h = landscape(A4)
    usable_h = page_h - (8 * mm) - (8 * mm)
    inscrits_rows = _inscrit_row_count(actividad, inscrits)
    used_h = (
        HEADER_BLOCK_HEIGHT
        + HEADER_ROW_HEIGHT
        + (DATA_ROW_HEIGHT * inscrits_rows)
        + RESERVA_TITLE_HEIGHT
        + HEADER_ROW_HEIGHT
    )
    available_rows = int(max(0, (usable_h - used_h) // DATA_ROW_HEIGHT))
    return max(MIN_RESERVA_ROWS, available_rows, len(reserves))


def _story(actividad: Actividad):
    styles = _build_styles()
    include_dni = _is_viatge(actividad)
    inscrits = sorted(
        [ins for ins in actividad.inscripciones if _is_inscrit(ins)],
        key=lambda ins: (
            ins.fechaInscripcion,
            ins.socio.apellido1 if ins.socio and ins.socio.apellido1 else "",
            ins.socio.apellido2 if ins.socio and ins.socio.apellido2 else "",
            ins.socio.nombre if ins.socio and ins.socio.nombre else "",
        ),
    )
    reserves = sorted(
        [ins for ins in actividad.inscripciones if _is_reserva(ins)],
        key=lambda ins: (
            ins.fechaInscripcion,
            ins.socio.apellido1 if ins.socio and ins.socio.apellido1 else "",
            ins.socio.apellido2 if ins.socio and ins.socio.apellido2 else "",
            ins.socio.nombre if ins.socio and ins.socio.nombre else "",
        ),
    )

    inscrits_rows = _inscrit_row_count(actividad, inscrits)
    reserva_rows = _reserva_row_count(actividad, inscrits, reserves)

    story = _build_header(actividad, len(inscrits), styles)
    story.append(_build_table(inscrits, inscrits_rows, numbered=True, include_dni=include_dni))
    story.append(Spacer(1, 5))
    story.append(Paragraph("RESERVA", styles["Info"]))
    story.append(_build_table(reserves, reserva_rows, numbered=False, include_dni=include_dni))
    return story


def generar_pdf_inscripciones(session: Session, actividadID: int, ruta_pdf: str):
    actividad = session.get(Actividad, actividadID)
    if not actividad:
        raise ValueError("Activitat no trobada.")

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )
    doc.build(_story(actividad))


def generar_pdf_matriculados_actividad(actividadID: int, ruta_pdf: str):
    with SessionLocal() as session:
        generar_pdf_inscripciones(session, actividadID, ruta_pdf)
