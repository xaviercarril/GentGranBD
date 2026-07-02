import json
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import URL, make_url

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from controladores.acceso import autenticar_usuario, bootstrap_admin_si_no_hay_usuarios
from database import ensure_schema_updates, local_database_url, set_database_url
from models import Base
from ui.theme import Palette, set_button_variant
from version import APP_VERSION
import database

CONNECTION_PROFILES_KEY = "connection_profiles"
LAST_CONNECTION_PROFILE_KEY = "last_connection_profile_id"
POSTGRES_SSLMODES = ("require", "prefer", "disable", "verify-full")


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgresql+")


def _url_without_credentials(url: str) -> str:
    if not _is_postgres_url(url):
        return url
    try:
        parsed = make_url(url)
    except Exception:
        return url
    return URL.create(
        drivername=parsed.drivername,
        host=parsed.host,
        port=parsed.port,
        database=parsed.database,
        query=parsed.query,
    ).render_as_string(hide_password=False)


def _url_has_credentials(url: str) -> bool:
    if not _is_postgres_url(url):
        return False
    try:
        parsed = make_url(url)
    except Exception:
        return False
    return bool(parsed.username or parsed.password)


def _initial_connection_url(saved_url: str, configured_url: str) -> str:
    if _url_has_credentials(configured_url):
        return configured_url
    return saved_url or configured_url


def _profile_name_for_url(url: str, fallback: str = "Connexió") -> str:
    if url.startswith("sqlite"):
        return "Local"
    if not _is_postgres_url(url):
        return fallback
    try:
        parsed = make_url(url)
    except Exception:
        return fallback
    database_name = parsed.database or "postgres"
    host = parsed.host or ""
    if "ondigitalocean.com" in host:
        return f"DigitalOcean - {database_name}"
    return f"{host} - {database_name}" if host else fallback


def _postgres_profile_from_url(url: str) -> dict:
    if not _is_postgres_url(url):
        return {}
    try:
        parsed = make_url(url)
    except Exception:
        return {}
    return {
        "driver": "postgresql",
        "host": parsed.host or "",
        "port": str(parsed.port or ""),
        "database": parsed.database or "",
        "db_username": parsed.username or "",
        "db_password": parsed.password or "",
        "sslmode": parsed.query.get("sslmode", "require"),
    }


def _profile_connection_url(profile: dict) -> str:
    if profile.get("url"):
        return profile["url"]
    if profile.get("driver") != "postgresql":
        return ""

    port_text = str(profile.get("port") or "").strip()
    try:
        port = int(port_text) if port_text else None
    except ValueError:
        port = None
    sslmode = str(profile.get("sslmode") or "require").strip()
    query = {"sslmode": sslmode} if sslmode else {}
    return URL.create(
        drivername="postgresql+psycopg",
        username=str(profile.get("db_username") or "").strip() or None,
        password=str(profile.get("db_password") or ""),
        host=str(profile.get("host") or "").strip() or None,
        port=port,
        database=str(profile.get("database") or "").strip() or None,
        query=query,
    ).render_as_string(hide_password=False)


def _profile_display_url(profile: dict) -> str:
    return _url_without_credentials(_profile_connection_url(profile))


def _profile_from_settings_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    if not name:
        return None

    profile = {
        "id": str(item.get("id") or uuid4()),
        "name": name,
        "builtin": False,
    }
    if item.get("url"):
        url = str(item.get("url") or "").strip()
        postgres_fields = _postgres_profile_from_url(url)
        if postgres_fields:
            profile.update(postgres_fields)
        elif url:
            profile["url"] = url
        else:
            return None
        return profile

    profile.update(
        {
            "driver": "postgresql",
            "host": str(item.get("host") or "").strip(),
            "port": str(item.get("port") or "").strip() or "25060",
            "database": str(item.get("database") or "").strip(),
            "db_username": str(item.get("db_username") or "").strip(),
            "db_password": str(item.get("db_password") or ""),
            "sslmode": str(item.get("sslmode") or "require").strip(),
        }
    )
    if not profile["host"] or not profile["database"] or not profile["db_username"]:
        return None
    return profile


def _builtin_connection_profiles(_configured_url: str | None = None) -> list[dict]:
    return [
        {
            "id": "local",
            "name": "Local",
            "url": local_database_url(),
            "builtin": True,
        }
    ]


def _load_custom_connection_profiles(settings: QSettings) -> list[dict]:
    raw = settings.value(CONNECTION_PROFILES_KEY, "", type=str) or ""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    profiles = []
    for item in data if isinstance(data, list) else []:
        profile = _profile_from_settings_item(item)
        if profile:
            profiles.append(profile)
    return profiles


def _save_custom_connection_profiles(settings: QSettings, profiles: list[dict]) -> None:
    custom = []
    for profile in profiles:
        if profile.get("builtin"):
            continue
        if profile.get("driver") == "postgresql":
            custom.append(
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "driver": "postgresql",
                    "host": profile.get("host", ""),
                    "port": profile.get("port", ""),
                    "database": profile.get("database", ""),
                    "db_username": profile.get("db_username", ""),
                    "db_password": profile.get("db_password", ""),
                    "sslmode": profile.get("sslmode", "require"),
                }
            )
            continue
        if profile.get("url"):
            custom.append(
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "url": profile["url"],
                }
            )
    settings.setValue(CONNECTION_PROFILES_KEY, json.dumps(custom, ensure_ascii=False))


def _connection_profiles(settings: QSettings, configured_url: str | None = None) -> list[dict]:
    return _builtin_connection_profiles(configured_url) + _load_custom_connection_profiles(settings)


class ConnectionProfileEditDialog(QDialog):
    def __init__(self, parent=None, profile: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Perfil de connexió")
        self.setMinimumWidth(520)
        profile = dict(profile or {})
        if profile.get("url"):
            profile.update(_postgres_profile_from_url(profile["url"]))
            profile.pop("url", None)

        self.name_input = QLineEdit(profile.get("name", ""))
        self.host_input = QLineEdit(profile.get("host", ""))
        self.host_input.setPlaceholderText("host privat o públic")
        self.port_input = QLineEdit(str(profile.get("port") or "25060"))
        self.database_input = QLineEdit(profile.get("database", "gentgran"))
        self.db_username_input = QLineEdit(profile.get("db_username", ""))
        self.db_password_input = QLineEdit(profile.get("db_password", ""))
        self.db_password_input.setEchoMode(QLineEdit.Password)
        self.sslmode_combo = QComboBox()
        for sslmode in POSTGRES_SSLMODES:
            self.sslmode_combo.addItem(sslmode, sslmode)
        sslmode_index = self.sslmode_combo.findData(profile.get("sslmode") or "require")
        if sslmode_index >= 0:
            self.sslmode_combo.setCurrentIndex(sslmode_index)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("Nom:", self.name_input)
        form.addRow("Host:", self.host_input)
        form.addRow("Port:", self.port_input)
        form.addRow("Base de dades:", self.database_input)
        form.addRow("Usuari BD:", self.db_username_input)
        form.addRow("Contrasenya BD:", self.db_password_input)
        form.addRow("SSL:", self.sslmode_combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Guardar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancel·lar")
        set_button_variant(self.buttons.button(QDialogButtonBox.Ok), "primary")
        set_button_variant(self.buttons.button(QDialogButtonBox.Cancel), "secondary")
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def profile_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "driver": "postgresql",
            "host": self.host_input.text().strip(),
            "port": self.port_input.text().strip(),
            "database": self.database_input.text().strip(),
            "db_username": self.db_username_input.text().strip(),
            "db_password": self.db_password_input.text(),
            "sslmode": self.sslmode_combo.currentData() or "require",
        }

    def _accept_if_valid(self):
        data = self.profile_data()
        if not data["name"] or not data["host"] or not data["database"] or not data["db_username"]:
            QMessageBox.warning(
                self,
                "Perfil incomplet",
                "Cal indicar nom, host, base de dades i usuari de BD.",
            )
            return
        if data["port"]:
            try:
                port = int(data["port"])
            except ValueError:
                QMessageBox.warning(self, "Port invàlid", "El port ha de ser numèric.")
                return
            if port <= 0 or port > 65535:
                QMessageBox.warning(self, "Port invàlid", "El port ha d'estar entre 1 i 65535.")
                return
            data["port"] = str(port)
        if not data["db_password"]:
            reply = QMessageBox.question(
                self,
                "Contrasenya buida",
                "Vols guardar el perfil sense contrasenya de BD?",
            )
            if reply != QMessageBox.Yes:
                return
        if not _profile_connection_url(data):
            QMessageBox.warning(self, "Perfil invàlid", "No s'ha pogut construir la connexió.")
            return
        self.accept()


class ConnectionProfilesDialog(QDialog):
    def __init__(self, profiles: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Perfils de connexió")
        self.setMinimumWidth(560)
        self._profiles = [dict(profile) for profile in profiles]
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._update_buttons)

        self.add_button = QPushButton("Nou")
        self.edit_button = QPushButton("Editar")
        self.delete_button = QPushButton("Eliminar")
        set_button_variant(self.add_button, "primary")
        set_button_variant(self.edit_button, "secondary")
        set_button_variant(self.delete_button, "secondary")
        self.add_button.clicked.connect(self._add_profile)
        self.edit_button.clicked.connect(self._edit_profile)
        self.delete_button.clicked.connect(self._delete_profile)

        actions = QHBoxLayout()
        actions.addWidget(self.add_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Guardar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancel·lar")
        set_button_variant(self.buttons.button(QDialogButtonBox.Ok), "primary")
        set_button_variant(self.buttons.button(QDialogButtonBox.Cancel), "secondary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(actions)
        layout.addWidget(self.buttons)
        self._reload_list()

    def profiles(self) -> list[dict]:
        return [dict(profile) for profile in self._profiles]

    def _selected_row(self) -> int:
        return self.list_widget.currentRow()

    def _selected_profile(self) -> dict | None:
        row = self._selected_row()
        if row < 0 or row >= len(self._profiles):
            return None
        return self._profiles[row]

    def _reload_list(self, selected_row: int | None = None):
        self.list_widget.clear()
        for profile in self._profiles:
            suffix = " (fix)" if profile.get("builtin") else ""
            item = QListWidgetItem(f"{profile['name']}{suffix}")
            item.setToolTip(_profile_display_url(profile))
            self.list_widget.addItem(item)
        if self._profiles:
            row = selected_row if selected_row is not None else 0
            self.list_widget.setCurrentRow(max(0, min(row, len(self._profiles) - 1)))
        self._update_buttons()

    def _update_buttons(self):
        profile = self._selected_profile()
        can_edit = bool(profile and not profile.get("builtin"))
        self.edit_button.setEnabled(can_edit)
        self.delete_button.setEnabled(can_edit)

    def _add_profile(self):
        dialog = ConnectionProfileEditDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.profile_data()
        self._profiles.append(
            {
                "id": str(uuid4()),
                "name": data["name"],
                "driver": "postgresql",
                "host": data["host"],
                "port": data["port"],
                "database": data["database"],
                "db_username": data["db_username"],
                "db_password": data["db_password"],
                "sslmode": data["sslmode"],
                "builtin": False,
            }
        )
        self._reload_list(len(self._profiles) - 1)

    def _edit_profile(self):
        profile = self._selected_profile()
        if not profile or profile.get("builtin"):
            return
        dialog = ConnectionProfileEditDialog(self, profile)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.profile_data()
        profile["name"] = data["name"]
        profile["driver"] = "postgresql"
        profile["host"] = data["host"]
        profile["port"] = data["port"]
        profile["database"] = data["database"]
        profile["db_username"] = data["db_username"]
        profile["db_password"] = data["db_password"]
        profile["sslmode"] = data["sslmode"]
        profile.pop("url", None)
        self._reload_list(self._selected_row())

    def _delete_profile(self):
        row = self._selected_row()
        profile = self._selected_profile()
        if row < 0 or not profile or profile.get("builtin"):
            return
        reply = QMessageBox.question(
            self,
            "Eliminar perfil",
            f"Vols eliminar el perfil «{profile['name']}»?",
        )
        if reply != QMessageBox.Yes:
            return
        del self._profiles[row]
        self._reload_list(row)


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
            QComboBox {
                min-height: 26px;
                padding: 3px 7px;
                border: 1px solid %s;
                border-radius: 5px;
                background: %s;
            }
            QLineEdit:focus {
                border: 1px solid %s;
            }
            QComboBox:focus {
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
                Palette.BORDER_STRONG,
                Palette.SURFACE,
                Palette.PRIMARY,
                Palette.PRIMARY,
            )
        )

        self._settings = QSettings("GentGran", "GentGranBD")
        self._initial_connection_url = local_database_url()
        self._initial_display_url = _url_without_credentials(self._initial_connection_url)
        self._profiles = _connection_profiles(self._settings)
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self.profile_menu_button = QPushButton("☰")
        self.profile_menu_button.setFixedWidth(42)
        self.profile_menu_button.setToolTip("Gestionar perfils de connexió")
        set_button_variant(self.profile_menu_button, "secondary")
        self.profile_menu_button.clicked.connect(self._manage_connection_profiles)
        self._reload_profile_combo()
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
        profile_row = QHBoxLayout()
        profile_row.setContentsMargins(0, 0, 0, 0)
        profile_row.addWidget(self.profile_combo, 1)
        profile_row.addWidget(self.profile_menu_button)
        form.addRow("Connexió:", profile_row)
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

    def _selected_profile(self) -> dict | None:
        profile_id = self.profile_combo.currentData()
        for profile in self._profiles:
            if profile.get("id") == profile_id:
                return profile
        return self._profiles[0] if self._profiles else None

    def _reload_profile_combo(self, selected_profile_id: str | None = None):
        selected_profile_id = (
            selected_profile_id
            or self._settings.value(LAST_CONNECTION_PROFILE_KEY, "", type=str)
            or "local"
        )
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected_index = 0
        for index, profile in enumerate(self._profiles):
            self.profile_combo.addItem(profile["name"], profile["id"])
            self.profile_combo.setItemData(
                index,
                _profile_display_url(profile),
                Qt.ToolTipRole,
            )
            if profile["id"] == selected_profile_id:
                selected_index = index
        if self._profiles:
            self.profile_combo.setCurrentIndex(selected_index)
        self.profile_combo.blockSignals(False)
        self._on_profile_changed()

    def _on_profile_changed(self):
        profile = self._selected_profile()
        if profile:
            self.profile_combo.setToolTip(_profile_display_url(profile))

    def _manage_connection_profiles(self):
        current_profile = self._selected_profile()
        dialog = ConnectionProfilesDialog(self._profiles, self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected_profile_id = current_profile["id"] if current_profile else None
        self._profiles = dialog.profiles()
        _save_custom_connection_profiles(self._settings, self._profiles)
        if selected_profile_id not in {profile["id"] for profile in self._profiles}:
            selected_profile_id = None
        self._reload_profile_combo(selected_profile_id)

    def _connection_url_from_form(self) -> str:
        profile = self._selected_profile()
        if profile:
            return _profile_connection_url(profile)
        return self._initial_connection_url

    def _save_last_url(self, url: str) -> None:
        profile = self._selected_profile()
        if profile:
            self._settings.setValue(LAST_CONNECTION_PROFILE_KEY, profile["id"])
        self._settings.setValue("last_database_url", _url_without_credentials(url))
        self._settings.remove("last_database_user")

    def _login(self):
        connection_url = self._connection_url_from_form()
        try:
            set_database_url(connection_url)
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

        self._save_last_url(connection_url or local_database_url())
        self.accept()
