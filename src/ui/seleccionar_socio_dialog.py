from PySide6.QtCore import QItemSelectionModel, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from controladores.socios import listar_socios_activos
from ui.table_models import DictTableModel
from ui.theme import set_button_variant


class SeleccionarSocioDialog(QDialog):
    def __init__(self, excluded_socio_ids=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir soci a l'activitat")
        self.setMinimumSize(650, 420)

        self._excluded_socio_ids = set(excluded_socio_ids or [])
        self._selected_socio = None
        self._socios = self._load_socios()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca per nom, cognoms o DNI/NIE...")
        self.search.textChanged.connect(self._refresh_table)

        self.table = QTableView()
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.accept)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_no_soci = QPushButton("Afegir no soci")
        self.btn_no_soci.setIcon(QIcon("ui/assets/plus.svg"))
        self.btn_no_soci.setIconSize(QSize(16, 16))
        set_button_variant(self.btn_no_soci, "primary")
        self.buttons.addButton(self.btn_no_soci, QDialogButtonBox.ActionRole)
        set_button_variant(self.buttons.button(QDialogButtonBox.Ok), "primary")
        set_button_variant(self.buttons.button(QDialogButtonBox.Cancel), "secondary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.btn_no_soci.clicked.connect(self._afegir_no_soci)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona un soci actiu:"))
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(self.buttons)

        self._refresh_table()

    def selected_socio(self):
        return self._selected_socio

    def accept(self):
        row = self.table.currentIndex().row()
        model = self.table.model()
        if model is None or row < 0 or row >= len(model.rows):
            return

        self._selected_socio = model.rows[row]
        super().accept()

    def _load_socios(self):
        socios = listar_socios_activos() or []
        return [s for s in socios if s.get("id") not in self._excluded_socio_ids]

    def _refresh_table(self):
        text = self.search.text().strip().lower()
        rows = self._socios
        if text:
            rows = [
                socio
                for socio in rows
                if text in self._search_text(socio)
            ]

        headers = [
            ("ID", "id"),
            ("DNI/NIE", "dniNie"),
            ("Nom", "nombre"),
            ("Primer cognom", "apellido1"),
            ("Segon cognom", "apellido2"),
        ]
        model = DictTableModel(rows, headers)
        self.table.setModel(model)
        self.table.hideColumn(0)
        self.table.resizeColumnsToContents()

        if rows:
            index = model.index(0, 0)
            self.table.selectionModel().setCurrentIndex(
                index,
                QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows,
            )

    def _search_text(self, socio):
        values = [
            socio.get("dniNie"),
            socio.get("nombre"),
            socio.get("apellido1"),
            socio.get("apellido2"),
        ]
        return " ".join(str(v).lower() for v in values if v)

    def _afegir_no_soci(self):
        dialog = NoSocioDialog(self)
        if dialog.exec():
            self._selected_socio = dialog.get_data()
            super().accept()


class NoSocioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir persona no sòcia")

        self.nombre = QLineEdit()
        self.apellido1 = QLineEdit()
        self.apellido2 = QLineEdit()
        self.dni = QLineEdit()
        self.telefono = QLineEdit()
        self.email = QLineEdit()
        self.observaciones = QLineEdit()

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Primer Cognom:", self.apellido1)
        form.addRow("Segon Cognom:", self.apellido2)
        form.addRow("DNI:", self.dni)
        form.addRow("Telefon:", self.telefono)
        form.addRow("Email:", self.email)
        form.addRow("Observacions:", self.observaciones)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        set_button_variant(self.buttons.button(QDialogButtonBox.Ok), "primary")
        set_button_variant(self.buttons.button(QDialogButtonBox.Cancel), "secondary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def accept(self):
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return
        super().accept()

    def get_data(self):
        return {
            "id": None,
            "es_socio": False,
            "noSocioNombre": self.nombre.text().strip(),
            "noSocioApellido1": self.apellido1.text().strip() or None,
            "noSocioApellido2": self.apellido2.text().strip() or None,
            "noSocioDni": self.dni.text().strip() or None,
            "noSocioTelefono": self.telefono.text().strip() or None,
            "noSocioEmail": self.email.text().strip() or None,
            "noSocioObservaciones": self.observaciones.text().strip() or None,
        }
