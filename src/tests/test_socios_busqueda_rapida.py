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
import ui.seleccionar_socio_dialog as seleccionar_socio_dialog


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


def test_listar_socios_tabla_filtra_y_limita_en_base_de_datos(patched_session):
    patched_session.add_all(
        [
            Socio(dniNie="12345678A", nombre="Maria", apellido1="Garcia", fechaAlta=date(2026, 1, 15)),
            Socio(dniNie="87654321B", nombre="Joan", apellido1="Puig", fechaAlta=date(2026, 1, 16)),
            Socio(dniNie="11111111C", nombre="Marta", apellido1="Garcia", fechaAlta=date(2026, 1, 17)),
        ]
    )
    patched_session.commit()

    rows = socios.listar_socios_tabla(
        search_field="apellido1",
        search_text="garcia",
        limit=1,
        order_by="id",
        descending=True,
    )

    assert [row["nombre"] for row in rows] == ["Marta"]


def test_listar_socios_activos_tabla_filtra_excluye_y_pagina(patched_session):
    patched_session.add_all(
        [
            Socio(dniNie="12345678A", nombre="Maria", apellido1="Garcia", fechaAlta=date(2026, 1, 15)),
            Socio(dniNie="87654321B", nombre="Joan", apellido1="Puig", fechaAlta=date(2026, 1, 16)),
            Socio(dniNie="11111111C", nombre="Marta", apellido1="Garcia", fechaAlta=date(2026, 1, 17)),
            Socio(dniNie="22222222D", nombre="Maria", apellido1="Baixa", fechaAlta=date(2026, 1, 18), fechaBaja=date(2026, 2, 1)),
        ]
    )
    patched_session.commit()

    assert socios.contar_socios_activos_tabla(search_field="nombre", search_text="maria") == 1
    rows = socios.listar_socios_activos_tabla(limit=1, offset=1)
    assert [row["nombre"] for row in rows] == ["Joan"]

    rows = socios.listar_socios_activos_tabla(excluded_socio_ids=[1])
    assert [row["id"] for row in rows] == [2, 3]


def test_selector_socios_consulta_por_paginas_y_campo(monkeypatch, qapp):
    calls = []

    def fake_count(**kwargs):
        calls.append(("count", kwargs))
        return 51

    def fake_list(**kwargs):
        calls.append(("list", kwargs))
        return [_row(socio_id=1)]

    monkeypatch.setattr(seleccionar_socio_dialog, "contar_socios_activos_tabla", fake_count)
    monkeypatch.setattr(seleccionar_socio_dialog, "listar_socios_activos_tabla", fake_list)

    dialog = seleccionar_socio_dialog.SeleccionarSocioDialog(excluded_socio_ids=[8])
    assert calls[-1] == (
        "list",
        {
            "search_field": "nombre",
            "search_text": "",
            "excluded_socio_ids": {8},
            "limit": 50,
            "offset": 0,
        },
    )
    assert dialog.btn_next_page.isEnabled()

    dialog.search.setText("maria")
    dialog._search_timer.stop()
    dialog._refresh_table()
    assert calls[-1][1]["search_text"] == "maria"

    dialog._next_page()
    assert calls[-1][1]["offset"] == 50


def test_busqueda_en_socios_consulta_remota_con_parametros(monkeypatch, qapp):
    calls = []

    def fake_listar_socios_tabla(**kwargs):
        calls.append(kwargs)
        if kwargs.get("search_text"):
            return [_row()]
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
    assert len(calls) == 1
    assert "limit" not in calls[-1]
    assert "offset" not in calls[-1]

    widget._search_box.setText("maria")
    widget._search_timer.stop()
    widget._apply_current_filter()

    assert len(calls) == 2
    assert calls[-1]["search_field"] == "nombre"
    assert calls[-1]["search_text"] == "maria"
    assert "offset" not in calls[-1]
    assert [row["id"] for row in widget.table_socis.model().rows] == [1]


def test_ordenacion_en_socios_consulta_remota_sin_paginacion(monkeypatch, qapp):
    calls = []

    def fake_listar_socios_tabla(**kwargs):
        calls.append(kwargs)
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
    assert calls[-1]["order_by"] == "id"
    assert "limit" not in calls[-1]
    assert "offset" not in calls[-1]

    widget._sort_by_header(1)

    assert calls[-1]["order_by"] == "apellido1"
    assert calls[-1]["descending"] is False
    assert "limit" not in calls[-1]
    assert "offset" not in calls[-1]
