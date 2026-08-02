from datetime import date

from openpyxl import load_workbook

from exportador.excel_participantes import (
    generar_excel_inscritos_curso_session,
    generar_excel_participantes_viaje_session,
)
from models import (
    Actividad,
    EstadoInscripcion,
    EstadoPago,
    InscripcionSocio,
    Pago,
    Socio,
    TipoActividadEnum,
)


def test_generar_excel_participantes_viaje_incluye_no_socios_y_pagat(session, tmp_path):
    actividad = Actividad(
        nombre="Viatge Tarragona",
        tipo=TipoActividadEnum.VIATGE,
        numMaxAlumnos=30,
        precio_matricula=25,
    )
    session.add(actividad)
    session.commit()

    socio = Socio(
        dniNie="X123",
        nombre="Anna",
        apellido1="Garcia",
        telefonoMovil="600111222",
        fechaAlta=date.today(),
    )
    session.add(socio)
    session.commit()

    session.add(
        InscripcionSocio(
            socioID=socio.id,
            actividadID=actividad.id,
            fechaInscripcion=date(2026, 2, 1),
            estado=EstadoInscripcion.INSCRIT,
        )
    )
    no_socio = InscripcionSocio(
        socioID=None,
        actividadID=actividad.id,
        noSocioNombre="Persona",
        noSocioApellido1="Externa",
        noSocioDni="Y999",
        noSocioTelefono="699111222",
        fechaInscripcion=date(2026, 2, 2),
        estado=EstadoInscripcion.INSCRIT,
    )
    session.add(no_socio)
    session.commit()

    session.add(
        Pago(
            socioID=None,
            actividadID=actividad.id,
            inscripcionID=no_socio.id,
            fecha=date(2026, 2, 3),
            importe=25,
            estado=EstadoPago.PAGAT,
        )
    )
    session.commit()

    output = tmp_path / "participants.xlsx"
    generar_excel_participantes_viaje_session(session, actividad.id, str(output))

    wb = load_workbook(output)
    ws = wb["Participants"]
    assert ws["A1"].value == "Participants - Viatge Tarragona"
    assert ws["D3"].value == "DNI"
    assert ws["H5"].value == "Sí"
    assert ws["D5"].value == "Y999"
    assert "Soci" not in [cell.value for cell in ws[3]]


def test_generar_excel_inscritos_curso_incluye_socios_y_no_socios(session, tmp_path):
    actividad = Actividad(
        nombre="Gimnàstica",
        tipo=TipoActividadEnum.CURS,
        numMaxAlumnos=20,
    )
    socio = Socio(
        dniNie="Z123",
        nombre="Maria",
        apellido1="Puig",
        apellido2="Soler",
        telefonoMovil="600123456",
        fechaAlta=date.today(),
    )
    session.add_all([actividad, socio])
    session.commit()

    session.add_all(
        [
            InscripcionSocio(
                socioID=socio.id,
                actividadID=actividad.id,
                fechaInscripcion=date(2026, 3, 1),
                estado=EstadoInscripcion.INSCRIT,
                observaciones="Grup matí",
            ),
            InscripcionSocio(
                socioID=None,
                actividadID=actividad.id,
                noSocioNombre="Joan",
                noSocioApellido1="Extern",
                noSocioTelefono="699123456",
                fechaInscripcion=date(2026, 3, 2),
                estado=EstadoInscripcion.RESERVA,
            ),
        ]
    )
    session.commit()

    output = tmp_path / "inscrits.xlsx"
    generar_excel_inscritos_curso_session(session, actividad.id, str(output))

    ws = load_workbook(output)["Inscrits"]
    assert ws["A1"].value == "Inscrits - Gimnàstica"
    assert [cell.value for cell in ws[3]] == [
        "Num soci",
        "Primer cognom",
        "Segon cognom",
        "Nom",
        "Telèfon mòbil",
        "Data inscripció",
        "Estat",
        "Observacions",
    ]
    assert ws["A4"].value == str(socio.id)
    assert ws["D4"].value == "Maria"
    assert ws["H4"].value == "Grup matí"
    assert ws["A5"].value == "-"
    assert ws["D5"].value == "Joan"
    assert ws["G5"].value == "RESERVA"
