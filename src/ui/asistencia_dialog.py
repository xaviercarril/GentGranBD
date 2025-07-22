from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QTimeEdit, QSpinBox, QGroupBox, QWidget
)
from PySide6.QtCore import Qt, QTime
from controladores.socios import consultar_socio
from controladores.trimestre import listar_clases_por_trimestre
from controladores.curso_academico import listar_trimestres_por_cursoA
from controladores.actividades import listar_inscripciones_por_Actividad

class AsistenciaDialog(QDialog):
    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'assistència")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID

        self.trimestre_selector = QComboBox()
        self.dias_checkboxes = []
        dias_layout = QHBoxLayout()
        dias_nombres = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
        for i, nombre in enumerate(dias_nombres):
            cb = QCheckBox(nombre)
            cb.setProperty("weekday", i)
            dias_layout.addWidget(cb)
            self.dias_checkboxes.append(cb)
        dias_group = QGroupBox("Dies de la setmana")
        dias_group.setLayout(dias_layout)

        self.hora_inicio = QTimeEdit(QTime(9, 0))
        self.hora_fin = QTimeEdit(QTime(10, 0))
        self.intervalo_semanas = QSpinBox()
        self.intervalo_semanas.setMinimum(1)
        self.intervalo_semanas.setValue(1)

        self.generar_btn = QPushButton("Generar classes")
        self.table = QTableWidget()

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Trimestre:"))
        top_layout.addWidget(self.trimestre_selector)
        top_layout.addWidget(dias_group)
        top_layout.addWidget(QLabel("Inici:"))
        top_layout.addWidget(self.hora_inicio)
        top_layout.addWidget(QLabel("Fi:"))
        top_layout.addWidget(self.hora_fin)
        top_layout.addWidget(QLabel("Cada"))
        top_layout.addWidget(self.intervalo_semanas)
        top_layout.addWidget(QLabel("setmana/es"))
        top_layout.addWidget(self.generar_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)

        self.trimestre_selector.currentIndexChanged.connect(self._cargar_parrilla)
        self.generar_btn.clicked.connect(self._generar_clases)

        self._cargar_trimestres()

    def _cargar_trimestres(self):
        self.trimestres = listar_trimestres_por_cursoA(self.cursoAcademicoID)
        self.trimestre_selector.clear()
        for t in self.trimestres:
            self.trimestre_selector.addItem(str(t["nombre"]), t["id"])

    def _cargar_parrilla(self):
        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            return

        clases = listar_clases_por_trimestre(trimestre_id)
        inscripciones = listar_inscripciones_por_Actividad(self.actividadID)
        inscripciones = [i for i in inscripciones if i.get("estado").value == "INSCRIT"]

        self.table.clear()
        self.table.setStyleSheet("QTableWidget::item { padding: 10px; }")
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setWordWrap(True)
        self.table.setRowCount(len(inscripciones))
        self.table.setColumnCount(len(clases))
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        for col, clase in enumerate(clases):
            texto = clase["fecha"].strftime("%d/%m/%Y")
            if clase.get("horaInicio") and clase.get("horaFin"):
                texto += f"\n{clase['horaInicio'].strftime('%H:%M')}–{clase['horaFin'].strftime('%H:%M')}"
            item = QTableWidgetItem(texto)
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(col, item)

        for row, insc in enumerate(inscripciones):
            socio = consultar_socio(insc["socioID"])
            item = QTableWidgetItem(f"{socio['nombre']} {socio['apellido1']}")
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setVerticalHeaderItem(row, item)
            for col in range(len(clases)):
                cb = QCheckBox()
                cb.setChecked(False)
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(cb)
                layout.setAlignment(Qt.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, col, container)

    def _generar_clases(self):
        from controladores.clase import generar_clases_semana

        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            QMessageBox.warning(self, "Error", "Selecciona un trimestre")
            return

        dias_semana = [cb.property("weekday") for cb in self.dias_checkboxes if cb.isChecked()]
        if not dias_semana:
            QMessageBox.warning(self, "Error", "Selecciona almenys un dia de la setmana")
            return

        trimestre = next((t for t in self.trimestres if t["id"] == trimestre_id), None)
        if not trimestre:
            QMessageBox.warning(self, "Error", "Trimestre no trobat")
            return

        fecha_inicio = trimestre["fechaInicio"]
        fecha_fin = trimestre["fechaFin"]

        hora_inicio = self.hora_inicio.time().toPython()
        hora_fin = self.hora_fin.time().toPython()

        ok = QMessageBox.question(
            self,
            "Confirmar generació",
            f"Vols generar classes del {fecha_inicio} al {fecha_fin} per als dies seleccionats?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        try:
            generar_clases_semana(
                actividadID=self.actividadID,
                trimestreID=trimestre_id,
                fechaInicio=fecha_inicio,
                fechaFin=fecha_fin,
                horaInicio=hora_inicio,
                horaFin=hora_fin,
                cada_n_semanas=self.intervalo_semanas.value(),
                dias_semana=dias_semana
            )
            QMessageBox.information(self, "Èxit", "Classes generades correctament")
            self._cargar_parrilla()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut generar les classes:\n{e}")