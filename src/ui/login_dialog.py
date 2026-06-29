from sqlalchemy.exc import SQLAlchemyError

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from controladores.acceso import autenticar_usuario, bootstrap_admin_si_no_hay_usuarios
from database import default_database_url, ensure_schema_updates, set_database_url
from models import Base
from ui.theme import Palette, set_button_variant
from version import APP_VERSION
import database


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Accés a Gent Gran")
        self.setMinimumWidth(560)
        self.current_user: dict | None = None
        self.setStyleSheet(
            """
            QDialog {
                background: %s;
            }
            QFrame#loginPanel {
                background: white;
                border: 1px solid %s;
                border-radius: 8px;
            }
            QLabel#title {
                color: %s;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#subtitle {
                color: %s;
                background: transparent;
            }
            QLabel#version {
                color: %s;
                font-size: 11px;
                background: transparent;
            }
            QLabel {
                background: transparent;
            }
            QLineEdit {
                min-height: 26px;
                padding: 3px 7px;
                border: 1px solid %s;
                border-radius: 5px;
                background: %s;
            }
            QLineEdit:focus {
                border: 1px solid %s;
            }
            QPushButton {
                min-height: 28px;
                padding: 4px 12px;
            }
            """
            % (
                Palette.APP_BG,
                Palette.BORDER,
                Palette.TEXT,
                Palette.TEXT_MUTED,
                Palette.TEXT_MUTED,
                Palette.BORDER_STRONG,
                Palette.SURFACE,
                Palette.PRIMARY,
            )
        )

        settings = QSettings("GentGran", "GentGranBD")
        initial_url = settings.value("last_database_url", "", type=str) or ""
        if not initial_url:
            initial_url = default_database_url()

        self.database_url = QLineEdit(initial_url)
        self.database_url.setPlaceholderText("URL SQLAlchemy de la base de dades")
        self.username = QLineEdit("admin")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        logo = QLabel()
        logo.setFixedHeight(120)
        logo.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap("extra/logo.png")
        if pixmap.isNull():
            pixmap = QPixmap("extra/icon.png")
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaledToHeight(110, Qt.SmoothTransformation))

        title = QLabel("Associació Gent Gran de Castelldefels")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Inicia sessió per accedir a la gestió")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        version = QLabel(f"Versió {APP_VERSION}")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignCenter)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.addRow("Database URL:", self.database_url)
        form.addRow("Usuari:", self.username)
        form.addRow("Contrasenya:", self.password)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Entrar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Sortir")
        set_button_variant(self.buttons.button(QDialogButtonBox.Ok), "primary")
        set_button_variant(self.buttons.button(QDialogButtonBox.Cancel), "secondary")
        self.buttons.accepted.connect(self._login)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        panel = QFrame()
        panel.setObjectName("loginPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 22, 28, 22)
        panel_layout.setSpacing(14)
        panel_layout.addWidget(logo)
        panel_layout.addWidget(title)
        panel_layout.addWidget(subtitle)
        panel_layout.addWidget(version)
        panel_layout.addSpacing(8)
        panel_layout.addLayout(form)
        panel_layout.addWidget(self.buttons)
        layout.addWidget(panel)

    def _save_last_url(self, url: str) -> None:
        settings = QSettings("GentGran", "GentGranBD")
        if "@" in url and ":" in url.split("@", 1)[0]:
            settings.remove("last_database_url")
            return
        settings.setValue("last_database_url", url)

    def _login(self):
        url = self.database_url.text().strip()
        try:
            set_database_url(url)
            Base.metadata.create_all(bind=database.engine)
            ensure_schema_updates()
            bootstrap_admin_si_no_hay_usuarios()
            self.current_user = autenticar_usuario(
                self.username.text(),
                self.password.text(),
            )
        except (SQLAlchemyError, ValueError) as exc:
            QMessageBox.warning(self, "No s'ha pogut iniciar sessió", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error de connexió", str(exc))
            return

        self._save_last_url(url or default_database_url())
        self.accept()
