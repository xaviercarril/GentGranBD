from datetime import date

from exportador.pdf_inscripciones import _build_table, _pago_text, _ultimo_pago, generar_pdf_inscripciones
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


def test_tabla_pdf_viatge_incluye_dni():
    socio = Socio(
        dniNie="X1234567A",
        nombre="Anna",
        apellido1="Garcia",
        fechaAlta=date.today(),
    )
    inscripcion = InscripcionSocio(
        socio=socio,
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
    )

    table = _build_table([inscripcion], row_count=1, numbered=True, include_dni=True)

    assert "DNI" in table._cellvalues[0]
    assert "X1234567A" in table._cellvalues[1]


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
