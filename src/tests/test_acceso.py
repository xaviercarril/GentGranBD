import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import controladores.acceso as acceso
import database
from models import Base, Usuario


@pytest.fixture()
def auth_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(acceso, "SessionLocal", Session)
    yield Session
    engine.dispose()


def test_bootstrap_admin_crea_admin_inicial(auth_session):
    assert acceso.bootstrap_admin_si_no_hay_usuarios() is True

    with auth_session() as db:
        usuario = db.query(Usuario).filter_by(username="admin").one()
        assert usuario.rol.value == "ADMIN"
        assert usuario.password_hash != "admin"
        assert acceso.verify_password("admin", usuario.password_hash)


def test_bootstrap_admin_no_duplica_si_ya_hay_usuarios(auth_session):
    acceso.crear_usuario("operador", "secret", "USER")

    assert acceso.bootstrap_admin_si_no_hay_usuarios() is False

    with auth_session() as db:
        assert db.query(Usuario).count() == 1


def test_autenticar_usuario_correcto_e_incorrecto(auth_session):
    acceso.bootstrap_admin_si_no_hay_usuarios()

    usuario = acceso.autenticar_usuario("admin", "admin")
    assert usuario["username"] == "admin"
    assert usuario["rol"] == "ADMIN"

    with pytest.raises(ValueError):
        acceso.autenticar_usuario("admin", "mal")


def test_usuario_inactivo_no_puede_entrar(auth_session):
    acceso.crear_usuario("operador", "secret", "USER", activo=False)

    with pytest.raises(ValueError):
        acceso.autenticar_usuario("operador", "secret")


def test_admin_gestiona_usuario_normal_y_password(auth_session):
    usuario = acceso.crear_usuario("operador", "secret", "USER")

    actualizado = acceso.modificar_usuario(
        usuario["id"],
        username="operador2",
        rol="ADMIN",
        activo=True,
        password="nuevo",
    )
    assert actualizado["username"] == "operador2"
    assert actualizado["rol"] == "ADMIN"

    assert acceso.autenticar_usuario("operador2", "nuevo")["username"] == "operador2"


def test_no_se_puede_eliminar_ni_desactivar_ultimo_admin(auth_session):
    acceso.bootstrap_admin_si_no_hay_usuarios()
    admin = acceso.autenticar_usuario("admin", "admin")

    with pytest.raises(ValueError):
        acceso.modificar_usuario(admin["id"], activo=False)

    with pytest.raises(ValueError):
        acceso.eliminar_usuario(admin["id"])


def test_ensure_schema_updates_crea_tabla_usuarios_en_sqlite_legacy(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE socios (id INTEGER PRIMARY KEY, dniNie VARCHAR(15) NOT NULL, nombre VARCHAR(50) NOT NULL, fechaAlta DATE NOT NULL)"))

    monkeypatch.setattr(database, "engine", engine)
    database.ensure_schema_updates()

    assert "usuarios" in inspect(engine).get_table_names()
    engine.dispose()


def test_set_database_url_reconfigura_sessionlocal_compartido(tmp_path):
    original_url = database.DATABASE_URL
    db_path = tmp_path / "auth.db"
    try:
        database.set_database_url(f"sqlite:///{db_path.as_posix()}")
        Base.metadata.create_all(bind=database.engine)

        with database.SessionLocal() as db:
            db.add(Usuario(username="admin", password_hash=acceso.hash_password("admin"), rol="ADMIN"))
            db.commit()

        assert acceso.autenticar_usuario("admin", "admin")["username"] == "admin"
    finally:
        database.set_database_url(original_url)
