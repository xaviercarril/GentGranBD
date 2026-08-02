import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QAbstractItemView
from PySide6.QtCore import Qt

import ui.actividad_detail as actividad_detail
import ui.tab_actividades as tab_actividades
import ui.asistencia_dialog as asistencia_dialog


def _app():
    return QApplication.instance() or QApplication([])


def test_inscripciones_salen_en_dialogo_y_permiten_llegar_a_la_ultima_fila(monkeypatch):
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
    assert tab.detail_actividad.inscrits_panel.isHidden()
    assert abs(tab.detail_actividad.geometry().top() - tab.table_activitats.geometry().top()) <= 1
    assert tab.detail_actividad.width() < tab.table_activitats.width() * 0.5

    rows = [
        {
            "id": row,
            "socioID": row,
            "nombre": f"Persona {row}",
            "apellido1": "Prova",
            "apellido2": "",
            "fechaInscripcion": None,
            "estado": "INSCRIT",
            "observaciones": "",
        }
        for row in range(40)
    ]
    monkeypatch.setattr(
        actividad_detail,
        "consultar_actividad",
        lambda _actividad_id: {
            "id": 7,
            "nombre": "Gimnàstica",
            "tipo": "CURS",
            "cursoAcademico_id": 3,
            "numMaxAlumnos": 50,
            "precio_matricula": 10,
            "descripcion": "",
            "personalID": None,
        },
    )
    monkeypatch.setattr(
        actividad_detail,
        "listar_inscripciones_detalle_por_Actividad",
        lambda _actividad_id: rows,
    )
    monkeypatch.setattr(
        actividad_detail,
        "consultar_socio",
        lambda _socio_id: {"foto": None},
    )

    dialog = actividad_detail.InscripcionesActividadDialog(7, tab)
    dialog.show()
    app.processEvents()
    table = dialog.inscripciones.inscrits_table

    assert dialog.inscripciones.details_panel.isHidden()
    assert dialog.inscripciones.inscrits_panel.isVisible()
    assert dialog.inscripciones.socio_preview.isVisible()
    assert dialog.inscripciones.btn_asistencia.text() == "Assistència"
    assert not dialog.inscripciones.btn_asistencia.isHidden()
    assert not dialog.inscripciones.btn_exportar_excel.isHidden()

    dialog.inscripciones.set_tipo_actividad("VIATGE")
    assert dialog.inscripciones.btn_asistencia.isHidden()
    assert not dialog.inscripciones.btn_exportar_excel.isHidden()
    dialog.inscripciones.set_tipo_actividad("CURS")
    assert not dialog.inscripciones.btn_asistencia.isHidden()
    assert dialog.inscripciones.btn_asistencia.isEnabled()
    assert dialog.inscripciones.btn_asistencia.toolTip() == "Obrir el control d'assistència del curs"

    asistencia_abierta = []

    class FakeAsistenciaDialog:
        def __init__(self, actividad_id, curso_id, parent):
            asistencia_abierta.append((actividad_id, curso_id, parent))

        def exec(self):
            return 0

    monkeypatch.setattr(asistencia_dialog, "AsistenciaDialog", FakeAsistenciaDialog)
    dialog.inscripciones.btn_asistencia.click()
    assert asistencia_abierta == [(7, 3, dialog.inscripciones)]

    model = table.model()
    last_index = model.index(model.rowCount() - 1, 1)
    table.scrollTo(last_index, QAbstractItemView.PositionAtBottom)
    app.processEvents()

    assert table.viewport().rect().intersects(table.visualRect(last_index))

    sorted_model = actividad_detail.InscripcionesActividadTableModel(
        [
            {"id": 1, "apellido2": "Zuluaga"},
            {"id": 2, "apellido2": "Alonso"},
            {"id": 3, "apellido2": "Martí"},
        ],
        [("ID", "id"), ("Segon Cognom", "apellido2")],
        lambda *_args: None,
    )
    sorted_model.sort(1, Qt.AscendingOrder)
    table.setModel(sorted_model)
    assert dialog.inscripciones._current_inscription_ids() == [2, 3, 1]

    assert not tab.btn_exportar_excel_cursos.isHidden()
    assert tab.btn_puntos_recogida.isHidden()
    tab.subtabs.setCurrentIndex(1)
    app.processEvents()
    assert tab.btn_exportar_excel_cursos.isHidden()
    assert not tab.btn_puntos_recogida.isHidden()
    assert not tab.btn_puntos_recogida.icon().isNull()

    catalogos_abiertos = []

    class FakePuntosRecogidaDialog:
        def __init__(self, parent):
            catalogos_abiertos.append(parent)

        def exec(self):
            return 0

    monkeypatch.setattr(tab_actividades, "PuntosRecogidaDialog", FakePuntosRecogidaDialog)
    tab.btn_puntos_recogida.click()
    assert catalogos_abiertos == [tab]
    dialog.close()
    tab.close()
