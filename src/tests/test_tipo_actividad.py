from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import controladores.actividades as actividades
import controladores.curso_academico as cursos_academicos
from database import ensure_schema_updates
from models import Base, CursoAcademico, TipoActividadEnum


@pytest.fixture()
def patched_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(actividades, "SessionLocal", Session)
    monkeypatch.setattr(cursos_academicos, "SessionLocal", Session)
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


def test_registrar_actividad_sin_tipo_crea_curs(patched_session):
    act_id = actividades.registrar_actividad({
        "nombre": "Gimnasia",
        "cursoAcademico_id": _curso(patched_session),
    })

    actividad = actividades.consultar_actividad(act_id)

    assert actividad["tipo"] == TipoActividadEnum.CURS


def test_filtra_actividades_por_tipo_y_curso_academico(patched_session):
    curso_id = _curso(patched_session)
    curso_act_id = actividades.registrar_actividad({
        "nombre": "Anglès",
        "tipo": "CURS",
        "cursoAcademico_id": curso_id,
    })
    viaje_act_id = actividades.registrar_actividad({
        "nombre": "Tarragona",
        "tipo": "VIATGE",
        "cursoAcademico_id": curso_id,
    })

    cursos = actividades.listar_actividades(tipo="CURS")
    viajes = cursos_academicos.listar_actividades_por_CursoAcademico(curso_id, tipo="VIATGE")

    assert [actividad["id"] for actividad in cursos] == [curso_act_id]
    assert [actividad["id"] for actividad in viajes] == [viaje_act_id]


def test_ensure_schema_updates_rellena_tipo_en_actividades_legacy(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE socios (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE actividades (id INTEGER PRIMARY KEY, nombre VARCHAR(100) NOT NULL)"))
        conn.execute(text("INSERT INTO actividades (id, nombre) VALUES (1, 'Legacy')"))

    monkeypatch.setattr("database.engine", engine)
    ensure_schema_updates()

    with engine.connect() as conn:
        tipo = conn.execute(text("SELECT tipo FROM actividades WHERE id = 1")).scalar_one()

    assert tipo == "CURS"
