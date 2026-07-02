import json
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from audit import REALTIME_CHANNEL, _notify_realtime_change, install_audit_listeners, set_current_user
from models import Auditoria, Base, Socio


def test_auditoria_registra_creacion_modificacion_y_borrado():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    install_audit_listeners()
    set_current_user("xavier")

    with Session() as db:
        socio = Socio(dniNie="12345678X", nombre="Pere", fechaAlta=date.today())
        db.add(socio)
        db.commit()
        socio_id = socio.id

        socio.nombre = "Pere Modificat"
        db.commit()

        db.delete(socio)
        db.commit()

    with Session() as db:
        rows = db.scalars(select(Auditoria).order_by(Auditoria.id)).all()

    assert [row.accion for row in rows] == ["CREATE", "UPDATE", "DELETE"]
    assert {row.usuario_app for row in rows} == {"xavier"}
    assert {row.tabla for row in rows} == {"socios"}
    assert {row.registro_id for row in rows} == {str(socio_id)}

    engine.dispose()


class _FakeDialect:
    def __init__(self, name):
        self.name = name


class _FakeConnection:
    def __init__(self, dialect_name):
        self.dialect = _FakeDialect(dialect_name)
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params))


def test_realtime_notify_solo_se_emite_en_postgresql():
    sqlite_connection = _FakeConnection("sqlite")
    _notify_realtime_change(sqlite_connection, "socios", "1", "UPDATE", "xavier")
    assert sqlite_connection.calls == []

    postgres_connection = _FakeConnection("postgresql")
    _notify_realtime_change(postgres_connection, "socios", "1", "UPDATE", "xavier")

    assert len(postgres_connection.calls) == 1
    statement, params = postgres_connection.calls[0]
    assert "pg_notify" in str(statement)
    assert params["channel"] == REALTIME_CHANNEL
    assert json.loads(params["payload"]) == {
        "tabla": "socios",
        "registro_id": "1",
        "accion": "UPDATE",
        "usuario_app": "xavier",
    }
