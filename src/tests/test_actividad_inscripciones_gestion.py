from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import controladores.actividades as actividades
import controladores.inscripcion_socio as inscripciones
import controladores.socios as socios
from models import Base, CursoAcademico, EstadoInscripcion


@pytest.fixture()
def patched_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(actividades, "SessionLocal", Session)
    monkeypatch.setattr(inscripciones, "SessionLocal", Session)
    monkeypatch.setattr(socios, "SessionLocal", Session)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _curso(session):
    curso = CursoAcademico(
        nombre="2025-2026",
        fechaInicio=date(2025, 9, 1),
        fechaFin=date(2026, 6, 30),
    )
    session.add(curso)
    session.commit()
    return curso.id


def _actividad(session, max_alumnos):
    return actividades.registrar_actividad({
        "nombre": "Gimnasia",
        "numMaxAlumnos": max_alumnos,
        "cursoAcademico_id": _curso(session),
        "precio_matricula": 10.0,
    })


def _socio(dni, nombre):
    return socios.registrar_socio({
        "dniNie": dni,
        "nombre": nombre,
        "apellido1": "Prova",
        "fechaAlta": date.today(),
    })


def test_actualizar_estados_promociona_reserva_al_eliminar_inscrit(patched_session):
    act_id = _actividad(patched_session, max_alumnos=1)
    socio_1 = _socio("T001", "Anna")
    socio_2 = _socio("T002", "Joan")

    ins_1 = inscripciones.registrar_inscripcion({
        "socioID": socio_1,
        "actividadID": act_id,
        "fechaInscripcion": date(2026, 1, 1),
        "estado": EstadoInscripcion.INSCRIT.value,
    })
    inscripciones.registrar_inscripcion({
        "socioID": socio_2,
        "actividadID": act_id,
        "fechaInscripcion": date(2026, 1, 2),
        "estado": EstadoInscripcion.RESERVA.value,
    })

    inscripciones.eliminar_inscripcion(ins_1.id)
    actividades.actualizar_estados_inscripciones(act_id)

    restantes = actividades.listar_inscripciones_por_Actividad(act_id)
    assert len(restantes) == 1
    assert restantes[0]["socioID"] == socio_2
    assert restantes[0]["estado"] == EstadoInscripcion.INSCRIT


def test_actualizar_estados_con_maximo_cero_deja_todos_en_reserva(patched_session):
    act_id = _actividad(patched_session, max_alumnos=0)
    socio_id = _socio("T003", "Maria")

    inscripciones.registrar_inscripcion({
        "socioID": socio_id,
        "actividadID": act_id,
        "fechaInscripcion": date.today(),
        "estado": EstadoInscripcion.INSCRIT.value,
    })

    actividades.actualizar_estados_inscripciones(act_id)

    [inscripcion] = actividades.listar_inscripciones_por_Actividad(act_id)
    assert inscripcion["estado"] == EstadoInscripcion.RESERVA


def test_no_permite_duplicar_socio_en_la_misma_actividad(patched_session):
    act_id = _actividad(patched_session, max_alumnos=2)
    socio_id = _socio("T004", "Pere")
    data = {
        "socioID": socio_id,
        "actividadID": act_id,
        "fechaInscripcion": date.today(),
        "estado": EstadoInscripcion.INSCRIT.value,
    }

    inscripciones.registrar_inscripcion(data)

    with pytest.raises(ValueError):
        inscripciones.registrar_inscripcion(data)


def test_modificar_fecha_inscripcion_reordena_promocion_de_reservas(patched_session):
    act_id = _actividad(patched_session, max_alumnos=1)
    socio_1 = _socio("T005", "Nuria")
    socio_2 = _socio("T006", "Marc")

    inscripciones.registrar_inscripcion({
        "socioID": socio_1,
        "actividadID": act_id,
        "fechaInscripcion": date(2026, 1, 10),
        "estado": EstadoInscripcion.RESERVA.value,
    })
    ins_2 = inscripciones.registrar_inscripcion({
        "socioID": socio_2,
        "actividadID": act_id,
        "fechaInscripcion": date(2026, 1, 20),
        "estado": EstadoInscripcion.RESERVA.value,
    })

    inscripciones.modificar_inscripcion(ins_2.id, {"fechaInscripcion": date(2026, 1, 1)})
    actividades.actualizar_estados_inscripciones(act_id)

    result = actividades.listar_inscripciones_por_Actividad(act_id)
    estados = {ins["socioID"]: ins["estado"] for ins in result}
    assert estados[socio_2] == EstadoInscripcion.INSCRIT
    assert estados[socio_1] == EstadoInscripcion.RESERVA


def test_registrar_inscripcion_de_persona_no_socia(patched_session):
    act_id = _actividad(patched_session, max_alumnos=2)

    inscripciones.registrar_inscripcion({
        "socioID": None,
        "actividadID": act_id,
        "noSocioNombre": "Persona",
        "noSocioApellido1": "Externa",
        "noSocioApellido2": "Prova",
        "noSocioDni": "X999",
        "noSocioTelefono": "699111222",
        "noSocioEmail": "persona@example.com",
        "noSocioObservaciones": "Observacio",
        "fechaInscripcion": date.today(),
        "estado": EstadoInscripcion.INSCRIT.value,
    })

    [inscripcion] = actividades.listar_inscripciones_por_Actividad(act_id)
    assert inscripcion["socioID"] is None
    assert inscripcion["noSocioNombre"] == "Persona"
    assert inscripcion["noSocioApellido1"] == "Externa"
    assert inscripcion["noSocioApellido2"] == "Prova"
    assert inscripcion["noSocioDni"] == "X999"
    assert inscripcion["noSocioTelefono"] == "699111222"
    assert inscripcion["noSocioEmail"] == "persona@example.com"
    assert inscripcion["noSocioObservaciones"] == "Observacio"


def test_modificar_observaciones_de_inscripcion(patched_session):
    act_id = _actividad(patched_session, max_alumnos=2)
    socio_id = _socio("T007", "Carla")
    inscripcion = inscripciones.registrar_inscripcion({
        "socioID": socio_id,
        "actividadID": act_id,
        "fechaInscripcion": date.today(),
        "estado": EstadoInscripcion.INSCRIT.value,
    })

    inscripciones.modificar_inscripcion(inscripcion.id, {"observaciones": "Portar rebut"})

    [result] = actividades.listar_inscripciones_por_Actividad(act_id)
    assert result["observaciones"] == "Portar rebut"
