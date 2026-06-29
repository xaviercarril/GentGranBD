from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import controladores.curso_academico as cursos
from models import Actividad, Base, CursoAcademico, InscripcionSocio, Trimestre, TrimestreEnum, TipoActividadEnum


@pytest.fixture()
def patched_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(cursos, "SessionLocal", Session)
    yield Session
    engine.dispose()


def _crear_curso_origen(Session):
    with Session() as db:
        curso = CursoAcademico(
            nombre="2025-2026",
            fechaInicio=date(2025, 9, 1),
            fechaFin=date(2026, 6, 30),
        )
        db.add(curso)
        db.flush()
        db.add(Trimestre(
            nombre=TrimestreEnum.T1,
            fechaInicio=date(2025, 9, 1),
            fechaFin=date(2025, 11, 30),
            cursoAcademicoID=curso.id,
        ))
        actividad = Actividad(
            nombre="Gimnàstica",
            tipo=TipoActividadEnum.CURS,
            descripcion="Activitat de prova",
            numMaxAlumnos=20,
            cursoAcademicoID=curso.id,
            precio_matricula=15,
        )
        db.add(actividad)
        db.commit()
        return curso.id


def test_duplica_curso_con_trimestres_y_actividades_sin_inscripciones(patched_session):
    Session = patched_session
    curso_id = _crear_curso_origen(Session)

    nuevo_id = cursos.duplicar_cursoA(curso_id, "2026-2027")

    with Session() as db:
        nuevo = db.get(CursoAcademico, nuevo_id)
        assert nuevo.nombre == "2026-2027"
        assert nuevo.fechaInicio == date(2025, 9, 1)
        assert nuevo.fechaFin == date(2026, 6, 30)

        trimestres = db.query(Trimestre).filter_by(cursoAcademicoID=nuevo_id).all()
        actividades = db.query(Actividad).filter_by(cursoAcademicoID=nuevo_id).all()
        assert [(t.nombre, t.fechaInicio, t.fechaFin) for t in trimestres] == [
            (TrimestreEnum.T1, date(2025, 9, 1), date(2025, 11, 30))
        ]
        assert [(a.nombre, a.tipo, a.numMaxAlumnos) for a in actividades] == [
            ("Gimnàstica", TipoActividadEnum.CURS, 20)
        ]
        assert db.query(InscripcionSocio).filter_by(actividadID=actividades[0].id).count() == 0


def test_duplica_curso_sumando_un_anio_a_curso_y_trimestres(patched_session):
    Session = patched_session
    curso_id = _crear_curso_origen(Session)

    nuevo_id = cursos.duplicar_cursoA(curso_id, "2026-2027", sumar_anio=True)

    with Session() as db:
        nuevo = db.get(CursoAcademico, nuevo_id)
        assert nuevo.fechaInicio == date(2026, 9, 1)
        assert nuevo.fechaFin == date(2027, 6, 30)

        trimestres = db.query(Trimestre).filter_by(cursoAcademicoID=nuevo_id).all()
        assert [(t.nombre, t.fechaInicio, t.fechaFin) for t in trimestres] == [
            (TrimestreEnum.T1, date(2026, 9, 1), date(2026, 11, 30))
        ]


def test_rechaza_nombre_vacio_repetido_o_igual_al_original(patched_session):
    Session = patched_session
    curso_id = _crear_curso_origen(Session)
    with Session() as db:
        db.add(CursoAcademico(
            nombre="Nom existent",
            fechaInicio=date(2024, 9, 1),
            fechaFin=date(2025, 6, 30),
        ))
        db.commit()

    for nombre in ("", "2025-2026", "Nom existent"):
        with pytest.raises(ValueError):
            cursos.duplicar_cursoA(curso_id, nombre)
