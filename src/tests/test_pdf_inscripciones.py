from datetime import date

from exportador.pdf_inscripciones import (
    COURSE_HEADERS,
    TRIP_HEADERS,
    _build_table,
    _ordered_inscripciones,
    _pago_text,
    _ultimo_pago,
    generar_pdf_inscripciones,
)
from models import (
    Actividad,
    CursoAcademico,
    EstadoInscripcion,
    EstadoPago,
    InscripcionSocio,
    Pago,
    Socio,
)


def test_generar_pdf_inscripciones(session, tmp_path):
    curso = CursoAcademico(
        nombre="2025-2026",
        fechaInicio=date(2025, 9, 1),
        fechaFin=date(2026, 6, 30),
    )
    session.add(curso)
    session.commit()

    actividad = Actividad(
        nombre="Anglès Elemental Nivell A2",
        numMaxAlumnos=18,
        cursoAcademicoID=curso.id,
        precio_matricula=20,
    )
    session.add(actividad)
    session.commit()

    for i in range(22):
        socio = Socio(
            dniNie=f"X{i:03}",
            nombre=f"Nom{i}",
            apellido1=f"Cognom{i}",
            telefonoMovil=f"600000{i:03}",
            fechaAlta=date.today(),
        )
        session.add(socio)
        session.commit()

        estado = EstadoInscripcion.INSCRIT if i < 18 else EstadoInscripcion.RESERVA
        inscripcion = InscripcionSocio(
            socioID=socio.id,
            actividadID=actividad.id,
            fechaInscripcion=date(2025, 9, min(i + 1, 28)),
            estado=estado,
        )
        session.add(inscripcion)
        session.commit()

        if i % 2 == 0:
            session.add(
                Pago(
                    socioID=socio.id,
                    actividadID=actividad.id,
                    fecha=date(2025, 9, 16),
                    importe=20,
                    estado=EstadoPago.PAGAT,
                )
            )
            session.commit()

    session.add(
        InscripcionSocio(
            socioID=None,
            actividadID=actividad.id,
            noSocioNombre="Persona",
            noSocioApellido1="No",
            noSocioApellido2="Sòcia",
            noSocioDni="Y999",
            noSocioTelefono="699111222",
            noSocioEmail="persona@example.com",
            noSocioObservaciones="Pendent de confirmar",
            fechaInscripcion=date(2025, 9, 23),
            estado=EstadoInscripcion.RESERVA,
        )
    )
    session.commit()

    output_file = tmp_path / "matriculats.pdf"
    generar_pdf_inscripciones(session, actividad.id, str(output_file))

    assert output_file.stat().st_size > 0


def test_tabla_pdf_curso_coincide_con_campos_visibles():
    socio = Socio(
        dniNie="X1234567A",
        nombre="Anna",
        apellido1="Garcia",
        apellido2="Serra",
        telefonoMovil="600111222",
        fechaAlta=date.today(),
    )
    inscripcion = InscripcionSocio(
        socio=socio,
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
        observaciones="Prefereix primera fila",
    )

    table = _build_table([inscripcion], include_dni=False)

    assert [cell.getPlainText() for cell in table._cellvalues[0]] == COURSE_HEADERS
    assert [cell.getPlainText() for cell in table._cellvalues[1]] == [
        "-",
        "Garcia",
        "Serra",
        "Anna",
        "600111222",
        date.today().strftime("%d/%m/%Y"),
        "INSCRIT",
        "Prefereix primera fila",
    ]


def test_tabla_pdf_viatge_añade_dni_y_pagat():
    socio = Socio(
        id=42,
        dniNie="X1234567A",
        nombre="Anna",
        apellido1="Garcia",
        fechaAlta=date.today(),
    )
    inscripcion = InscripcionSocio(
        socio=socio,
        socioID=42,
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
    )

    table = _build_table([inscripcion], include_dni=True)

    assert [cell.getPlainText() for cell in table._cellvalues[0]] == TRIP_HEADERS
    assert [cell.getPlainText() for cell in table._cellvalues[1]][5:7] == ["X1234567A", "No"]


def test_pdf_respeta_el_orden_de_inscripciones_recibido():
    actividad = Actividad(nombre="Gimnàstica")
    actividad.inscripciones = [
        InscripcionSocio(id=1, fechaInscripcion=date(2026, 1, 1), estado=EstadoInscripcion.INSCRIT),
        InscripcionSocio(id=2, fechaInscripcion=date(2026, 1, 2), estado=EstadoInscripcion.INSCRIT),
        InscripcionSocio(id=3, fechaInscripcion=date(2026, 1, 3), estado=EstadoInscripcion.INSCRIT),
    ]

    ordenadas = _ordered_inscripciones(actividad, [3, 1, 2])

    assert [inscripcion.id for inscripcion in ordenadas] == [3, 1, 2]


def test_pdf_usa_pago_por_inscripcion_en_persona_no_socia(session):
    inscripcion = InscripcionSocio(
        socioID=None,
        actividadID=1,
        noSocioNombre="Persona",
        noSocioApellido1="Externa",
        noSocioDni="Y123",
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
    )
    session.add(inscripcion)
    session.commit()

    session.add(
        Pago(
            socioID=None,
            actividadID=1,
            inscripcionID=inscripcion.id,
            fecha=date.today(),
            importe=25,
            estado=EstadoPago.PAGAT,
        )
    )
    session.commit()

    assert _pago_text(_ultimo_pago(inscripcion)) == "Sí"
