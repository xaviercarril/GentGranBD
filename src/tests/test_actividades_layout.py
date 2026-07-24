import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QAbstractItemView

import ui.actividad_detail as actividad_detail
import ui.tab_actividades as tab_actividades
from ui.table_models import DictTableModel


def _app():
    return QApplication.instance() or QApplication([])


def test_tabla_inscritos_encaja_y_permite_llegar_a_la_ultima_fila(monkeypatch):
    monkeypatch.setattr(tab_actividades, "listar_cursosA", lambda: [])
    monkeypatch.setattr(
        tab_actividades,
        "obtener_curso_academico_predeterminado",
        lambda cursos: None,
    )
    monkeypatch.setattr(
        tab_actividades,
        "listar_actividades_resumen",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(actividad_detail, "listar_personal", lambda: [])

    app = _app()
    tab = tab_actividades.ActividadesTab()
    tab.resize(1300, 650)
    tab.show()
    app.processEvents()

    assert tab.minimumSizeHint().height() <= 650
    assert tab.inscrits_panel.geometry().bottom() < tab._content_widget.height()

    rows = [{"id": row, "nombre": f"Persona {row}"} for row in range(40)]
    model = DictTableModel(rows, [("ID", "id"), ("Nom", "nombre")])
    table = tab.detail_actividad.inscrits_table
    table.setModel(model)
    table.hideColumn(0)

    last_index = model.index(model.rowCount() - 1, 1)
    table.scrollTo(last_index, QAbstractItemView.PositionAtBottom)
    app.processEvents()

    assert table.viewport().rect().intersects(table.visualRect(last_index))
    tab.close()
