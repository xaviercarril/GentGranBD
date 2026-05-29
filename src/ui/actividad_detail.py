from datetime import date, datetime
import re
import tempfile

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QSpinBox, QMessageBox, QVBoxLayout,
    QTextEdit, QComboBox, QDoubleSpinBox, QTableView, QLabel, QPushButton,
    QHBoxLayout, QSizePolicy, QStyledItemDelegate
)
from controladores.actividades import consultar_actividad, modificar_actividad, listar_inscripciones_por_Actividad, actualizar_estados_inscripciones
from controladores.inscripcion_socio import eliminar_inscripcion, modificar_inscripcion, registrar_inscripcion, listar_pagos_por_InscripcionSocio
from controladores.pagos import modificar_pago, registrar_pago
from controladores.personal import consultar_personal, listar_personal
from controladores.socios import consultar_socio
from exportador.pdf_inscripciones import generar_pdf_matriculados_actividad
from models import EstadoInscripcion
from ui.seleccionar_socio_dialog import SeleccionarSocioDialog
from ui.table_models import DictTableModel


class InscripcionesActividadTableModel(QAbstractTableModel):
    EDITABLE_KEYS = {"fechaInscripcion", "observaciones", "pagat"}

    def __init__(self, rows, headers, inscription_changed_callback, parent=None):
        super().__init__(parent)
        self.rows = rows or []
        self.labels, self.keys = zip(*headers)
        self._inscription_changed_callback = inscription_changed_callback

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
            if isinstance(value, date):
                return value.strftime("%d/%m/%Y")
            if value is None:
                return ""
            return str(value)

        if role == Qt.BackgroundRole and self.rows[index.row()].get("estado") == EstadoInscripcion.RESERVA.value:
            return QColor("#fff4cf")

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
            inscripcion = self.rows[index.row()]
            if key == "fechaInscripcion":
                new_value = self._parse_date(value)
            elif key == "pagat":
                new_value = self._parse_pagat(value)
            else:
                text = str(value).strip()
                new_value = text or None
            self._inscription_changed_callback(inscripcion["id"], key, new_value)
            inscripcion[key] = new_value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except ValueError as e:
            QMessageBox.warning(None, "Error", str(e))
            return False

    def sort(self, column, order=Qt.AscendingOrder):
        key = self.keys[column]
        reverse = order == Qt.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self.rows.sort(key=lambda row: self._sort_value(row.get(key)), reverse=reverse)
        self.layoutChanged.emit()

    def _sort_value(self, value):
        if value is None:
            return ""
        if isinstance(value, date):
            return value
        return str(value).lower()

    def _parse_date(self, value):
        text = str(value).strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        raise ValueError("La data ha de tenir format dd/mm/aaaa.")

    def _parse_pagat(self, value):
        text = str(value).strip().lower()
        if text in {"sí", "si", "s", "yes", "pagat", "pagado", "true", "1"}:
            return "Sí"
        if text in {"no", "n", "pendent", "pendiente", "false", "0"}:
            return "No"
        raise ValueError("El camp Pagat ha de ser Sí o No.")


class PagatDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(["No", "Sí"])
        return combo

    def setEditorData(self, editor, index):
        value = str(index.model().data(index, Qt.EditRole) or "No")
        pos = editor.findText(value)
        editor.setCurrentIndex(pos if pos >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actividadID = None
        self._loading = False
        self._inscripciones = []
        self._tipo_actividad = "CURS"

        self.nombre = QLineEdit()
        self.personal = QComboBox()
        self._refresh_personal()
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(0)
        self.numMaxAlumnos.setMaximum(999)
        self.preuMatricula = QDoubleSpinBox()
        self.preuMatricula.setDecimals(2)
        self.descripcion = QTextEdit()
        self.descripcion.setFixedHeight(95)
        self.socio_preview = QLabel("Sense foto")
        self.socio_preview.setFixedSize(115, 135)
        self.socio_preview.setAlignment(Qt.AlignCenter)
        self.socio_preview.setStyleSheet("border: 1px solid #888; color: #777; font-size: 12px;")
        detail_field_style = "font-size: 14px;"
        for widget in (
            self.nombre,
            self.personal,
            self.numMaxAlumnos,
            self.preuMatricula,
            self.descripcion,
        ):
            widget.setStyleSheet(detail_field_style)
        self.nombre.setAlignment(Qt.AlignLeft)
        self.numMaxAlumnos.setAlignment(Qt.AlignLeft)
        self.preuMatricula.setAlignment(Qt.AlignLeft)
        self.descripcion.setAlignment(Qt.AlignLeft)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label_nom = QLabel("Nom:")
        self.label_personal = QLabel("Professor/Voluntari:")
        self.label_maxim = QLabel("Màxim alumnes:")
        self.label_preu = QLabel("Preu matrícula:")
        form.addRow(self.label_nom, self.nombre)
        form.addRow(self.label_personal, self.personal)
        form.addRow(self.label_maxim, self.numMaxAlumnos)
        form.addRow(self.label_preu, self.preuMatricula)

        layout = QVBoxLayout(self)
        self.details_panel = QWidget()
        self.details_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)
        top_layout = QHBoxLayout()
        top_layout.addLayout(form, stretch=1)
        top_layout.addWidget(self.socio_preview, alignment=Qt.AlignTop | Qt.AlignRight)
        details_layout.addLayout(top_layout)
        self.label_descripcio = QLabel("Descripció:")
        details_layout.addWidget(self.label_descripcio)
        details_layout.addWidget(self.descripcion)
        layout.addWidget(self.details_panel)

        self.label_inscrits = QLabel("INSCRITS: 0/0")
        self.label_inscrits.setStyleSheet("font-weight: 600;")

        btn_layout = QHBoxLayout()
        self.btn_afegir_soci = QPushButton("Afegir soci")
        self.btn_eliminar_inscripcio = QPushButton("Eliminar inscripció")
        self.btn_refrescar = QPushButton("Refrescar")
        self.btn_exportar_pdf = QPushButton("Exportar PDF")
        self.btn_exportar_excel = QPushButton("Exportar Excel")
        self.btn_afegir_soci.setIcon(QIcon("ui/assets/plus.svg"))
        self.btn_eliminar_inscripcio.setIcon(QIcon("ui/assets/minus.svg"))
        self.btn_refrescar.setIcon(QIcon("ui/assets/refresh.svg"))
        self.btn_exportar_pdf.setIcon(QIcon("ui/assets/pdf.svg"))
        self.btn_exportar_excel.setIcon(QIcon("ui/assets/excel.svg"))
        btn_layout.addWidget(self.btn_afegir_soci)
        btn_layout.addWidget(self.btn_eliminar_inscripcio)
        btn_layout.addWidget(self.btn_refrescar)
        btn_layout.addWidget(self.btn_exportar_pdf)
        btn_layout.addWidget(self.btn_exportar_excel)
        btn_layout.addStretch()

        self.inscrits_table = QTableView()
        self.inscrits_table.verticalHeader().setVisible(False)
        self.inscrits_table.setSelectionBehavior(QTableView.SelectRows)
        self.inscrits_table.setSelectionMode(QTableView.SingleSelection)
        self.inscrits_table.setAlternatingRowColors(True)
        self.inscrits_table.setSortingEnabled(True)
        self.inscrits_table.setMinimumHeight(300)

        self.inscrits_panel = QWidget()
        self.inscrits_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        inscrits_layout = QVBoxLayout(self.inscrits_panel)
        inscrits_layout.setContentsMargins(0, 0, 0, 0)
        inscrits_layout.addWidget(self.label_inscrits)
        inscrits_layout.addLayout(btn_layout)
        inscrits_layout.addWidget(self.inscrits_table)
        layout.addWidget(self.inscrits_panel)
        layout.addStretch()

        self.nombre.editingFinished.connect(self._on_editing_finished)
        self.descripcion.focusOutEvent = self._wrap_focus_out(self.descripcion.focusOutEvent)
        self.personal.currentTextChanged.connect(self._on_editing_finished)
        self.numMaxAlumnos.editingFinished.connect(self._on_editing_finished)
        self.preuMatricula.editingFinished.connect(self._on_editing_finished)
        self.btn_afegir_soci.clicked.connect(self._afegir_soci)
        self.btn_eliminar_inscripcio.clicked.connect(self._eliminar_inscripcio)
        self.btn_refrescar.clicked.connect(self._refresh_inscripcions)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf)
        self.btn_exportar_excel.clicked.connect(self._exportar_excel)
        self._set_inscription_actions_enabled(False)
        self.set_tipo_actividad("CURS")

    def _on_editing_finished(self):
        if not self._loading:
            self._save()

    def set_tipo_actividad(self, tipo):
        value = getattr(tipo, "value", tipo) or "CURS"
        self._tipo_actividad = value
        is_viatge = value == "VIATGE"

        self.label_nom.setText("Nom del viatge:" if is_viatge else "Nom:")
        self.label_personal.setText("Responsable:" if is_viatge else "Professor/Voluntari:")
        self.label_maxim.setText("Places:" if is_viatge else "Màxim alumnes:")
        self.label_preu.setText("Preu viatge:" if is_viatge else "Preu matrícula:")
        self.label_descripcio.setText("Descripció / itinerari:" if is_viatge else "Descripció:")
        self.btn_afegir_soci.setText("Afegir participant" if is_viatge else "Afegir soci")
        self.btn_exportar_excel.setVisible(is_viatge)
        self._update_inscrits_counter()

    def set_top_section_height(self, height):
        fixed_overhead = self.details_panel.sizeHint().height() - self.descripcion.height()
        self.descripcion.setFixedHeight(max(80, height - fixed_overhead))

    def load(self, actividadID):
        self._loading = True
        self._actividadID = actividadID

        if actividadID is None:
            self._clear()
            self._loading = False
            return

        act = consultar_actividad(actividadID)
        if not act:
            QMessageBox.warning(self, "Error", "Activitat no trobada.")
            self._clear()
            self._loading = False
            return

        self.set_tipo_actividad(act.get("tipo"))
        self.nombre.setText(act.get("nombre", ""))

        self._refresh_personal()
        personalID = act.get("personalID")
        if personalID is None:
            self.personal.setCurrentText("Desconegut")
        else:
            personal = consultar_personal(personalID)
            if personal.get("apellido2") is None:
                self.personal.setCurrentText(f"{personal['apellido1']}, {personal['nombre']}".strip())
            else:
                self.personal.setCurrentText(
                    f"{personal.get('apellido1', '')} {personal.get('apellido2', '')}, {personal.get('nombre', '')}".strip()
                )

        numMaxAlumnos = act.get("numMaxAlumnos")
        if numMaxAlumnos is None:
            self.numMaxAlumnos.setValue(0)
        else:
            self.numMaxAlumnos.setValue(numMaxAlumnos)

        self.preuMatricula.setValue(act.get("precio_matricula", 0.0))
        self.preuMatricula.setMinimum(0.0)
        self.preuMatricula.setMaximum(999.99)
        self.descripcion.setText(act.get("descripcion", ""))

        self._load_inscrits_table()
        self._set_inscription_actions_enabled(True)
        self._loading = False

    def _load_inscrits_table(self):
        try:
            inscripciones = listar_inscripciones_por_Actividad(self._actividadID)
            dni_label = "DNI" if self._tipo_actividad == "VIATGE" else "DNI/NIE"
            headers = [
                ("ID", "id"),
                ("Nom", "nombre"),
                ("Primer cognom", "apellido1"),
                ("Segon cognom", "apellido2"),
                (dni_label, "dniNie"),
                ("Soci", "esSocio"),
            ]
            if self._tipo_actividad == "VIATGE":
                headers.append(("Pagat", "pagat"))
            headers.extend(
                [
                    ("Data Inscripció", "fechaInscripcion"),
                    ("Estat", "estado"),
                    ("Observacions", "observaciones"),
                ]
            )
            for inscripcion in inscripciones:
                socio_id = inscripcion.get("socioID")
                socio = consultar_socio(socio_id) if socio_id else None
                inscripcion["estado"] = self._estado_value(inscripcion["estado"])
                if socio:
                    inscripcion["nombre"] = socio.get("nombre", "")
                    inscripcion["apellido1"] = socio.get("apellido1", "")
                    inscripcion["apellido2"] = socio.get("apellido2", "")
                    inscripcion["dniNie"] = socio.get("dniNie", "")
                    inscripcion["esSocio"] = "Sí"
                    
                else:
                    inscripcion["nombre"] = inscripcion.get("noSocioNombre") or "Desconegut"
                    inscripcion["apellido1"] = inscripcion.get("noSocioApellido1") or ""
                    inscripcion["apellido2"] = inscripcion.get("noSocioApellido2") or ""
                    inscripcion["dniNie"] = inscripcion.get("noSocioDni") or ""
                    inscripcion["esSocio"] = "No"
                if self._tipo_actividad == "VIATGE":
                    self._set_pagat_info(inscripcion)
            self._inscripciones = inscripciones
            self._update_inscrits_counter()
            self.inscrits_table.setModel(
                InscripcionesActividadTableModel(
                    self._inscripciones,
                    headers,
                    self._update_inscripcion_field,
                    self,
                )
            )
            if self._tipo_actividad == "VIATGE":
                model = self.inscrits_table.model()
                pagat_col = model.keys.index("pagat") if model and "pagat" in model.keys else -1
                if pagat_col >= 0:
                    self.inscrits_table.setItemDelegateForColumn(pagat_col, PagatDelegate(self.inscrits_table))
            self.inscrits_table.hideColumn(0)
            self.inscrits_table.resizeColumnsToContents()
            selection_model = self.inscrits_table.selectionModel()
            if selection_model:
                selection_model.currentRowChanged.connect(self._update_selected_socio_photo)
            self._clear_socio_preview()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut carregar les inscripcions: {e}")

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.numMaxAlumnos.setValue(0)
        self._inscripciones = []
        label = "PARTICIPANTS" if self._tipo_actividad == "VIATGE" else "INSCRITS"
        self.label_inscrits.setText(f"{label}: 0/0")
        self.inscrits_table.setModel(DictTableModel([], []))
        self._clear_socio_preview()
        self._set_inscription_actions_enabled(False)

    def _validar(self) -> bool:
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El camp 'Nom' és obligatori.")
            return False
        return True

    def _build_data(self) -> dict:
        return {
            "nombre": self.nombre.text().strip(),
            "personalID": self.personal.currentData(),
            "numMaxAlumnos": self.numMaxAlumnos.value(),
            "precio_matricula": self.preuMatricula.value(),
            "descripcion": self.descripcion.toPlainText().strip() or None,
        }

    def _save(self):
        if self._loading or self._actividadID is None:
            return

        if not self._validar():
            QMessageBox.warning(self, "Error", "Dades incompletes o incorrectes.")
            return  

        data = self._build_data()
        try:
            modificar_actividad(self._actividadID, data)
            actualizar_estados_inscripciones(self._actividadID)
            self._load_inscrits_table()
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _afegir_soci(self):
        if self._actividadID is None:
            return

        excluded_socio_ids = [ins["socioID"] for ins in self._inscripciones if ins.get("socioID")]
        dialog = SeleccionarSocioDialog(excluded_socio_ids=excluded_socio_ids, parent=self)
        if not dialog.exec():
            return

        socio = dialog.selected_socio()
        if not socio:
            return

        estado = EstadoInscripcion.RESERVA.value
        max_alumnes = self.numMaxAlumnos.value()
        inscrits_actuals = [
            ins for ins in self._inscripciones
            if ins.get("estado") == EstadoInscripcion.INSCRIT.value
        ]
        if max_alumnes > 0 and len(inscrits_actuals) < max_alumnes:
            estado = EstadoInscripcion.INSCRIT.value

        try:
            data = {
                "socioID": socio.get("id"),
                "actividadID": self._actividadID,
                "fechaInscripcion": date.today(),
                "estado": estado,
                "observaciones": "",
            }
            if socio.get("es_socio") is False:
                data["noSocioNombre"] = socio.get("noSocioNombre")
                data["noSocioApellido1"] = socio.get("noSocioApellido1")
                data["noSocioApellido2"] = socio.get("noSocioApellido2")
                data["noSocioDni"] = socio.get("noSocioDni")
                data["noSocioTelefono"] = socio.get("noSocioTelefono")
                data["noSocioEmail"] = socio.get("noSocioEmail")
                data["noSocioObservaciones"] = socio.get("noSocioObservaciones")
            registrar_inscripcion(data)
            actualizar_estados_inscripciones(self._actividadID)
            self._refresh_inscripcions()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'ha pogut afegir el soci: {e}")

    def _eliminar_inscripcio(self):
        row = self.inscrits_table.currentIndex().row()
        model = self.inscrits_table.model()
        if model is None or row < 0 or row >= len(model.rows):
            QMessageBox.warning(self, "Error", "Selecciona una inscripció primer.")
            return

        inscripcio = model.rows[row]
        nom = " ".join(
            value for value in [
                inscripcio.get("nombre", ""),
                inscripcio.get("apellido1", ""),
                inscripcio.get("apellido2", ""),
            ] if value
        )
        reply = QMessageBox.question(
            self,
            "Confirmació",
            f"Segur que vols eliminar la inscripció de {nom or 'aquest soci'}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            eliminar_inscripcion(inscripcio["id"])
            actualizar_estados_inscripciones(self._actividadID)
            self._refresh_inscripcions()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'ha pogut eliminar la inscripció: {e}")

    def _refresh_inscripcions(self):
        if self._actividadID is None:
            return
        actualizar_estados_inscripciones(self._actividadID)
        self._load_inscrits_table()
        self.saved.emit()

    def _update_inscripcion_field(self, inscripcion_id, field, value):
        if field == "pagat":
            self._update_pagat_field(inscripcion_id, value)
            self.saved.emit()
            return

        modificar_inscripcion(inscripcion_id, {field: value})
        if field == "fechaInscripcion":
            actualizar_estados_inscripciones(self._actividadID)
            QTimer.singleShot(0, self._load_inscrits_table)
        self.saved.emit()

    def _set_pagat_info(self, inscripcion):
        pago = self._latest_pago(inscripcion)
        inscripcion["_pago_id"] = pago.get("id") if pago else None
        estado = self._estado_value(pago.get("estado")) if pago else None
        inscripcion["pagat"] = "Sí" if estado == "PAGAT" else "No"

    def _latest_pago(self, inscripcion):
        try:
            pagos = listar_pagos_por_InscripcionSocio(inscripcion["id"])
        except Exception:
            return None
        if not pagos:
            return None
        return sorted(
            pagos,
            key=lambda pago: (pago.get("fecha_pago") or date.min, pago.get("id") or 0),
        )[-1]

    def _update_pagat_field(self, inscripcion_id, value):
        inscripcion = next((ins for ins in self._inscripciones if ins.get("id") == inscripcion_id), None)
        if not inscripcion:
            raise ValueError("Inscripció no trobada.")
        estado = "PAGAT" if value == "Sí" else "PENDENT"
        pago_id = inscripcion.get("_pago_id")
        if pago_id:
            modificar_pago(pago_id, {"estado": estado})
        else:
            pago_id = registrar_pago(
                {
                    "socioID": inscripcion["socioID"],
                    "actividadID": self._actividadID,
                    "inscripcionID": inscripcion_id,
                    "fecha_pago": date.today(),
                    "importe": self.preuMatricula.value(),
                    "estado": estado,
                    "observaciones": "",
                }
            )
            inscripcion["_pago_id"] = pago_id
        inscripcion["pagat"] = value

    def _exportar_pdf(self):
        if self._actividadID is None:
            return

        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", self.nombre.text()).strip("_") or "activitat"
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f"matriculats-{nombre}-",
                suffix=".pdf",
                delete=False,
            ) as tmp:
                ruta = tmp.name
            generar_pdf_matriculados_actividad(self._actividadID, ruta)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
                QMessageBox.warning(
                    self,
                    "Avís",
                    f"No s'ha pogut obrir el visor PDF del sistema.\nPDF temporal: {ruta}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")

    def _exportar_excel(self):
        if self._actividadID is None:
            return

        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", self.nombre.text()).strip("_") or "viatge"
        try:
            from exportador.excel_participantes import generar_excel_participantes_viaje

            with tempfile.NamedTemporaryFile(
                prefix=f"participants-{nombre}-",
                suffix=".xlsx",
                delete=False,
            ) as tmp:
                ruta = tmp.name
            generar_excel_participantes_viaje(self._actividadID, ruta)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
                QMessageBox.warning(
                    self,
                    "Avís",
                    f"No s'ha pogut obrir l'Excel del sistema.\nFitxer temporal: {ruta}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar l'Excel:\n{e}")

    def _update_inscrits_counter(self):
        inscrits = sum(
            1 for ins in self._inscripciones
            if ins.get("estado") == EstadoInscripcion.INSCRIT.value
        )
        label = "PARTICIPANTS" if self._tipo_actividad == "VIATGE" else "INSCRITS"
        self.label_inscrits.setText(f"{label}: {inscrits}/{self.numMaxAlumnos.value()}")

    def _set_inscription_actions_enabled(self, enabled):
        self.btn_afegir_soci.setEnabled(enabled)
        self.btn_eliminar_inscripcio.setEnabled(enabled)
        self.btn_refrescar.setEnabled(enabled)
        self.btn_exportar_pdf.setEnabled(enabled)
        self.btn_exportar_excel.setEnabled(enabled)

    def _estado_value(self, estado):
        return getattr(estado, "value", estado)

    def _update_selected_socio_photo(self, current, previous):
        if not current.isValid():
            self._clear_socio_preview()
            return

        model = self.inscrits_table.model()
        if not model or current.row() < 0 or current.row() >= len(model.rows):
            self._clear_socio_preview()
            return

        socio_id = model.rows[current.row()].get("socioID")
        if not socio_id:
            self._clear_socio_preview("No soci")
            return

        socio = consultar_socio(socio_id)
        foto = socio.get("foto") if socio else None
        if not foto:
            self._clear_socio_preview()
            return

        pix = QPixmap()
        pix.loadFromData(foto)
        self.socio_preview.setText("")
        self.socio_preview.setPixmap(
            pix.scaled(self.socio_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _clear_socio_preview(self, text="Sense foto"):
        self.socio_preview.setPixmap(QPixmap())
        self.socio_preview.setText(text)

    def _refresh_personal(self):
        """Actualiza la lista de personal en el combo box."""
        self.personal.clear()
        for persona in listar_personal():
            if persona.get("apellido2") is None:
                nombre = f"{persona['apellido1']}, {persona['nombre']}".strip()
            else:
                nombre = f"{persona['apellido1']} {persona['apellido2']}, {persona['nombre']}".strip()
            self.personal.addItem(nombre, userData=persona["id"])

    def _wrap_focus_out(self, original_focus_out):
        def new_focus_out(event):
            if not self._loading:
                self._save()
            return original_focus_out(event)
        return new_focus_out
