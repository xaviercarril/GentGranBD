from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout,
    QMessageBox, QComboBox, QTableView, QHeaderView, QStyledItemDelegate
)
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from controladores.inscripcion_socio import (
    consultar_actividadID_InscripcionSocio, consultar_socioID_InscripcionSocio, registrar_inscripcion, eliminar_inscripcion
)
from controladores.actividades import consultar_actividad, listar_actividades, listar_inscripciones_por_Actividad
from controladores.socios import consultar_socio, listar_inscripciones_por_socio
from datetime import date, datetime
from controladores.inscripcion_socio import modificar_inscripcion, listar_pagos_por_InscripcionSocio
from controladores.pagos import modificar_pago
from ui.table_models import DictTableModel


def _actividad_tipo_label(tipo) -> str:
    value = getattr(tipo, "value", tipo)
    return "Viatge" if value == "VIATGE" else "Curs"


class PagosTableModel(QAbstractTableModel):
    EDITABLE_KEYS = {"fecha_pago", "importe", "estado", "observaciones"}

    def __init__(self, rows, headers, payment_changed_callback, parent=None):
        super().__init__(parent)
        self.rows = rows or []
        self.labels, self.keys = zip(*headers)
        self._payment_changed_callback = payment_changed_callback

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.keys)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        key = self.keys[index.column()]
        value = self.rows[index.row()].get(key, "")

        if role in (Qt.DisplayRole, Qt.EditRole):
            if value is None:
                return "" if role == Qt.EditRole else "----"
            if key == "fecha_pago":
                return value.strftime("%d-%m-%Y") if isinstance(value, date) else str(value)
            if key == "importe":
                try:
                    return f"{float(value):.2f} €" if role == Qt.DisplayRole else f"{float(value):.2f}"
                except (TypeError, ValueError):
                    return str(value)
            return str(getattr(value, "value", value))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.labels[section]
        return super().headerData(section, orientation, role)

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and self.keys[index.column()] in self.EDITABLE_KEYS:
            return flags | Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False

        key = self.keys[index.column()]
        if key not in self.EDITABLE_KEYS:
            return False

        try:
            pago = self.rows[index.row()]
            new_value = self._parse_value(key, value)
            self._payment_changed_callback(pago["id"], key, new_value)
            pago[key] = new_value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except ValueError as e:
            QMessageBox.warning(None, "Error", str(e))
            return False

    def _parse_value(self, key, value):
        text = str(value).strip()
        if key == "fecha_pago":
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(text, fmt).date()
                except ValueError:
                    pass
            raise ValueError("La data ha de tenir format dd/mm/aaaa.")
        if key == "importe":
            text = text.replace("€", "").replace(",", ".").strip()
            try:
                parsed = float(text)
            except ValueError:
                raise ValueError("L'import ha de ser un número.")
            if parsed < 0:
                raise ValueError("L'import no pot ser negatiu.")
            return parsed
        if key == "estado":
            normalized = text.upper().replace("ANULAT", "ANUL·LAT")
            if normalized not in {"PENDENT", "PAGAT", "ANUL·LAT"}:
                raise ValueError("L'estat ha de ser PENDENT, PAGAT o ANUL·LAT.")
            return normalized
        return text or None


class EstadoPagoDelegate(QStyledItemDelegate):
    ESTADOS = ["PENDENT", "PAGAT", "ANUL·LAT"]

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self.ESTADOS)
        return combo

    def setEditorData(self, editor, index):
        value = str(index.model().data(index, Qt.EditRole) or "")
        pos = editor.findText(value)
        editor.setCurrentIndex(pos if pos >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class InscripcionesDialog(QDialog):
    def __init__(self, socio_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'inscripcions del soci")
        self.socio_id = socio_id

        self.left_layout = QVBoxLayout()

        self.combo_cursos = QComboBox()
        self.combo_cursos.currentIndexChanged.connect(self._carregar_inscripcions)
        self.left_layout.addWidget(QLabel("Curs acadèmic:"))
        self.left_layout.addWidget(self.combo_cursos)

        self.label = QLabel("Activitats inscrites:")
        self.left_layout.addWidget(self.label)

        self.lista_inscripciones = QListWidget()
        self.left_layout.addWidget(self.lista_inscripciones)

        btn_layout = QHBoxLayout()
        self.btn_afegir = QPushButton("Afegir inscripció")
        self.btn_eliminar = QPushButton("Eliminar inscripció")
        btn_layout.addWidget(self.btn_afegir)
        btn_layout.addWidget(self.btn_eliminar)
        self.left_layout.addLayout(btn_layout)

        self.pagos_table = QTableView()
        self.pagos_table.setMinimumWidth(400)
        self.pagos_table.setMinimumHeight(200)
        self.pagos_table.verticalHeader().setVisible(False)
        self.pagos_table.setSelectionBehavior(QTableView.SelectRows)
        self.pagos_table.setSelectionMode(QTableView.SingleSelection)
        self.pagos_table.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed)
        self.pagos_table.setAlternatingRowColors(True)
        self.pagos_table.horizontalHeader().setVisible(True)
        self.pagos_table.horizontalHeader().setStretchLastSection(True)

        self.btn_pagos_layout = QHBoxLayout()
        self.btn_afegir_pago = QPushButton("Afegir pagament")
        self.btn_afegir_pago.clicked.connect(self._afegir_pagament)
        self.btn_eliminar_pago = QPushButton("Eliminar pagament")
        self.btn_eliminar_pago.clicked.connect(self._eliminar_pagament)
        self.btn_pagos_layout.addWidget(self.btn_afegir_pago)
        self.btn_pagos_layout.addWidget(self.btn_eliminar_pago)

        pagos_layout = QVBoxLayout()
        pagos_layout.addLayout(self.btn_pagos_layout)
        pagos_layout.addWidget(self.pagos_table)

        main_layout = QHBoxLayout()
        main_layout.addLayout(self.left_layout)
        main_layout.addLayout(pagos_layout)
        self.setLayout(main_layout)
        self.setMinimumSize(800, 400)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 2)

        self.lista_inscripciones.currentRowChanged.connect(self._carregar_pagos)

        self.btn_afegir.clicked.connect(self._afegir_inscripcio)
        self.btn_eliminar.clicked.connect(self._eliminar_inscripcio)

        self._carregar_cursos()
        self._carregar_inscripcions()

    def _carregar_cursos(self):
        from controladores.curso_academico import listar_cursosA
        from datetime import date
        self._cursos = listar_cursosA()
        self.combo_cursos.clear()
        self.combo_cursos.addItem("Tots els cursos", userData=None)

        index_to_select = 0
        today = date.today()

        for i, curs in enumerate(self._cursos):
            self.combo_cursos.addItem(curs["nombre"], userData=curs["id"])
            if curs["fechaInicio"] <= today <= curs["fechaFin"]:
                index_to_select = i + 1  # +1 because "Tots els cursos" is at index 0

        self.combo_cursos.setCurrentIndex(index_to_select)

    def _carregar_inscripcions(self):
        self.lista_inscripciones.clear()
        curso_id = self.combo_cursos.currentData()
        self._inscripcions = [
            ins for ins in listar_inscripciones_por_socio(self.socio_id)
            if curso_id is None or consultar_actividad(ins["actividadID"])["cursoAcademico_id"] == curso_id
        ]
        for ins in self._inscripcions:
            actividadID = consultar_actividadID_InscripcionSocio(ins["id"])
            act = consultar_actividad(actividadID) if actividadID else None
            if act and (curso_id is None or act["cursoAcademico_id"] == curso_id):
                tipo = _actividad_tipo_label(act.get("tipo"))
                self.lista_inscripciones.addItem(
                    f"{act['nombre']} ({tipo}) - {ins['estado'].value} - {ins['fechaInscripcion'].strftime('%d-%m-%Y')}"
                )
        self._carregar_pagos(self.lista_inscripciones.currentRow())

    def _afegir_inscripcio(self):
        curso_id = self.combo_cursos.currentData()
        activitats = [a for a in listar_actividades() if curso_id is None or a["cursoAcademico_id"] == curso_id]
        opcions = {
            f"{a['nombre']} ({_actividad_tipo_label(a.get('tipo'))}, ID {a['id']})": a
            for a in activitats
        }

        from PySide6.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(
            self,
            "Selecciona una activitat",
            "Activitat:",
            list(opcions.keys()),
            0,
            False,
        )
        if ok and item:
            act = opcions.get(item)
            if act:
                ya_inscrito = any(
                    ins["actividadID"] == act["id"] for ins in self._inscripcions
                )
                if ya_inscrito:
                    QMessageBox.warning(self, "Error", f"El soci ja està inscrit a {item}.")
                    return
                inscripciones_actividad = [
                    ins for ins in listar_inscripciones_por_socio(self.socio_id)
                    if consultar_actividad(ins["actividadID"])["id"] == act["id"]
                ]

                inscripciones_todas = listar_inscripciones_por_Actividad(act["id"])
                inscritos_actuales = [
                    i for i in inscripciones_todas if i["estado"].value == "INSCRIT"
                ]
                estado = "INSCRIT" if len(inscritos_actuales) < act["numMaxAlumnos"] else "RESERVA"
                try:
                    registrar_inscripcion({
                        "socioID": self.socio_id,
                        "actividadID": act["id"],
                        "fechaInscripcion": date.today(),
                        "estado": estado,
                        "observaciones": ""
                    })
                    print(f"Inscripció a {item} registrada.")
                    self._carregar_inscripcions()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"No s'ha pogut afegir: {e}")

    def _eliminar_inscripcio(self):
        idx = self.lista_inscripciones.currentRow()
        if idx == -1:
            return
        if idx >= len(self._inscripcions):
            return
        inscripcio = self._inscripcions[idx]
        actividadID = consultar_actividadID_InscripcionSocio(inscripcio["id"])
        actividad_nombre = consultar_actividad(actividadID)["nombre"] if actividadID else "Desconeguda"
        reply = QMessageBox.question(
            self,
            "Confirmació",
            f"Segur que vols eliminar la inscripció a {actividad_nombre}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            eliminar_inscripcion(inscripcio["id"])
            self._actualitzar_reserves(actividadID)
            self._carregar_inscripcions()

    def _actualitzar_reserves(self, actividadID: int):
        from controladores.actividades import actualizar_estados_inscripciones
        actualizados = actualizar_estados_inscripciones(actividadID)
        if actualizados:
            for socio in actualizados:
                QMessageBox.information(
                    self,
                    "Reserva actualitzada",
                    f"Soci ID:{socio['id']}, {socio['nombre'] + ' ' + socio['apellido1']} ha passat de RESERVA a INSCRIT a {act['nombre']}"
                )
            self._carregar_inscripcions()

    def _carregar_pagos(self, index: int):
        if index < 0 or index >= len(self._inscripcions):
            self.pagos_table.setModel(DictTableModel([], []))
            return

        inscripcio = self._inscripcions[index]
        try:
            pagos = listar_pagos_por_InscripcionSocio(inscripcio["id"])
            headers = [
                ("Data", "fecha_pago"),
                ("Import", "importe"),
                ("Estat", "estado"),
                ("Observacions", "observaciones")
            ]
            self.pagos_table.setModel(PagosTableModel(pagos, headers, self._actualitzar_pagament, self))
            self.pagos_table.setItemDelegateForColumn(2, EstadoPagoDelegate(self.pagos_table))
            self.pagos_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut carregar els pagaments: {e}")

    def _actualitzar_pagament(self, pago_id: int, field: str, value):
        modificar_pago(pago_id, {field: value})


    def _afegir_pagament(self):
        from ui.pago_dialog import PagoDialog
        idx = self.lista_inscripciones.currentRow()
        if idx == -1 or idx >= len(self._inscripcions):
            QMessageBox.warning(self, "Error", "Selecciona una inscripció primer.")
            return

        inscripcio = self._inscripcions[idx]
        actividad = consultar_actividad(inscripcio["actividadID"])
        default_importe = actividad.get("precio_matricula", 0.0)

        dialog = PagoDialog(default_importe, self)
        if dialog.exec():
            data = dialog.get_data()
            data["socioID"] = inscripcio["socioID"]
            data["actividadID"] = inscripcio["actividadID"]
            data["inscripcionID"] = inscripcio["id"]

            from controladores.pagos import registrar_pago
            try:
                registrar_pago(data)
                self._carregar_pagos(idx)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No s'ha pogut registrar el pagament: {e}")

    def _eliminar_pagament(self):
        idx_inscripcio = self.lista_inscripciones.currentRow()
        idx_pago = self.pagos_table.currentIndex().row()
        
        if idx_inscripcio == -1 or idx_inscripcio >= len(self._inscripcions):
            QMessageBox.warning(self, "Error", "Selecciona una inscripció primer.")
            return
        
        if idx_pago == -1:
            QMessageBox.warning(self, "Error", "Selecciona un pagament per eliminar.")
            return
        
        inscripcio = self._inscripcions[idx_inscripcio]
        try:
            pagos = listar_pagos_por_InscripcionSocio(inscripcio["id"])
            if idx_pago >= len(pagos):
                QMessageBox.warning(self, "Error", "Pagament seleccionat invàlid.")
                return

            pago_id = pagos[idx_pago]["id"]

            from controladores.pagos import eliminar_pago
            confirmar = QMessageBox.question(
                self, "Confirmació", "Segur que vols eliminar el pagament seleccionat?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmar == QMessageBox.Yes:
                eliminar_pago(pago_id)
                self._carregar_pagos(idx_inscripcio)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'ha pogut eliminar el pagament: {e}")
