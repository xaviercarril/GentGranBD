from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDateEdit, QTextEdit, QPushButton,
    QFileDialog, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtGui import QPixmap, QIntValidator
from PySide6.QtCore import Qt, QDate
from datetime import date
from controladores.socios import registrar_socio, modificar_socio
from ui.theme import Palette, set_button_variant


EMPTY_DATE = QDate(1900, 1, 1)


class SocioDialog(QDialog):
    """Diàleg de “Nou / Editar” soci amb tots els camps i gestió de foto."""

    _REQUERITS = ("dniNie", "nombre")

    def __init__(self, parent=None, socio: dict | None = None):
        super().__init__(parent)
        self._edit_mode = socio is not None
        self._socioID = socio["id"] if socio else None
        self._foto_path: str | None = None
        self.setWindowTitle("Editar soci" if socio else "Nou soci")

        # ── Widgets ──────────────────────────────────────────
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Automàtic si es deixa en blanc")
        self.id_input.setValidator(QIntValidator(0, 999999999, self))
        self.dni = QLineEdit();      self.nom = QLineEdit()
        self.c1 = QLineEdit();       self.c2 = QLineEdit()
        self.dir = QLineEdit()
        self.tel_fix = QLineEdit();  self.tel_mob = QLineEdit()
        self.email = QLineEdit();    self.grup = QLineEdit()
        self.data_naixement = QDateEdit(); self.data_naixement.setCalendarPopup(True)
        self.data_naixement.setDisplayFormat("dd/MM/yyyy")
        self.data_naixement.setMinimumDate(EMPTY_DATE)
        self.data_naixement.setSpecialValueText("")
        self.data_naixement.setDate(EMPTY_DATE)
        self.data_alta = QDateEdit();  self.data_alta.setCalendarPopup(True)
        self.obs = QTextEdit()
        self.preview = QLabel();     self.preview.setFixedSize(100, 120)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet(f"border:1px solid {Palette.BORDER_STRONG}; border-radius: 5px; background: {Palette.SURFACE_ALT};")


        self.data_alta.setDate(QDate.currentDate())

        # ── Disseny ──────────────────────────────────────────
        form = QFormLayout(self)
        form.addRow("ID soci:", self.id_input)
        form.addRow("DNI/NIE *:", self.dni)
        form.addRow("Nom *:", self.nom)
        form.addRow("1r Cognom *:", self.c1)
        form.addRow("2n Cognom:", self.c2)
        form.addRow("Adreça:", self.dir)
        form.addRow("Tel. fix:", self.tel_fix)
        form.addRow("Tel. mòbil:", self.tel_mob)
        form.addRow("Email:", self.email)
        form.addRow("Grup difusió:", self.grup)
        form.addRow("Data naixement:", self.data_naixement)
        form.addRow("Data alta:", self.data_alta)
        form.addRow("Observacions:", self.obs)

        # Foto
        btn_foto = QPushButton("Carregar foto")
        set_button_variant(btn_foto, "secondary")
        btn_foto.clicked.connect(self._seleccionar_foto)
        foto_box = QHBoxLayout(); foto_box.addWidget(btn_foto); foto_box.addWidget(self.preview)
        form.addRow("Foto:", foto_box)

        # Botó guardar
        btn_save = QPushButton("Desar")
        set_button_variant(btn_save, "primary")
        btn_save.clicked.connect(self._guardar)
        form.addRow(btn_save)

        if socio:
            self._carregar_socio(socio)

    # ─────────────────────────────────────────────────────────
    # Utils
    # ─────────────────────────────────────────────────────────
    def _seleccionar_foto(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Selecciona foto", "", "Imatges (*.png *.jpg *.jpeg)"
        )
        if file:
            self._foto_path = file
            pix = QPixmap(file).scaled(
                self.preview.width(), self.preview.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview.setPixmap(pix)

    # ─────────────────────────────────────────────────────────
    # Guardar
    # ─────────────────────────────────────────────────────────
    def _validar(self) -> bool:
        if not self.dni.text().strip() or not self.nom.text().strip() or not self.c1.text().strip():
            QMessageBox.warning(self, "Error",
                                "Els camps marcats amb * són obligatoris.")
            return False
        return True

    def _build_data(self) -> dict:
        id_text = self.id_input.text().strip()
        id_value = None
        if id_text:
            try:
                id_value = int(id_text)
                if id_value <= 0:
                    raise ValueError("L'ID ha de ser un enter positiu.")
            except ValueError as exc:
                raise ValueError("L'ID ha de ser un número enter vàlid.") from exc

        data = {
            "dniNie": self.dni.text().strip(),
            "nombre": self.nom.text().strip(),
            "apellido1": self.c1.text().strip(),
            "apellido2": self.c2.text().strip() or None,
            "direccion": self.dir.text().strip() or None,
            "telefonoFijo": self.tel_fix.text().strip() or None,
            "telefonoMovil": self.tel_mob.text().strip() or None,
            "email": self.email.text().strip() or None,
            "grupoDifusion": self.grup.text().strip() or None,
            "fechaNacimiento": (
                self.data_naixement.date().toPython()
                if self.data_naixement.date() != EMPTY_DATE
                else None
            ),
            "fechaAlta": self.data_alta.date().toPython() or date.today(),
            "fechaBaja": None,
            "observaciones": self.obs.toPlainText() or None,
        }
        if id_value is not None:
            data["id"] = id_value
        elif self._edit_mode and self._socioID is not None:
            data["id"] = self._socioID
        if self._foto_path:
            with open(self._foto_path, "rb") as fh:
                data["foto"] = fh.read()
        return data

    def _guardar(self):
        if not self._validar():
            return

        try:
            data = self._build_data()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            if self._edit_mode and self._socioID is not None:
                self.id_input.setText(str(self._socioID))
            return

        try:
            if self._edit_mode:
                modificar_socio(self._socioID, data)
                if data.get("id") is not None:
                    self._socioID = data["id"]
                    self.id_input.setText(str(self._socioID))
            else:
                registrar_socio(data)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.accept()

    def _carregar_socio(self, socio: dict):
        """Omple el formulari amb les dades existents."""
        self.id_input.setText(str(socio.get("id", "") or ""))
        self.dni.setText(socio.get("dniNie", "") or "")
        self.nom.setText(socio.get("nombre", "") or "")
        self.c1.setText(socio.get("apellido1", "") or "")
        self.c2.setText(socio.get("apellido2", "") or "")
        self.dir.setText(socio.get("direccion", "") or "")
        self.tel_fix.setText(socio.get("telefonoFijo", "") or "")
        self.tel_mob.setText(socio.get("telefonoMovil", "") or "")
        self.email.setText(socio.get("email", "") or "")
        self.grup.setText(socio.get("grupoDifusion", "") or "")
        fecha_naixement = socio.get("fechaNacimiento")
        if fecha_naixement:
            if isinstance(fecha_naixement, date):
                self.data_naixement.setDate(QDate(fecha_naixement.year, fecha_naixement.month, fecha_naixement.day))
            else:
                self.data_naixement.setDate(QDate.fromString(str(fecha_naixement)))
        else:
            self.data_naixement.setDate(EMPTY_DATE)
        fecha_alta = socio.get("fechaAlta")
        if fecha_alta:
            if isinstance(fecha_alta, date):
                self.data_alta.setDate(QDate(fecha_alta.year, fecha_alta.month, fecha_alta.day))
            else:
                self.data_alta.setDate(QDate.fromString(str(fecha_alta)))
        self.obs.setPlainText(socio.get("observaciones", "") or "")
