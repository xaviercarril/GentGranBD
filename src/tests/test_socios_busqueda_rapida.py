import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QWidget

import controladores.socios as socios
from models import Base, Socio
import ui.tab_socios as tab_socios


@pytest.fixture()
def patched_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(socios, "SessionLocal", Session)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyDetailWidget(QWidget):
    saved = Signal(int)

    def confirm_pending_changes(self, emit_saved=True):
        return True

    def has_pending_changes(self):
        return False

    def load(self, socio_id):
        self.loaded_socio_id = socio_id


def _row(
    socio_id=1,
    nombre="Maria",
    apellido1="Garcia",
    apellido2="Soler",
    dni="12345678A",
    movil="600111222",
    fijo="936001122",
    email="maria@example.test",
):
    return {
        "id": socio_id,
        "apellido1": apellido1,
        "apellido2": apellido2,
        "nombre": nombre,
        "dniNie": dni,
        "telefonoMovil": movil,
        "telefonoFijo": fijo,
        "direccion": "Carrer Major 1",
        "fechaAlta": date(2026, 1, 15),
        "fechaNacimiento": date(1950, 5, 20),
        "grupoDifusion": "General",
        "email": email,
    }


def _set_search_field(widget, field_key):
    index = widget._search_field_combo.findData(field_key)
    assert index >= 0
    widget._search_field_combo.setCurrentIndex(index)
    widget._search_timer.stop()


def test_listar_socios_tabla_devuelve_campos_ligeros(patched_session):
    patched_session.add(
        Socio(
            dniNie="12345678A",
            nombre="Maria",
            apellido1="Garcia",
            apellido2="Soler",
            direccion="Carrer Major 1",
            telefonoFijo="936001122",
            telefonoMovil="600111222",
            email="maria@example.test",
            grupoDifusion="General",
            fechaNacimiento=date(1950, 5, 20),
            fechaAlta=date(2026, 1, 15),
            observaciones="No debe ir a la tabla",
            foto=b"foto",
        )
    )
    patched_session.commit()

    rows = socios.listar_socios_tabla()

    assert rows == [_row()]
    assert "foto" not in rows[0]
    assert "observaciones" not in rows[0]


def test_busqueda_en_socios_no_recarga_base_de_datos(monkeypatch, qapp):
    calls = 0

    def fake_listar_socios_tabla():
        nonlocal calls
        calls += 1
        return [
            _row(),
            _row(
                socio_id=2,
                nombre="Joan",
                apellido1="Puig",
                dni="87654321B",
                email="joan@example.test",
            ),
        ]

    monkeypatch.setattr(tab_socios, "listar_socios_tabla", fake_listar_socios_tabla)
    monkeypatch.setattr(tab_socios, "SocioDetailWidget", DummyDetailWidget)

    widget = tab_socios.SociosTab()
    assert calls == 1

    widget._search_box.setText("maria")
    widget._search_timer.stop()
    widget._apply_current_filter()

    assert calls == 1
    assert [row["id"] for row in widget.table_socis.model().rows] == [1]


def test_busqueda_en_socios_filtra_solo_por_campo_seleccionado(monkeypatch, qapp):
    rows = [
        _row(),
        _row(
            socio_id=2,
            nombre="Joan",
            apellido1="Puig",
            apellido2="Vila",
            dni="87654321B",
            movil="611222333",
            fijo="937778899",
            email="joan@example.test",
        ),
    ]

    monkeypatch.setattr(tab_socios, "listar_socios_tabla", lambda: rows)
    monkeypatch.setattr(tab_socios, "SocioDetailWidget", DummyDetailWidget)

    widget = tab_socios.SociosTab()

    _set_search_field(widget, "nombre")
    assert [row["id"] for row in widget._filter_rows("MARIA")] == [1]
    assert widget._filter_rows("garcia") == []

    _set_search_field(widget, "apellido1")
    assert [row["id"] for row in widget._filter_rows("puig")] == [2]

    _set_search_field(widget, "dniNie")
    assert [row["id"] for row in widget._filter_rows("87654321b")] == [2]

    _set_search_field(widget, "telefonoMovil")
    assert [row["id"] for row in widget._filter_rows("611222333")] == [2]

    _set_search_field(widget, "email")
    assert [row["id"] for row in widget._filter_rows("joan@example")] == [2]
