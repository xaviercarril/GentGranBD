from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Actividad, EstadoPago, InscripcionSocio, Pago


_COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _estado_value(value) -> str:
    return getattr(value, "value", value) or ""


def _fmt_date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _nom_participant(inscripcion: InscripcionSocio) -> tuple[str, str, str, str, str, str]:
    socio = inscripcion.socio
    if socio:
        return (
            socio.nombre or "",
            socio.apellido1 or "",
            socio.apellido2 or "",
            socio.dniNie or "",
            "Sí",
            socio.telefonoMovil or socio.telefonoFijo or "",
        )
    return (
        inscripcion.noSocioNombre or "",
        inscripcion.noSocioApellido1 or "",
        inscripcion.noSocioApellido2 or "",
        inscripcion.noSocioDni or "",
        "No",
        inscripcion.noSocioTelefono or "",
    )


def _ultimo_pago(session: Session, inscripcion: InscripcionSocio):
    pagos = []
    if inscripcion.socioID:
        pagos.extend(
            session.query(Pago)
            .filter(
                Pago.socioID == inscripcion.socioID,
                Pago.actividadID == inscripcion.actividadID,
            )
            .all()
        )
    if inscripcion.id is not None:
        pagos.extend(
            session.query(Pago)
            .filter(Pago.inscripcionID == inscripcion.id)
            .all()
        )
    pagos = list({pago.id: pago for pago in pagos if pago.id is not None}.values())
    if not pagos:
        return None
    return sorted(pagos, key=lambda pago: (pago.fecha, pago.id or 0))[-1]


def _pagat_text(pago) -> str:
    if not pago:
        return "No"
    estado = _estado_value(pago.estado)
    return "Sí" if estado == EstadoPago.PAGAT.value else "No"


def _cell_ref(row: int, col: int) -> str:
    return f"{_COLS[col - 1]}{row}"


def _xml_text(value) -> str:
    return escape(str(value), {"'": "&apos;", '"': "&quot;"})


def _worksheet_xml(title: str, headers: list[str], rows: list[list]) -> str:
    sheet_rows = []
    sheet_rows.append(
        '<row r="1"><c r="A1" t="inlineStr" s="1"><is><t>'
        + _xml_text(title)
        + "</t></is></c></row>"
    )
    sheet_rows.append('<row r="2"></row>')

    header_cells = []
    for col, value in enumerate(headers, start=1):
        ref = _cell_ref(3, col)
        header_cells.append(f'<c r="{ref}" t="inlineStr" s="2"><is><t>{_xml_text(value)}</t></is></c>')
    sheet_rows.append(f'<row r="3">{"".join(header_cells)}</row>')

    for row_idx, values in enumerate(rows, start=4):
        cells = []
        for col, value in enumerate(values, start=1):
            ref = _cell_ref(row_idx, col)
            if value is None or value == "":
                cells.append(f'<c r="{ref}"/>')
            elif isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}" s="3"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_xml_text(value)}</t></is></c>')
        sheet_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

    widths = [18, 18, 18, 14, 10, 16, 16, 12, 10, 16, 10, 34]
    cols = "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, width in enumerate(widths, start=1)
    )
    max_row = max(3, len(rows) + 3)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <dimension ref="A1:L{max_row}"/>
 <sheetViews>
  <sheetView workbookViewId="0">
   <pane ySplit="3" topLeftCell="A4" activePane="bottomLeft" state="frozen"/>
   <selection pane="bottomLeft" activeCell="A4" sqref="A4"/>
  </sheetView>
 </sheetViews>
 <cols>{cols}</cols>
 <sheetData>{''.join(sheet_rows)}</sheetData>
 <autoFilter ref="A3:L{max_row}"/>
 <mergeCells count="1"><mergeCell ref="A1:L1"/></mergeCells>
</worksheet>"""


def _write_xlsx(path: Path, title: str, headers: list[str], rows: list[list]) -> None:
    worksheet = _worksheet_xml(title, headers, rows)
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="xml" ContentType="application/xml"/>
 <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
 <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
 <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
 <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
 <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""",
        )
        zf.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
 <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Participants" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/styles.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>
 <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9E6C5"/></patternFill></fill></fills>
 <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
 <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
 <cellXfs count="4">
  <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  <xf numFmtId="0" fontId="1" fillId="0" borderId="0" applyFont="1" applyAlignment="1"><alignment horizontal="center"/></xf>
  <xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf>
  <xf numFmtId="4" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/>
 </cellXfs>
 <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>""",
        )
        zf.writestr("xl/worksheets/sheet1.xml", worksheet)
        zf.writestr(
            "docProps/core.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Participants</dc:title></cp:coreProperties>""",
        )
        zf.writestr(
            "docProps/app.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Gent Gran BD</Application></Properties>""",
        )


def generar_excel_participantes_viaje(actividadID: int, ruta_xlsx: str) -> None:
    with SessionLocal() as session:
        generar_excel_participantes_viaje_session(session, actividadID, ruta_xlsx)


def generar_excel_participantes_viaje_session(session: Session, actividadID: int, ruta_xlsx: str) -> None:
    actividad = session.get(Actividad, actividadID)
    if not actividad:
        raise ValueError("Viatge no trobat.")

    inscripciones = sorted(
        actividad.inscripciones or [],
        key=lambda ins: (
            ins.fechaInscripcion,
            (ins.socio.apellido1 if ins.socio else ins.noSocioApellido1) or "",
            (ins.socio.apellido2 if ins.socio else ins.noSocioApellido2) or "",
            (ins.socio.nombre if ins.socio else ins.noSocioNombre) or "",
        ),
    )

    title = f"Participants - {actividad.nombre}"
    headers = [
        "Nom",
        "Primer cognom",
        "Segon cognom",
        "DNI",
        "Soci",
        "Telèfon",
        "Data inscripció",
        "Estat",
        "Pagat",
        "Data pagament",
        "Import",
        "Observacions",
    ]
    rows = []
    for inscripcion in inscripciones:
        nombre, apellido1, apellido2, dni, es_socio, telefono = _nom_participant(inscripcion)
        pago = _ultimo_pago(session, inscripcion)
        rows.append(
            [
                nombre,
                apellido1,
                apellido2,
                dni,
                es_socio,
                telefono,
                _fmt_date(inscripcion.fechaInscripcion),
                _estado_value(inscripcion.estado),
                _pagat_text(pago),
                _fmt_date(pago.fecha) if pago else "",
                float(pago.importe) if pago else "",
                inscripcion.observaciones
                or (pago.observaciones if pago and pago.observaciones else "")
                or inscripcion.noSocioObservaciones
                or "",
            ]
        )

    output = Path(ruta_xlsx)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_xlsx(output, title, headers, rows)
