from PySide6.QtWidgets import (
    QDialog, QLineEdit, QComboBox, QDateEdit, QSpinBox, QPushButton,
    QVBoxLayout, QFormLayout, QMessageBox
)
from controladores.actividades import registrar_actividad
from controladores.personal import listar_personal
from PySide6.QtWidgets import QDoubleSpinBox
from ui.theme import fit_combo_popup_to_contents, set_button_variant

class ActividadDialog(QDialog):
    def __init__(self, parent=None, cursoAcademico_id=None, tipo="CURS"):
        super().__init__(parent)
        self._cursoAcademico_id = cursoAcademico_id
        self._tipo = tipo
        self.setWindowTitle("Nou viatge" if tipo == "VIATGE" else "Nou curs")

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.personal = QComboBox()
        self.personal.setMinimumWidth(220)
        for persona in listar_personal():
            if persona.get("apellido2") is None:
                nombre = f"{persona['apellido1']}, {persona['nombre']}".strip()
            else:
                nombre = f"{persona['apellido1']} {persona['apellido2']}, {persona['nombre']}".strip()
            self.personal.addItem(nombre, userData=persona["id"])
        fit_combo_popup_to_contents(self.personal)
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(1)
        self.numMaxAlumnos.setMaximum(999)
        self.precioMatricula = QDoubleSpinBox()
        self.precioMatricula.setDecimals(2)
        self.precioMatricula.setMinimum(0.0)
        self.precioMatricula.setMaximum(999.99)

        form = QFormLayout()
        if tipo == "CURS":
            form.addRow("Nom:", self.nombre)
            form.addRow("Descripció:", self.descripcion)
            form.addRow("Professor/Voluntari:", self.personal)
            form.addRow("Preu matrícula:", self.precioMatricula)
            form.addRow("Màxim alumnes:", self.numMaxAlumnos)
        else:
            form.addRow("Nom del viatge:", self.nombre)
            form.addRow("Descripció / itinerari:", self.descripcion)
            form.addRow("Responsable:", self.personal)
            form.addRow("Preu viatge:", self.precioMatricula)
            form.addRow("Places:", self.numMaxAlumnos)

        btn_guardar = QPushButton("Guardar")
        btn_cancelar = QPushButton("Cancel·lar")
        set_button_variant(btn_guardar, "primary")
        set_button_variant(btn_cancelar, "secondary")
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
            "tipo": self._tipo,
        }

        if not data["nombre"]:
            QMessageBox.warning(self, "Error", "El nom és obligatori.")
            return
        
        registrar_actividad(data)

        self.accept()
