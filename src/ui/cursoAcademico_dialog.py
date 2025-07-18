from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QDateEdit, QPushButton
from PySide6.QtCore import QDate
from controladores.curso_academico import registrar_cursoA

class CursoAcademicoFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nou Curs Acadèmic")

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.nom = QLineEdit()
        self.inici = QDateEdit()
        self.inici.setDate(QDate.currentDate())
        self.inici.setCalendarPopup(True)
        self.inici.setDisplayFormat("dd-MM-yyyy")

        self.fi = QDateEdit()
        self.fi.setDate(QDate.currentDate().addYears(1))
        self.fi.setCalendarPopup(True)
        self.fi.setDisplayFormat("dd-MM-yyyy")

        form_layout.addRow("Nom del curs:", self.nom)
        form_layout.addRow("Inici:", self.inici)
        form_layout.addRow("Fi:", self.fi)

        self.btn_crear = QPushButton("Crear")
        self.btn_crear.clicked.connect(self._guardar)

        layout.addLayout(form_layout)
        layout.addWidget(self.btn_crear)

        self.setLayout(layout)

    def _guardar(self):
        registrar_cursoA({
            "nombre": self.nom.text(),
            "fechaInicio": self.inici.date().toPython(),
            "fechaFin": self.fi.date().toPython()
        })
        self.accept()