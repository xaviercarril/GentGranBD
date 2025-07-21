from PySide6.QtWidgets import (
    QDialog, QLineEdit, QComboBox, QDateEdit, QSpinBox, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox
)
from controladores.actividades import registrar_actividad
from controladores.personal import listar_personal
from PySide6.QtWidgets import QDoubleSpinBox

class ActividadDialog(QDialog):
    def __init__(self, parent=None, cursoAcademico_id=None):
        super().__init__(parent)
        self._cursoAcademico_id = cursoAcademico_id
        self.setWindowTitle("Nova activitat")

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.personal = QComboBox()
        for persona in listar_personal():
            if persona.get("apellido2") is None:
                nombre = f"{persona['apellido1']}, {persona['nombre']}".strip()
            else:
                nombre = f"{persona['apellido1']} {persona['apellido2']}, {persona['nombre']}".strip()
            self.personal.addItem(nombre, userData=persona["id"])
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(1)
        self.numMaxAlumnos.setMaximum(999)
        self.precioMatricula = QDoubleSpinBox()
        self.precioMatricula.setDecimals(2)
        self.precioMatricula.setMinimum(0.0)
        self.precioMatricula.setMaximum(999.99)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Professor/Voluntari:", self.personal)
        form.addRow("Preu matrícula:", self.precioMatricula)
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


    def _save(self):
        data = {
            "nombre": self.nombre.text().strip(),
            "descripcion": self.descripcion.text().strip(),
            "numMaxAlumnos": self.numMaxAlumnos.value(),
            "cursoAcademico_id": self._cursoAcademico_id,
            "personalID": self.personal.currentData(),
            "precio_matricula": self.precioMatricula.value(),
        }

        if not data["nombre"]:
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return
        
        registrar_actividad(data)

        self.accept()