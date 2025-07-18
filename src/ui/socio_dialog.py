from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDateEdit, QTextEdit, QPushButton,
    QFileDialog, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QDate
from datetime import date
from controladores.socios import registrar_socio, modificar_socio
import os


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
        self.dni = QLineEdit();      self.nom = QLineEdit()
        self.c1 = QLineEdit();       self.c2 = QLineEdit()
        self.dir = QLineEdit()
        self.tel_fix = QLineEdit();  self.tel_mob = QLineEdit()
        self.email = QLineEdit();    self.grup = QLineEdit()
        self.data_alta = QDateEdit();  self.data_alta.setCalendarPopup(True)
        self.obs = QTextEdit()
        self.preview = QLabel();     self.preview.setFixedSize(100, 120)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("border:1px solid #aaa;")


        self.data_alta.setDate(QDate.currentDate())

        # ── Disseny ──────────────────────────────────────────
        form = QFormLayout(self)
        form.addRow("DNI/NIE *:", self.dni)
        form.addRow("Nom *:", self.nom)
        form.addRow("1r Cognom *:", self.c1)
        form.addRow("2n Cognom:", self.c2)
        form.addRow("Adreça:", self.dir)
        form.addRow("Tel. fix:", self.tel_fix)
        form.addRow("Tel. mòbil:", self.tel_mob)
        form.addRow("Email:", self.email)
        form.addRow("Grup difusió:", self.grup)
        form.addRow("Data alta:", self.data_alta)
        form.addRow("Observacions:", self.obs)

        # Foto
        btn_foto = QPushButton("Carregar foto")
        btn_foto.clicked.connect(self._seleccionar_foto)
        foto_box = QHBoxLayout(); foto_box.addWidget(btn_foto); foto_box.addWidget(self.preview)
        form.addRow("Foto:", foto_box)

        # Botó guardar
        btn_save = QPushButton("Desar")
        btn_save.clicked.connect(self._guardar)
        form.addRow(btn_save)

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
            "fechaAlta": self.data_alta.date().toPython() or date.today(),
            "fechaBaja": None,
            "observaciones": self.obs.toPlainText() or None,
        }
        if self._foto_path:
            with open(self._foto_path, "rb") as fh:
                data["foto"] = fh.read()
        return data

    def _guardar(self):
        if not self._validar():
            return

        data = self._build_data()
        try:
            if self._edit_mode:
                modificar_socio(self._socioID, data)
            else:
                registrar_socio(data)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.accept()