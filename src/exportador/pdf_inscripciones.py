from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, object_session

from controladores.dtos import normalize_phone
from database import SessionLocal
from inscripcion_columns import COURSE_INSCRIPTION_COLUMNS, TRIP_INSCRIPTION_COLUMNS
from models import Actividad, EstadoPago, InscripcionSocio, Pago, TipoActividadEnum


COURSE_HEADERS = [label for label, key in COURSE_INSCRIPTION_COLUMNS if key != "id"]
TRIP_HEADERS = [label for label, key in TRIP_INSCRIPTION_COLUMNS if key != "id"]
COURSE_COLUMN_WIDTHS = [18 * mm, 38 * mm, 38 * mm, 34 * mm, 28 * mm, 30 * mm, 21 * mm, 74 * mm]
TRIP_COLUMN_WIDTHS = [
    12 * mm,
    24 * mm,
    24 * mm,
    22 * mm,
    21 * mm,
    23 * mm,
    12 * mm,
    14 * mm,
    34 * mm,
    18 * mm,
    18 * mm,
    59 * mm,
]


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


def _nom_soci_fields(inscripcion: InscripcionSocio) -> tuple[str, str, str]:
    socio = inscripcion.socio
    if not socio:
        return (
            inscripcion.noSocioApellido1 or "",
            inscripcion.noSocioApellido2 or "",
            inscripcion.noSocioNombre or "Desconegut",
        )
    return socio.apellido1 or "", socio.apellido2 or "", socio.nombre or ""


def _dni_soci(inscripcion: InscripcionSocio) -> str:
    socio = inscripcion.socio
    if not socio:
        return inscripcion.noSocioDni or ""
    return socio.dniNie or ""


def _telefon_soci(inscripcion: InscripcionSocio) -> str:
    socio = inscripcion.socio
    if not socio:
        return normalize_phone(inscripcion.noSocioTelefono) or ""
    return normalize_phone(socio.telefonoMovil) or ""


def _is_inscrit(inscripcion: InscripcionSocio) -> bool:
    return _estado_value(inscripcion.estado) == "INSCRIT"


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
    return "Sí" if estado in {EstadoPago.PAGAT.value, "PAGADO", "PAGAT"} else "No"


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
            fontSize=7.5,
            leading=9,
        )
    )
    styles.add(
        ParagraphStyle(
            "CellCenter",
            parent=styles["Cell"],
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
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


def _paragraph(value, style):
    return Paragraph(escape(str(value if value is not None else "")), style)


def _row_for_inscripcion(inscripcion: InscripcionSocio, styles, include_dni: bool):
    apellido1, apellido2, nombre = _nom_soci_fields(inscripcion)
    row = [
        _paragraph(inscripcion.socioID if inscripcion.socioID else "-", styles["CellCenter"]),
        _paragraph(apellido1, styles["Cell"]),
        _paragraph(apellido2, styles["Cell"]),
        _paragraph(nombre, styles["Cell"]),
        _paragraph(_telefon_soci(inscripcion), styles["CellCenter"]),
    ]
    if include_dni:
        row.extend(
            [
                _paragraph(_dni_soci(inscripcion), styles["CellCenter"]),
                _paragraph(_pago_text(_ultimo_pago(inscripcion)), styles["CellCenter"]),
                _paragraph(inscripcion.asiento or "", styles["CellCenter"]),
                _paragraph(inscripcion.lugarRecogida or "", styles["Cell"]),
            ]
        )
    row.extend(
        [
            _paragraph(_fmt_date(inscripcion.fechaInscripcion), styles["CellCenter"]),
            _paragraph(_estado_value(inscripcion.estado), styles["CellCenter"]),
            _paragraph(inscripcion.observaciones or "", styles["Cell"]),
        ]
    )
    return row


def _build_table(inscripciones: list[InscripcionSocio], include_dni: bool):
    styles = _build_styles()
    headers = TRIP_HEADERS if include_dni else COURSE_HEADERS
    data = [[_paragraph(header, styles["TableHeader"]) for header in headers]]
    data.extend(_row_for_inscripcion(inscripcion, styles, include_dni) for inscripcion in inscripciones)

    table = Table(
        data,
        colWidths=TRIP_COLUMN_WIDTHS if include_dni else COURSE_COLUMN_WIDTHS,
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("BOX", (0, 0), (-1, -1), 1.1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.9, 0.78)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.94, 0.94, 0.94)]),
            ]
        )
    )
    return table


def _ordered_inscripciones(actividad: Actividad, inscripcion_ids: list[int] | None = None):
    inscripciones = list(actividad.inscripciones or [])
    if inscripcion_ids is None:
        return sorted(
            inscripciones,
            key=lambda inscripcion: (inscripcion.fechaInscripcion, inscripcion.id or 0),
        )

    by_id = {inscripcion.id: inscripcion for inscripcion in inscripciones}
    return [by_id[inscripcion_id] for inscripcion_id in inscripcion_ids if inscripcion_id in by_id]


def _story(actividad: Actividad, inscripcion_ids: list[int] | None = None):
    styles = _build_styles()
    include_dni = _is_viatge(actividad)
    inscripciones = _ordered_inscripciones(actividad, inscripcion_ids)
    total_inscrits = sum(1 for inscripcion in inscripciones if _is_inscrit(inscripcion))

    story = _build_header(actividad, total_inscrits, styles)
    story.append(_build_table(inscripciones, include_dni=include_dni))
    return story


def generar_pdf_inscripciones(
    session: Session,
    actividadID: int,
    ruta_pdf: str,
    inscripcion_ids: list[int] | None = None,
):
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
    doc.build(_story(actividad, inscripcion_ids))


def generar_pdf_matriculados_actividad(
    actividadID: int,
    ruta_pdf: str,
    inscripcion_ids: list[int] | None = None,
):
    with SessionLocal() as session:
        generar_pdf_inscripciones(session, actividadID, ruta_pdf, inscripcion_ids)
