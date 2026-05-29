from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

import database
import controladores.pagos as pagos
import controladores.inscripcion_socio as inscripciones
from models import Base, EstadoInscripcion, EstadoPago, InscripcionSocio, Pago


@pytest.fixture()
def patched_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(pagos, "SessionLocal", Session)
    monkeypatch.setattr(inscripciones, "SessionLocal", Session)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_modificar_pago_actualiza_campos_editables(patched_session):
    pago = Pago(
        socioID=1,
        actividadID=1,
        fecha=date(2026, 1, 10),
        importe=20,
        estado=EstadoPago.PENDENT,
        observaciones="Inicial",
    )
    patched_session.add(pago)
    patched_session.commit()
    pago_id = pago.id

    pagos.modificar_pago(
        pago_id,
        {
            "fecha_pago": date(2026, 1, 20),
            "importe": 35.5,
            "estado": "PAGAT",
            "observaciones": "Pagat en efectiu",
        },
    )

    patched_session.expire_all()
    actualizado = patched_session.get(Pago, pago_id)
    assert actualizado.fecha == date(2026, 1, 20)
    assert float(actualizado.importe) == 35.5
    assert actualizado.estado == EstadoPago.PAGAT
    assert actualizado.observaciones == "Pagat en efectiu"


def test_pago_de_persona_no_socia_se_lista_por_inscripcion(patched_session):
    inscripcion = InscripcionSocio(
        socioID=None,
        actividadID=1,
        noSocioNombre="Persona",
        noSocioApellido1="Externa",
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
    )
    patched_session.add(inscripcion)
    patched_session.commit()

    pago_id = pagos.registrar_pago(
        {
            "socioID": None,
            "actividadID": 1,
            "inscripcionID": inscripcion.id,
            "fecha_pago": date.today(),
            "importe": 42,
            "estado": "PAGAT",
        }
    )

    result = inscripciones.listar_pagos_por_InscripcionSocio(inscripcion.id)

    assert [pago["id"] for pago in result] == [pago_id]
    assert result[0]["estado"] == EstadoPago.PAGAT.value


def test_migracion_sqlite_pagos_permite_socio_null_y_anade_inscripcion_id(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE socios (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                """
                CREATE TABLE inscripciones (
                    id INTEGER PRIMARY KEY,
                    "socioID" INTEGER,
                    "actividadID" INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE matricula_pagos (
                    id INTEGER PRIMARY KEY,
                    "socioID" INTEGER NOT NULL,
                    "actividadID" INTEGER NOT NULL,
                    fecha DATE NOT NULL,
                    importe DECIMAL(10, 2) NOT NULL,
                    estado VARCHAR(7) NOT NULL,
                    observaciones TEXT
                )
                """
            )
        )

    monkeypatch.setattr(database, "engine", engine)
    database.ensure_schema_updates()

    with engine.connect() as conn:
        columns = conn.execute(text("PRAGMA table_info(matricula_pagos)")).mappings().all()
        by_name = {column["name"]: column for column in columns}

    assert "inscripcionID" in by_name
    assert by_name["socioID"]["notnull"] == 0
