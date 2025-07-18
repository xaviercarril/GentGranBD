

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QHBoxLayout, QLabel, QTableView
from PySide6.QtCore import Qt

class PersonalTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.subtabs = QTabWidget()
        self.professors_tab = QWidget()
        self.voluntarios_tab = QWidget()

        self.subtabs.addTab(self.professors_tab, "Professors")
        self.subtabs.addTab(self.voluntarios_tab, "Voluntaris")

        layout.addWidget(self.subtabs)

        self._init_professors_tab()
        self._init_voluntarios_tab()

    def _init_professors_tab(self):
        layout = QVBoxLayout()
        self.prof_table = QTableView()
        btn_layout = QHBoxLayout()
        btn_nou = QPushButton("Nou Professor")
        btn_eliminar = QPushButton("Eliminar")
        btn_layout.addWidget(btn_nou)
        btn_layout.addWidget(btn_eliminar)
        layout.addWidget(self.prof_table)
        layout.addLayout(btn_layout)
        self.professors_tab.setLayout(layout)

    def _init_voluntarios_tab(self):
        layout = QVBoxLayout()
        self.vol_table = QTableView()
        btn_layout = QHBoxLayout()
        btn_nou = QPushButton("Nou Voluntari")
        btn_eliminar = QPushButton("Eliminar")
        btn_layout.addWidget(btn_nou)
        btn_layout.addWidget(btn_eliminar)
        layout.addWidget(self.vol_table)
        layout.addLayout(btn_layout)
        self.voluntarios_tab.setLayout(layout)