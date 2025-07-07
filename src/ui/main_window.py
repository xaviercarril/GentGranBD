from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTableView,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

from controladores.socios import (
    listar_socios, modificar_socio, eliminar_socio, consultar_socio
)
from controladores.actividades import listar_actividades
from ui.table_models import DictTableModel
from ui.socio_dialog import SocioDialog


class MainWindow(QMainWindow):
    """Finestra principal amb pestanyes (Socis, Activitats, …)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gent Gran – Gestió")
        self.resize(900, 600)

        # ── QTabWidget ───────────────────────────────────────────
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Pestaña Socis
        self._init_tab_socis()

        # Pestaña Activitats (placeholder)
        self._init_tab_activitats()

    # ==========================================================
    #   SOCIS
    # ==========================================================
    def _init_tab_socis(self):
        self.table_socis = QTableView()
        self._refresh_socios()

        self.table_socis.doubleClicked.connect(self._editar_socio_dialog)

        btn_nou = QPushButton("Nou soci")
        btn_esborrar = QPushButton("Eliminar")

        btn_nou.clicked.connect(self._dialog_nou_socio)
        btn_esborrar.clicked.connect(self._eliminar_socio)

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addWidget(btn_nou, 0, Qt.AlignLeft)
        ly.addWidget(btn_esborrar, 0, Qt.AlignLeft)
        ly.addWidget(self.table_socis, 1)

        self.tabs.addTab(page, "Socis")

    def _refresh_socios(self):
        rows = listar_socios()
        headers = [
            ("ID", "id"),
            ("DNI/NIE", "dni_nie"),
            ("Nom", "nombre"),
            ("1r Cognom", "apellido1"),
            ("2n Cognom", "apellido2"),
            ("Adreça", "direccion"),
            ("Tel. fix", "telefonoFijo"),
            ("Mòbil", "telefonoMovil"),
            ("Email", "email"),
            ("Grup Difusió", "grupoDifusion"),
        ]
        model = DictTableModel(rows, headers)
        # model.edited.connect(self._guardar_edicio_inline)
        self.table_socis.setModel(model)
        self.table_socis.resizeColumnsToContents()

    # ---- CRUD actions ----
    def _dialog_nou_socio(self):
        dlg = SocioDialog(self)
        if dlg.exec():
            self._refresh_socios()

    def _editar_socio_dialog(self, index):
        fila = self.table_socis.model().rows[index.row()]
        socio_id = fila["id"]
        socio_complet = consultar_socio(socio_id)      # inclou bytes de foto
        dlg = SocioDialog(self, socio=socio_complet)
        if dlg.exec():
            self._refresh_socios()

    def _eliminar_socio(self):
        sel = self.table_socis.selectionModel().selectedRows()
        if not sel:
            return
        row = sel[0].row()
        socio_id = self.table_socis.model().rows[row]["id"]
        eliminar_socio(socio_id)
        self._refresh_socios()

    def _guardar_edicio_inline(self, fila: dict):
        socio_id = fila["id"]
        cambios = {
            "dni_nie": fila["dni_nie"],
            "nombre": fila["nombre"],
            "apellido1": fila["apellido1"],
            "apellido2": fila.get("apellido2", ""),
            "direccion": fila.get("direccion", ""),
            "telefonoFijo": fila.get("telefonoFijo", ""),
            "telefonoMovil": fila.get("telefono", ""),
            "email": fila.get("email", ""),
            "grupoDifusion": fila.get("grupoDifusion", ""),
        }
        try:
            modificar_socio(socio_id, cambios)
        except ValueError as e:
            QMessageBox.warning(self, "Error en guardar", str(e))
            self._refresh_socios()

    # ==========================================================
    #   ACTIVITATS (placeholder de moment)
    # ==========================================================
    def _init_tab_activitats(self):
        table_act = QTableView()
        rows = listar_actividades()
        headers = ["id", "nombre", "tipo", "max_alumnos"]
        table_act.setModel(DictTableModel(rows, headers))
        table_act.resizeColumnsToContents()

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addWidget(table_act, 1)

        self.tabs.addTab(page, "Activitats")