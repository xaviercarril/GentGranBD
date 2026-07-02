import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from controladores.acceso import (
    cambiar_password_usuario,
    crear_usuario,
    eliminar_usuario,
    listar_auditoria_usuario,
    listar_usuarios,
    modificar_usuario,
)
from ui.table_utils import enable_table_copy
from ui.theme import set_button_variant


class UsuarioEditDialog(QDialog):
    def __init__(self, parent=None, usuario: dict | None = None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("Editar usuari" if usuario else "Crear usuari")
        self.setMinimumWidth(420)

        self.username = QLineEdit((usuario or {}).get("username", ""))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password_repeat = QLineEdit()
        self.password_repeat.setEchoMode(QLineEdit.Password)
        if usuario:
            self.password.setPlaceholderText("Deixa-la buida per mantenir-la")
            self.password_repeat.setPlaceholderText("Repeteix-la només si la canvies")
        else:
            self.password.setPlaceholderText("Obligatòria")
            self.password_repeat.setPlaceholderText("Obligatòria")

        self.rol = QComboBox()
        self.rol.addItems(["USER", "ADMIN"])
        self.rol.setCurrentText((usuario or {}).get("rol", "USER"))
        self.activo = QCheckBox("Actiu")
        self.activo.setChecked((usuario or {}).get("activo", True))

        form = QFormLayout()
        form.addRow("Usuari:", self.username)
        form.addRow("Contrasenya:", self.password)
        form.addRow("Repeteix contrasenya:", self.password_repeat)
        form.addRow("Rol:", self.rol)
        form.addRow("", self.activo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        save_button = self.buttons.button(QDialogButtonBox.Save)
        cancel_button = self.buttons.button(QDialogButtonBox.Cancel)
        if save_button:
            save_button.setText("Desar")
            set_button_variant(save_button, "primary")
        if cancel_button:
            cancel_button.setText("Cancel·lar")
            set_button_variant(cancel_button, "secondary")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def data(self) -> dict:
        values = {
            "username": self.username.text().strip(),
            "rol": self.rol.currentText(),
            "activo": self.activo.isChecked(),
        }
        password = self.password.text()
        if password:
            values["password"] = password
        return values

    def _accept(self):
        username = self.username.text().strip()
        password = self.password.text()
        password_repeat = self.password_repeat.text()
        if not username:
            QMessageBox.warning(self, "Dades incompletes", "El nom d'usuari és obligatori.")
            return
        if not self.usuario and not password:
            QMessageBox.warning(self, "Dades incompletes", "La contrasenya és obligatòria.")
            return
        if password or password_repeat:
            if password != password_repeat:
                QMessageBox.warning(self, "Contrasenya", "Les contrasenyes no coincideixen.")
                return
        self.accept()


class CambiarPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Canviar contrasenya")
        self.setMinimumWidth(420)

        self.password_actual = QLineEdit()
        self.password_actual.setEchoMode(QLineEdit.Password)
        self.password_nueva = QLineEdit()
        self.password_nueva.setEchoMode(QLineEdit.Password)
        self.password_repeat = QLineEdit()
        self.password_repeat.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Contrasenya actual:", self.password_actual)
        form.addRow("Nova contrasenya:", self.password_nueva)
        form.addRow("Repeteix nova contrasenya:", self.password_repeat)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        save_button = self.buttons.button(QDialogButtonBox.Save)
        cancel_button = self.buttons.button(QDialogButtonBox.Cancel)
        if save_button:
            save_button.setText("Canviar")
            set_button_variant(save_button, "primary")
        if cancel_button:
            cancel_button.setText("Cancel·lar")
            set_button_variant(cancel_button, "secondary")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def passwords(self) -> tuple[str, str]:
        return self.password_actual.text(), self.password_nueva.text()

    def _accept(self):
        if not self.password_actual.text():
            QMessageBox.warning(self, "Dades incompletes", "Indica la contrasenya actual.")
            return
        if not self.password_nueva.text():
            QMessageBox.warning(self, "Dades incompletes", "Indica la nova contrasenya.")
            return
        if self.password_nueva.text() != self.password_repeat.text():
            QMessageBox.warning(self, "Contrasenya", "Les contrasenyes no coincideixen.")
            return
        self.accept()


class UsuarioAuditoriaDialog(QDialog):
    def __init__(self, parent=None, username: str = "", rows: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Auditoria de {username}")
        self.resize(920, 520)
        rows = rows or []

        label = QLabel(f"{len(rows)} registres d'auditoria per a l'usuari {username}")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Data", "Acció", "Taula", "Registre", "Detall"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        enable_table_copy(self.table)

        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(130)

        close_button = QPushButton("Tancar")
        close_button.clicked.connect(self.accept)
        set_button_variant(close_button, "secondary")

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(self.table)
        layout.addWidget(self.detail)
        layout.addLayout(buttons)

        self._load(rows)
        self.table.itemSelectionChanged.connect(self._update_detail)
        if rows:
            self.table.selectRow(0)

    def _load(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            fecha = row["fecha_hora"].strftime("%Y-%m-%d %H:%M:%S") if row["fecha_hora"] else ""
            detalle = self._format_detail(row.get("detalle") or "")
            values = [
                fecha,
                row.get("accion") or "",
                row.get("tabla") or "",
                row.get("registro_id") or "",
                detalle,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == 4:
                    item.setData(Qt.UserRole, detalle)
                self.table.setItem(row_index, col, item)

    def _update_detail(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            self.detail.clear()
            return
        row = selected[0].row()
        detail_item = self.table.item(row, 4)
        self.detail.setPlainText(detail_item.data(Qt.UserRole) if detail_item else "")

    def _format_detail(self, detail: str) -> str:
        try:
            return json.dumps(json.loads(detail), ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return detail


class UsuariosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'usuaris")
        self.resize(820, 440)
        self._usuarios: list[dict] = []
        self._selected_user_id: int | None = None

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Usuari", "Rol", "Actiu", "Últim accés", "ID"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        enable_table_copy(self.table)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnHidden(4, True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._show_audit_for_item)

        self.btn_create = QPushButton("Crear usuari")
        self.btn_edit = QPushButton("Editar")
        self.btn_audit = QPushButton("Veure auditoria")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_close = QPushButton("Tancar")
        self.btn_create.clicked.connect(self._create)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_audit.clicked.connect(self._show_selected_audit)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_close.clicked.connect(self.accept)
        set_button_variant(self.btn_create, "primary")
        set_button_variant(self.btn_edit, "secondary")
        set_button_variant(self.btn_audit, "secondary")
        set_button_variant(self.btn_delete, "danger")
        set_button_variant(self.btn_close, "secondary")

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_create)
        buttons.addWidget(self.btn_edit)
        buttons.addWidget(self.btn_audit)
        buttons.addWidget(self.btn_delete)
        buttons.addStretch()
        buttons.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        self._refresh()

    def _refresh(self):
        self._usuarios = listar_usuarios()
        self.table.setRowCount(len(self._usuarios))
        for row, usuario in enumerate(self._usuarios):
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
        self._clear_selection()

    def _clear_selection(self):
        self._selected_user_id = None
        self.table.clearSelection()
        self.btn_edit.setEnabled(False)
        self.btn_audit.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self._selected_user_id = None
            self.btn_edit.setEnabled(False)
            self.btn_audit.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return
        row = selected[0].row()
        self._selected_user_id = int(self.table.item(row, 4).text())
        self.btn_edit.setEnabled(True)
        self.btn_audit.setEnabled(True)
        self.btn_delete.setEnabled(True)

    def _selected_usuario(self) -> dict | None:
        if self._selected_user_id is None:
            return None
        for usuario in self._usuarios:
            if usuario["id"] == self._selected_user_id:
                return usuario
        return None

    def _create(self):
        dlg = UsuarioEditDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        values = dlg.data()
        try:
            crear_usuario(values["username"], values["password"], values["rol"], values["activo"])
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut desar", str(exc))
            return
        self._refresh()

    def _edit(self):
        usuario = self._selected_usuario()
        if not usuario:
            QMessageBox.information(self, "Selecciona un usuari", "Selecciona un usuari de la taula per editar-lo.")
            return

        dlg = UsuarioEditDialog(self, usuario)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            modificar_usuario(usuario["id"], **dlg.data())
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut desar", str(exc))
            return
        self._refresh()

    def _delete(self):
        usuario = self._selected_usuario()
        if not usuario:
            return
        reply = QMessageBox.question(
            self,
            "Eliminar usuari",
            f"Vols eliminar l'usuari {usuario['username']}?",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            eliminar_usuario(usuario["id"])
        except ValueError as exc:
            QMessageBox.warning(self, "No s'ha pogut eliminar", str(exc))
            return
        self._refresh()

    def _show_audit_for_item(self, item: QTableWidgetItem):
        self.table.selectRow(item.row())
        self._show_selected_audit()

    def _show_selected_audit(self):
        usuario = self._selected_usuario()
        if not usuario:
            return
        rows = listar_auditoria_usuario(usuario["username"])
        dlg = UsuarioAuditoriaDialog(self, usuario["username"], rows)
        dlg.exec()


def cambiar_password_actual(parent, current_user: dict) -> bool:
    usuario_id = current_user.get("id")
    if not usuario_id:
        QMessageBox.warning(parent, "Usuari", "No s'ha pogut identificar l'usuari actual.")
        return False

    dlg = CambiarPasswordDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return False
    actual, nueva = dlg.passwords()
    try:
        cambiar_password_usuario(usuario_id, actual, nueva)
    except ValueError as exc:
        QMessageBox.warning(parent, "No s'ha pogut canviar", str(exc))
        return False
    QMessageBox.information(parent, "Contrasenya", "La contrasenya s'ha canviat correctament.")
    return True
