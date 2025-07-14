from PySide6.QtWidgets import (
    QDialog, QLineEdit, QComboBox, QDateEdit, QSpinBox, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox
)
from PySide6.QtCore import QDate
from controladores.actividades import modificar_actividad, registrar_actividad

class ActividadDialog(QDialog):
    def __init__(self, parent=None, actividad=None):
        super().__init__(parent)
        self.actividad = actividad
        self.setWindowTitle("Nova activitat" if actividad is None else "Editar activitat")

        self.nombre = QLineEdit()
        self.tipo = QComboBox()
        self.tipo.addItems(["Curso", "Taller", "Altres"])
        self.descripcion = QLineEdit()
        self.profesor = QLineEdit()
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate())
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        self.numero_maximo_alumnos = QSpinBox()
        self.numero_maximo_alumnos.setMinimum(1)
        self.numero_maximo_alumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Tipus:", self.tipo)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Professor/Voluntari:", self.profesor)
        form.addRow("Data inici:", self.fecha_inicio)
        form.addRow("Data fi:", self.fecha_fin)
        form.addRow("Màxim alumnes:", self.numero_maximo_alumnos)

        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancel·lar")
        btn_guardar.clicked.connect(self._save)
        btn_cancelar.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(btn_guardar)
        layout.addWidget(btn_cancelar)
        self.setLayout(layout)

        if actividad:
            self.nombre.setText(actividad["nombre"])
            self.tipo.setCurrentText(actividad["tipo"])
            self.descripcion.setText(actividad.get("descripcion", ""))
            self.profesor.setText(actividad.get("profesor", ""))
            self.fecha_inicio.setDate(QDate.fromString(actividad.get("fecha_inicio", ""), "yyyy-MM-dd"))
            self.fecha_fin.setDate(QDate.fromString(actividad.get("fecha_fin", ""), "yyyy-MM-dd"))
            self.numero_maximo_alumnos.setValue(actividad.get("numero_maximo_alumnos", 1))

    def _save(self):
        data = {
            "nombre": self.nombre.text().strip(),
            "tipo": self.tipo.currentText(),
            "descripcion": self.descripcion.text().strip(),
            "profesor": self.profesor.text().strip(),
            "fecha_inicio": self.fecha_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.fecha_fin.date().toString("yyyy-MM-dd"),
            "numero_maximo_alumnos": self.numero_maximo_alumnos.value()
        }

        if not data["nombre"]:
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return

        if self.actividad:
            modificar_actividad(self.actividad["id"], data)
        else:
            registrar_actividad(data)

        self.accept()