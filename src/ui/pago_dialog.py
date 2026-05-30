from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QDoubleSpinBox, QTextEdit, QComboBox
)
from PySide6.QtCore import QDate
from datetime import date
from ui.theme import set_button_variant

class PagoDialog(QDialog):
    def __init__(self, importe_default: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir pagament")

        layout = QVBoxLayout(self)

        # Fecha del pago
        layout_fecha = QHBoxLayout()
        layout_fecha.addWidget(QLabel("Data del pagament:"))
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setDate(QDate.currentDate())
        self.fecha_edit.setCalendarPopup(True)
        layout_fecha.addWidget(self.fecha_edit)
        layout.addLayout(layout_fecha)

        # Importe
        layout_importe = QHBoxLayout()
        layout_importe.addWidget(QLabel("Import:"))
        self.importe_spin = QDoubleSpinBox()
        self.importe_spin.setDecimals(2)
        self.importe_spin.setMinimum(0.0)
        self.importe_spin.setMaximum(9999.99)
        self.importe_spin.setValue(importe_default)
        layout_importe.addWidget(self.importe_spin)
        layout.addLayout(layout_importe)

        # Estado
        layout_estado = QHBoxLayout()
        layout_estado.addWidget(QLabel("Estat:"))
        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["PENDENT", "PAGAT"])
        layout_estado.addWidget(self.estado_combo)
        layout.addLayout(layout_estado)

        # Observaciones
        layout.addWidget(QLabel("Observacions:"))
        self.observaciones_edit = QTextEdit()
        layout.addWidget(self.observaciones_edit)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Afegir")
        self.btn_cancel = QPushButton("Cancel·lar")
        set_button_variant(self.btn_ok, "primary")
        set_button_variant(self.btn_cancel, "secondary")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self) -> dict:
        return {
            "fecha_pago": self.fecha_edit.date().toPython(),
            "importe": self.importe_spin.value(),
            "estado": self.estado_combo.currentText(),
            "observaciones": self.observaciones_edit.toPlainText().strip()
        }
