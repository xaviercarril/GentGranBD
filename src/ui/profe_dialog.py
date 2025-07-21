from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDateEdit, QTextEdit, QPushButton,
    QFileDialog, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QDate
from datetime import date
from controladores.personal import registrar_personal, modificar_personal
import os


class ProfeDialog(QDialog):
    """Diàleg de “Nou / Editar” professor amb tots els camps i gestió de foto."""

    _REQUERITS = ("dniNie", "nombre")

    def __init__(self, parent=None, personal: dict | None = None):
        super().__init__(parent)
        self._edit_mode = personal is not None
        self._personalID = personal["id"] if personal else None
        self.setWindowTitle("Editar professor" if personal else "Nou professor")

        # ── Widgets ──────────────────────────────────────────
        self.dni = QLineEdit()
        self.nom = QLineEdit()
        self.c1 = QLineEdit()
        self.c2 = QLineEdit()
        self.tel_mob = QLineEdit()
        self.email = QLineEdit()
        self.obs = QTextEdit()
        self.preview = QLabel();     self.preview.setFixedSize(100, 120)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("border:1px solid #aaa;")

        # ── Disseny ──────────────────────────────────────────
        form = QFormLayout(self)
        form.addRow("DNI/NIE *:", self.dni)
        form.addRow("Nom *:", self.nom)
        form.addRow("1r Cognom *:", self.c1)
        form.addRow("2n Cognom:", self.c2)
        form.addRow("Tel. mòbil:", self.tel_mob)
        form.addRow("Email:", self.email)
        form.addRow("Observacions:", self.obs)

        # Botó guardar
        btn_save = QPushButton("Desar")
        btn_save.clicked.connect(self._guardar)
        form.addRow(btn_save)

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
            "telfMovil": self.tel_mob.text().strip() or None,
            "email": self.email.text().strip() or None,
            "observaciones": self.obs.toPlainText() or None
        }
        return data

    def _guardar(self):
        if not self._validar():
            return

        data = self._build_data()
        try:
            if self._edit_mode:
                modificar_personal(self._personalID, data)
            else:
                registrar_personal(data, "profesor")
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.accept()