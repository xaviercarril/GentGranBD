from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QTimeEdit, QSpinBox, QGroupBox, QWidget, QGridLayout, QTableWidgetSelectionRange
)
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QFileDialog
from controladores.socios import consultar_socio
from controladores.trimestre import listar_clases_por_trimestre
from controladores.curso_academico import listar_trimestres_por_cursoA
from controladores.actividades import consultar_actividad, listar_inscripciones_por_Actividad
from controladores.asistencia_socio import registrar_asistenciaSocio, eliminar_asistenciaSocio, consultar_asistenciaSocio, generar_pdf_asistencias
from controladores.clase import generar_clases_semana, registrar_clase


class AsistenciaDialog(QDialog):
    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.resize(1200, 700)
        self.setWindowTitle("Gestió d'assistència")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID
       
        self.trimestre_selector = QComboBox()
        self.btn_exportar = QPushButton("Exportar a PDF")
        self.btn_generar_dialog = QPushButton("Generar classes auto.")
        self.btn_añadir_manual = QPushButton("Afegir una classe")
        self.btn_generar_dialog.clicked.connect(self._abrir_dialog_generar)
        self.btn_añadir_manual.clicked.connect(self._abrir_dialog_afegir)
        self.btn_exportar.clicked.connect(self._exportar_asistencia_pdf)
        
        self.table = QTableWidget()

        top_layout = QHBoxLayout()
        label_trimestre = QLabel("Trimestre:")
        label_trimestre.setFixedWidth(70)
        top_layout.addWidget(label_trimestre)
        top_layout.addWidget(self.trimestre_selector)
        top_layout.addWidget(self.btn_exportar)
        top_layout.addWidget(self.btn_generar_dialog)
        top_layout.addWidget(self.btn_añadir_manual)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)

        self.trimestre_selector.currentIndexChanged.connect(self._cargar_parrilla)
        self._cargar_trimestres()

    def _cargar_trimestres(self):
        self.trimestres = listar_trimestres_por_cursoA(self.cursoAcademicoID)
        self.trimestre_selector.clear()
        for t in self.trimestres:
            self.trimestre_selector.addItem(str(t["nombre"].value), t["id"])

    def _cargar_parrilla(self):
        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            return

        clases = [c for c in listar_clases_por_trimestre(trimestre_id) if c["actividadID"] == self.actividadID]
        clases.sort(key=lambda c: (c["fecha"], c.get("horaInicio")))
        inscripciones = listar_inscripciones_por_Actividad(self.actividadID)
        inscripciones = [i for i in inscripciones if i.get("estado").value == "INSCRIT"]
        # Inicializar cell_widgets
        self.cell_widgets = [[None for _ in range(len(clases))] for _ in range(len(inscripciones))]

        self.table.setStyleSheet("""
            QTableWidget::item {
                padding: 10px;
                border: 1px solid #cccccc;
                background-color: #fdfdfd;
            }
            QTableWidget::item:selected {
                background-color: #d0e8ff;
            }
        """)
        self.table.clear()
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setWordWrap(True)
        self.table.setRowCount(len(inscripciones))
        self.table.setColumnCount(len(clases))
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.horizontalHeader().setDefaultSectionSize(90)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # Habilitar el botón de la esquina superior izquierda de la tabla
        self.table.setCornerButtonEnabled(True)

        from collections import defaultdict
        meses = defaultdict(list)
        for col, clase in enumerate(clases):
            fecha = clase["fecha"]
            texto = fecha.strftime("%d/%m")
            if clase.get("horaInicio") and clase.get("horaFin"):
                texto += f"\n{clase['horaInicio'].strftime('%H:%M')}–{clase['horaFin'].strftime('%H:%M')}"
            item = QTableWidgetItem(texto)
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(col, item)
            meses[fecha.strftime("%B %Y")].append(col)

        # Aplicar color o separación visual por mes
        for i, (mes, columnas) in enumerate(meses.items()):
            color = "#e6f2ff" if i % 2 == 0 else "#ffffff"
            for col in columnas:
                for row in range(self.table.rowCount()):
                    cell = self.table.cellWidget(row, col)
                    if cell:
                        cell.setStyleSheet(f"background-color: {color}; border-radius: 4px;")

        for row, insc in enumerate(inscripciones):
            socio = consultar_socio(insc["socioID"])
            item = QTableWidgetItem(f"{socio['nombre']} {socio['apellido1']}")
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setVerticalHeaderItem(row, item)
            for col in range(len(clases)):
                cb = QCheckBox()
                cb.setStyleSheet("QCheckBox { margin-left: auto; margin-right: auto; }")
                asiste = consultar_asistenciaSocio(insc["socioID"], clases[col]["id"])
                cb.setChecked(asiste is not None)
                cb.stateChanged.connect(lambda _, s=insc["socioID"], c=clases[col]["id"], ch=cb: self._guardar_asistencia(s, c, ch))
                container = QWidget()
                container.setStyleSheet("background-color: white; border-radius: 4px;")
                layout = QHBoxLayout(container)
                layout.addWidget(cb)
                layout.setAlignment(Qt.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, col, container)
                self.cell_widgets[row][col] = container
        # Habilitar selección completa de filas y columnas
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)
        self.table.verticalHeader().sectionClicked.connect(lambda row: self._seleccionar_fila(row))
        self.table.horizontalHeader().sectionClicked.connect(lambda col: self._seleccionar_columna(col))

    def _reset_colores(self):
        for fila in range(len(self.cell_widgets)):
            for col in range(len(self.cell_widgets[fila])):
                if self.cell_widgets[fila][col]:
                    self.cell_widgets[fila][col].setStyleSheet("background-color: white; border-radius: 4px;")

    def _seleccionar_columna(self, columna):
        # Permitir aplicar cambios a todas las columnas seleccionadas si hay más de una
        columnas = sorted(set(index.column() for index in self.table.selectedIndexes()))
        if len(columnas) > 1:
            for col in columnas:
                self._seleccionar_columna(col)
            return
        self._reset_colores()
        self.table.clearSelection()
        self.table.selectColumn(columna)
        for fila in range(len(self.cell_widgets)):
            if self.cell_widgets[fila][columna]:
                self.cell_widgets[fila][columna].setStyleSheet("background-color: #d0e8ff; border-radius: 4px;")
        # Marcar/desmarcar todos los checkboxes de la columna
        todos_marcados = all(
            self.cell_widgets[fila][columna].findChild(QCheckBox).isChecked()
            for fila in range(len(self.cell_widgets))
            if self.cell_widgets[fila][columna]
        )
        for fila in range(len(self.cell_widgets)):
            if self.cell_widgets[fila][columna]:
                checkbox = self.cell_widgets[fila][columna].findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not todos_marcados)

    def _seleccionar_fila(self, fila):
        # Permitir aplicar cambios a todas las filas seleccionadas si hay más de una
        filas = sorted(set(index.row() for index in self.table.selectedIndexes()))
        if len(filas) > 1:
            for f in filas:
                self._seleccionar_fila(f)
            return
        self._reset_colores()
        self.table.clearSelection()
        self.table.selectRow(fila)
        for col in range(len(self.cell_widgets[fila])):
            if self.cell_widgets[fila][col]:
                self.cell_widgets[fila][col].setStyleSheet("background-color: #d0e8ff; border-radius: 4px;")
        # Marcar/desmarcar todos los checkboxes de la fila
        todos_marcados = all(
            self.cell_widgets[fila][col].findChild(QCheckBox).isChecked()
            for col in range(len(self.cell_widgets[fila]))
            if self.cell_widgets[fila][col]
        )
        for col in range(len(self.cell_widgets[fila])):
            if self.cell_widgets[fila][col]:
                checkbox = self.cell_widgets[fila][col].findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not todos_marcados)
    
    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeyEvent
        from controladores.clase import eliminar_clase
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key_Delete:
            columnas = sorted(set(index.column() for index in self.table.selectedIndexes()))
            if not columnas:
                return
            trimestre_id = self.trimestre_selector.currentData()
            clases = [c for c in listar_clases_por_trimestre(trimestre_id) if c["actividadID"] == self.actividadID]
            clases_a_eliminar = [clases[col] for col in columnas if col < len(clases)]
            if not clases_a_eliminar:
                return
            confirm = QMessageBox.question(self, "Confirmar eliminació",
                                           f"Vols eliminar {len(clases_a_eliminar)} classe(s) seleccionada(es)?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                for clase in clases_a_eliminar:
                    eliminar_clase(clase["id"])
                self._cargar_parrilla()

    def _guardar_asistencia(self, socio_id, clase_id, checkbox):
        if checkbox.isChecked():
            registrar_asistenciaSocio({
                "socioID": socio_id,
                "claseID": clase_id,
                "presente": True
            })
        else:
            eliminar_asistenciaSocio(socio_id, clase_id)

    def _abrir_dialog_generar(self):
        dlg = GenerarClasesDialog(self.actividadID, self.cursoAcademicoID, self)
        if dlg.exec():
            self._cargar_parrilla()

    def _abrir_dialog_afegir(self):
        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            QMessageBox.warning(self, "Error", "Selecciona un trimestre primer")
            return
        dlg = AñadirClaseDialog(self.actividadID, trimestre_id, self)
        if dlg.exec():
            self._cargar_parrilla()

    def _exportar_asistencia_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(self, f"Desar PDF", f"assistencia-{consultar_actividad(self.actividadID)['nombre']}.pdf", "PDF Files (*.pdf)")
        if not ruta:
            return
        
        trimestre_id = self.trimestre_selector.currentData()

        try:
            generar_pdf_asistencias(self.actividadID, trimestre_id, ruta)
            QMessageBox.information(self, "Èxit", "El PDF s'ha generat correctament.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")
            
class GenerarClasesDialog(QDialog):
    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar classes automàticament")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID

        from controladores.curso_academico import listar_trimestres_por_cursoA
        self.trimestres = listar_trimestres_por_cursoA(cursoAcademicoID)

        self.trimestre_selector = QComboBox()
        for t in self.trimestres:
            self.trimestre_selector.addItem(str(t["nombre"].value), t["id"])

        self.dias_checkboxes = []
        dias_layout = QGridLayout()
        dias_nombres = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
        for i, nombre in enumerate(dias_nombres):
            cb = QCheckBox(nombre)
            cb.setProperty("weekday", i)
            dias_layout.addWidget(cb, i // 4, i % 4)
            self.dias_checkboxes.append(cb)
        dias_group = QGroupBox("Dies de la setmana")
        dias_group.setLayout(dias_layout)

        self.hora_inicio = QTimeEdit(QTime(9, 0))
        self.hora_fin = QTimeEdit(QTime(10, 0))
        self.intervalo_semanas = QSpinBox()
        self.intervalo_semanas.setMinimum(1)
        self.intervalo_semanas.setValue(1)

        btn_ok = QPushButton("Generar")
        btn_ok.clicked.connect(self._generar_clases)

        layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Trimestre:"), 0, 0)
        form_layout.addWidget(self.trimestre_selector, 0, 1)
        form_layout.addWidget(QLabel("Dies de la setmana:"), 1, 0)
        form_layout.addWidget(dias_group, 1, 1)
        form_layout.addWidget(QLabel("Hora inici:"), 2, 0)
        form_layout.addWidget(self.hora_inicio, 2, 1)
        form_layout.addWidget(QLabel("Hora fi:"), 3, 0)
        form_layout.addWidget(self.hora_fin, 3, 1)
        form_layout.addWidget(QLabel("Cada N setmanes:"), 4, 0)
        form_layout.addWidget(self.intervalo_semanas, 4, 1)

        layout.addLayout(form_layout)
        layout.addWidget(btn_ok)

    def _generar(self):
        trimestre_id = self.trimestre_selector.currentData()
        dias_semana = [cb.property("weekday") for cb in self.dias_checkboxes if cb.isChecked()]
        trimestre = next((t for t in self.trimestres if t["id"] == trimestre_id), None)

        if not trimestre or not dias_semana:
            QMessageBox.warning(self, "Error", "Trimestre o dies no vàlids")
            return

        try:
            generar_clases_semana(
                actividadID=self.actividadID,
                trimestreID=trimestre_id,
                fechaInicio=trimestre["fechaInicio"],
                fechaFin=trimestre["fechaFin"],
                horaInicio=self.hora_inicio.time().toPython(),
                horaFin=self.hora_fin.time().toPython(),
                cada_n_semanas=self.intervalo_semanas.value(),
                dias_semana=dias_semana
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'han pogut generar les classes:\n{e}")

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
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut generar les classes:\n{e}")


class AñadirClaseDialog(QDialog):
    def __init__(self, actividadID, trimestreID, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir una classe manualment")
        self.actividadID = actividadID
        self.trimestreID = trimestreID

        from PySide6.QtWidgets import QDateEdit
        from datetime import datetime

        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDate(datetime.today().date())
        self.hora_inicio = QTimeEdit(QTime(9, 0))
        self.hora_fin = QTimeEdit(QTime(10, 0))

        form = QVBoxLayout()
        form.addWidget(QLabel("Data de la classe:"))
        form.addWidget(self.fecha)
        form.addWidget(QLabel("Hora inici:"))
        form.addWidget(self.hora_inicio)
        form.addWidget(QLabel("Hora fi:"))
        form.addWidget(self.hora_fin)

        btn_ok = QPushButton("Afegir")
        btn_ok.clicked.connect(self._afegir)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn_ok)

    def _afegir(self):
        try:
            registrar_clase({
                "actividadID": self.actividadID,
                "trimestreID": self.trimestreID,
                "fecha": self.fecha.date().toPython(),
                "horaInicio": self.hora_inicio.time().toPython(),
                "horaFin": self.hora_fin.time().toPython()
            })
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut afegir la classe:\n{e}")




    