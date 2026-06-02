from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from controladores.acceso import crear_usuario, eliminar_usuario, listar_usuarios, modificar_usuario
from ui.theme import set_button_variant


class UsuariosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'usuaris")
        self.resize(760, 440)
        self._selected_user_id: int | None = None

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Usuari", "Rol", "Actiu", "Últim accés", "ID"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnHidden(4, True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Obligatòria en crear; opcional en editar")
        self.rol = QComboBox()
        self.rol.addItems(["USER", "ADMIN"])
        self.activo = QCheckBox("Actiu")
        self.activo.setChecked(True)

        form = QFormLayout()
        form.addRow("Usuari:", self.username)
        form.addRow("Contrasenya:", self.password)
        form.addRow("Rol:", self.rol)
        form.addRow("", self.activo)

        self.btn_new = QPushButton("Netejar")
        self.btn_create = QPushButton("Crear usuari")
        self.btn_save = QPushButton("Desar canvis")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_close = QPushButton("Tancar")
        self.btn_new.clicked.connect(self._clear_form)
        self.btn_create.clicked.connect(self._create)
        self.btn_save.clicked.connect(self._save)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_close.clicked.connect(self.accept)
        set_button_variant(self.btn_new, "secondary")
        set_button_variant(self.btn_create, "primary")
        set_button_variant(self.btn_save, "primary")
        set_button_variant(self.btn_delete, "danger")
        set_button_variant(self.btn_close, "secondary")

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_new)
        buttons.addWidget(self.btn_create)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_delete)
        buttons.addStretch()
        buttons.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(form)
        layout.addLayout(buttons)

        self._refresh()

    def _refresh(self):
        usuarios = listar_usuarios()
        self.table.setRowCount(len(usuarios))
        for row, usuario in enumerate(usuarios):
            values = [
                usuario["username"],
                usuario["rol"],
                "Sí" if usuario["activo"] else "No",
                usuario["last_login"].strftime("%Y-%m-%d %H:%M") if usuario["last_login"] else "",
                str(usuario["id"]),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
        self._clear_form()

    def _clear_form(self):
        self._selected_user_id = None
        self.table.clearSelection()
        self.username.clear()
        self.password.clear()
        self.rol.setCurrentText("USER")
        self.activo.setChecked(True)
        self.btn_save.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        self._selected_user_id = int(self.table.item(row, 4).text())
        self.username.setText(self.table.item(row, 0).text())
        self.password.clear()
        self.rol.setCurrentText(self.table.item(row, 1).text())
        self.activo.setChecked(self.table.item(row, 2).text() == "Sí")
        self.btn_save.setEnabled(True)
        self.btn_delete.setEnabled(True)

    def _create(self):
        username = self.username.text().strip()
        password = self.password.text()
        try:
            crear_usuario(username, password, self.rol.currentText(), self.activo.isChecked())
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut desar", str(exc))
            return

        self._refresh()

    def _save(self):
        if self._selected_user_id is None:
            QMessageBox.information(self, "Selecciona un usuari", "Selecciona un usuari de la taula per editar-lo.")
            return

        username = self.username.text().strip()
        password = self.password.text()
        try:
            kwargs = {
                "username": username,
                "rol": self.rol.currentText(),
                "activo": self.activo.isChecked(),
            }
            if password:
                kwargs["password"] = password
            modificar_usuario(self._selected_user_id, **kwargs)
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut desar", str(exc))
            return

        self._refresh()

    def _delete(self):
        if self._selected_user_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Eliminar usuari",
            "Vols eliminar l'usuari seleccionat?",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            eliminar_usuario(self._selected_user_id)
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut eliminar", str(exc))
            return
        self._refresh()
