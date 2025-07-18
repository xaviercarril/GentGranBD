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
        self.fechaInicio = QDateEdit()
        self.fechaInicio.setCalendarPopup(True)
        self.fechaInicio.setDate(QDate.currentDate())
        self.fechaFin = QDateEdit()
        self.fechaFin.setCalendarPopup(True)
        self.fechaFin.setDate(QDate.currentDate())
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(1)
        self.numMaxAlumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Tipus:", self.tipo)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Professor/Voluntari:", self.profesor)
        form.addRow("Data inici:", self.fechaInicio)
        form.addRow("Data fi:", self.fechaFin)
        form.addRow("Màxim alumnes:", self.numMaxAlumnos)

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
            self.fechaInicio.setDate(QDate.fromString(actividad.get("fechaInicio", ""), "dd-MM-yyyy"))
            self.fechaFin.setDate(QDate.fromString(actividad.get("fechaFin", ""), "dd-MM-yyyy"))
            self.numMaxAlumnos.setValue(actividad.get("numMaxAlumnos", 1))

    def _save(self):
        data = {
            "nombre": self.nombre.text().strip(),
            "tipo": self.tipo.currentText(),
            "descripcion": self.descripcion.text().strip(),
            "profesor": self.profesor.text().strip(),
            "fechaInicio": self.fechaInicio.date().toString("dd-MM-yyyy"),
            "fechaFin": self.fechaFin.date().toString("dd-MM-yyyy"),
            "numMaxAlumnos": self.numMaxAlumnos.value()
        }

        if not data["nombre"]:
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return

        if self.actividad:
            modificar_actividad(self.actividad["id"], data)
        else:
            registrar_actividad(data)

        self.accept()