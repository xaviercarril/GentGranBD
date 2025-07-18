from PySide6.QtWidgets import (
    QDialog, QLineEdit, QComboBox, QDateEdit, QSpinBox, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox
)
from PySide6.QtCore import QDate
from controladores.actividades import modificar_actividad, registrar_actividad

class ActividadDialog(QDialog):
    def __init__(self, parent=None, actividad=None, cursoAcademico_id=None):
        super().__init__(parent)
        self._cursoAcademico_id = cursoAcademico_id
        self.actividad = actividad
        self.setWindowTitle("Nova activitat" if actividad is None else "Editar activitat")

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.profesor = QLineEdit()
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(1)
        self.numMaxAlumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Professor/Voluntari:", self.profesor)
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
            self.descripcion.setText(actividad.get("descripcion", ""))
            self.profesor.setText(actividad.get("profesor", ""))
            self.numMaxAlumnos.setValue(actividad.get("numMaxAlumnos", 1))

    def _save(self):
        data = {
            "nombre": self.nombre.text().strip(),
            "descripcion": self.descripcion.text().strip(),
            "profesor": self.profesor.text().strip(),
            "numMaxAlumnos": self.numMaxAlumnos.value(),
            "cursoAcademico_id": self.actividad["cursoAcademico_id"] if self.actividad else self._cursoAcademico_id
        }

        if not data["nombre"]:
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return

        if self.actividad:
            modificar_actividad(self.actividad["id"], data)
        else:
            registrar_actividad(data)

        self.accept()