from PySide6.QtCore import QItemSelectionModel, QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from controladores.socios import contar_socios_activos_tabla, listar_socios_activos_tabla
from ui.table_models import DictTableModel
from ui.table_utils import add_table_copy_actions, enable_table_copy
from ui.theme import set_button_variant


class SeleccionarSocioDialog(QDialog):
    PAGE_SIZE = 50

    def __init__(self, excluded_socio_ids=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir soci a l'activitat")
        self.setMinimumSize(650, 420)

        self._excluded_socio_ids = set(excluded_socio_ids or [])
        self._selected_socio = None
        self._page = 0
        self._total_socios = 0

        self.search_field = QComboBox()
        for label, key in self._search_fields():
            self.search_field.addItem(label, key)
        default_search_field = self.search_field.findData("nombre")
        if default_search_field >= 0:
            self.search_field.setCurrentIndex(default_search_field)
        self.search_field.currentIndexChanged.connect(self._queue_search)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca...")
        self.search.textChanged.connect(self._queue_search)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._refresh_table)

        self.table = QTableView()
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        enable_table_copy(self.table)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
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

        self.btn_previous_page = QPushButton("‹ Anterior")
        self.btn_previous_page.clicked.connect(self._previous_page)
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.btn_next_page = QPushButton("Següent ›")
        self.btn_next_page.clicked.connect(self._next_page)
        pagination = QHBoxLayout()
        pagination.addWidget(self.btn_previous_page)
        pagination.addWidget(self.page_label, 1)
        pagination.addWidget(self.btn_next_page)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona un soci actiu:"))
        search_bar = QHBoxLayout()
        search_bar.addWidget(self.search_field)
        search_bar.addWidget(self.search, 1)
        layout.addLayout(search_bar)
        layout.addWidget(self.table)
        layout.addLayout(pagination)
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

    def _refresh_table(self):
        self._total_socios = contar_socios_activos_tabla(
            search_field=self._selected_search_field(),
            search_text=self.search.text(),
            excluded_socio_ids=self._excluded_socio_ids,
        )
        total_pages = self._total_pages()
        if self._page >= total_pages:
            self._page = max(0, total_pages - 1)
        rows = listar_socios_activos_tabla(
            search_field=self._selected_search_field(),
            search_text=self.search.text(),
            excluded_socio_ids=self._excluded_socio_ids,
            limit=self.PAGE_SIZE,
            offset=self._page * self.PAGE_SIZE,
        )

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
        self._update_pagination()

    def _search_fields(self):
        return [
            ("Num Soci", "id"),
            ("Primer cognom", "apellido1"),
            ("Segon cognom", "apellido2"),
            ("Nom", "nombre"),
            ("DNI", "dniNie"),
            ("Telf. Movil", "telefonoMovil"),
            ("Telf. Fixe", "telefonoFijo"),
            ("Adreça", "direccion"),
            ("Grup difusió", "grupoDifusion"),
            ("Email", "email"),
        ]

    def _selected_search_field(self):
        return self.search_field.currentData() or "nombre"

    def _queue_search(self, *_args):
        self._page = 0
        self._search_timer.start()

    def _total_pages(self):
        return (self._total_socios + self.PAGE_SIZE - 1) // self.PAGE_SIZE

    def _previous_page(self):
        if self._page <= 0:
            return
        self._page -= 1
        self._refresh_table()

    def _next_page(self):
        if self._page + 1 >= self._total_pages():
            return
        self._page += 1
        self._refresh_table()

    def _update_pagination(self):
        total_pages = self._total_pages()
        if not total_pages:
            self.page_label.setText("No s'han trobat socis")
        else:
            first = self._page * self.PAGE_SIZE + 1
            last = min(first + self.PAGE_SIZE - 1, self._total_socios)
            self.page_label.setText(
                f"Socis {first}-{last} de {self._total_socios} · Pàgina {self._page + 1} de {total_pages}"
            )
        self.btn_previous_page.setEnabled(self._page > 0)
        self.btn_next_page.setEnabled(self._page + 1 < total_pages)

    def _afegir_no_soci(self):
        dialog = NoSocioDialog(self)
        if dialog.exec():
            self._selected_socio = dialog.get_data()
            super().accept()

    def _show_table_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        self.table.setCurrentIndex(index)
        self.table.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
        )
        menu = QMenu(self)
        add_table_copy_actions(menu, self.table, index)
        menu.addSeparator()
        action = menu.addAction("Seleccionar soci")
        action.triggered.connect(self.accept)
        menu.exec(self.table.viewport().mapToGlobal(pos))


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
