from controladores.actividades import contar_inscripciones_Actividad, listar_actividades, consultar_actividad, eliminar_actividad
from controladores.personal import consultar_personal  # Import the missing function
from PySide6.QtWidgets import (
  QWidget, QVBoxLayout, QHBoxLayout, QTableView,
  QPushButton, QMessageBox, QLineEdit, QComboBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, QModelIndex, QItemSelectionModel
from ui.actividad_dialog import ActividadDialog
from ui.actividad_detail import ActividadDetailWidget
from ui.table_models import DictTableModel
from controladores.curso_academico import listar_cursosA, listar_actividades_por_CursoAcademico

class ActividadesTab(QWidget):
  # ==========================================================
  #   ACTIVITATS
  # ==========================================================
  def __init__(self, parent=None):
    super().__init__(parent)


    self._curso_selector = QComboBox()
    self._curso_selector.addItem("Tots els cursos", None)
    for curso in listar_cursosA():
        self._curso_selector.addItem(curso["nombre"], curso["id"])
    from datetime import date
    hoy = date.today()
    for i in range(1, self._curso_selector.count()):
        curso_id = self._curso_selector.itemData(i)
        curso_nombre = self._curso_selector.itemText(i)
        for curso in listar_cursosA():
            if curso["id"] == curso_id and curso["fechaInicio"] <= hoy <= curso["fechaFin"]:
                self._curso_selector.setCurrentIndex(i)
                break
    self._curso_selector.currentIndexChanged.connect(self._refresh_activitats)
    # Installa event filter para detectar cuando se despliega el ComboBox
    self._curso_selector.view().window().installEventFilter(self)

    self.table_activitats = QTableView()
    self._search_box = QLineEdit()
    self._search_box.setPlaceholderText("Cerca activitats...")
    self._search_box.textChanged.connect(self._refresh_activitats)

    # Configure table
    self.table_activitats.verticalHeader().setVisible(False)
    self.table_activitats.setSelectionBehavior(QTableView.SelectRows)
    self.table_activitats.setSelectionMode(QTableView.SingleSelection)
    self.table_activitats.setAlternatingRowColors(True)
    self.table_activitats.setStyleSheet("""
      QTableView::item:selected {
        background: #c5d6a1;
        color: black;
      } 
      QTableView::item:selected:active {
        background: #a8bd88;
      }
    """)

    self.detail_actividad = ActividadDetailWidget()
    self.detail_actividad.saved.connect(self._refresh_activitats)
    self.detail_actividad.setFixedWidth(300)

    # Buttons
    self.btn_nova_actividad = QPushButton("Nova Activitat")
    self.btn_nova_actividad.setIcon(QIcon("ui/assets/plus.svg"))
    self.btn_nova_actividad.setIconSize(QSize(16, 16))
    btn_eliminar_actividad = QPushButton("Eliminar Activitat")
    btn_eliminar_actividad.setIcon(QIcon("ui/assets/minus.svg"))
    btn_eliminar_actividad.setIconSize(QSize(16, 16))

    self.btn_nova_actividad.clicked.connect(self._dialog_nova_actividad)
    btn_eliminar_actividad.clicked.connect(self._eliminar_actividad)

    # Layouts
    main_layout = QVBoxLayout(self)

    top_buttons = QHBoxLayout()
    top_buttons.addWidget(self.btn_nova_actividad)
    top_buttons.addWidget(btn_eliminar_actividad)
    top_buttons.addStretch()

    main_layout.addWidget(self._curso_selector)
    main_layout.addLayout(top_buttons)
    main_layout.addWidget(self._search_box)

    mid_layout = QHBoxLayout()
    mid_layout.addWidget(self.table_activitats, stretch=3)
    mid_layout.addWidget(self.detail_actividad, stretch=0)

    main_layout.addLayout(mid_layout, 1)

    self._refresh_activitats()

  def _refresh_activitats(self):
    """Actualiza la lista de actividades y el detalle."""

    curso_id = self._curso_selector.currentData()
    self.btn_nova_actividad.setEnabled(curso_id is not None)
    rows = listar_actividades_por_CursoAcademico(curso_id) if curso_id else listar_actividades()
    headers = [
      ("ID", "id"),
      ("Nom", "nombre"),
      ("Personal", "personal_nombre"),
      ("Preu matrícula", f"precio_matricula"),
      ("Inscrits", "inscritos"),
      ("Màxim alumnes", "numMaxAlumnos"),
      ("Descripció", "descripcion")
    ]

    # Enriquecer datos con nombre del personal y contar inscritos
    for row in rows:
        row["precio_matricula"] = f"{row['precio_matricula']:.2f} €"
        try:
            personal = consultar_personal(row["personalID"]) if row["personalID"] else None
            row["personal_nombre"] = f"{personal['nombre']} {personal['apellido1']}" if personal else "Desconegut"
        except Exception:
            row["personal_nombre"] = "Desconegut"

        try:
            row["inscritos"] = contar_inscripciones_Actividad(row["id"])
        except Exception:
            row["inscritos"] = "?"

    filtered_rows = self._filter_activitats_rows(self._search_box.text(), rows)

    # Guardar ID seleccionado
    selected_id = None
    sel_model = self.table_activitats.selectionModel()
    if sel_model and sel_model.currentIndex().isValid():
        selected_id = self.table_activitats.model().rows[sel_model.currentIndex().row()]["id"]

    # Asignar nuevo modelo
    model = DictTableModel(filtered_rows, headers)
    self.table_activitats.setModel(model)
    self.table_activitats.resizeColumnsToContents()
    self.table_activitats.hideColumn(0)

    # Conectar el nuevo modelo
    sel_model = self.table_activitats.selectionModel()
    sel_model.currentChanged.connect(self._row_changed_actividad)

    # Restaurar selección
    if selected_id is not None:
        for row_idx, r in enumerate(model.rows):
            if r["id"] == selected_id:
                index = model.index(row_idx, 0)
                from PySide6.QtCore import QItemSelectionModel
                sel_model.setCurrentIndex(index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows)
                break

  def _filter_activitats_rows(self, text, rows):
    if not text.strip():
      return rows
    text = text.lower()
    def matches(a):
      return any(
        text in str(value).lower() if value else ""
        for value in a.values()
      )
    return [a for a in rows if matches(a)]

  def _row_changed_actividad(self, current: QModelIndex, previous: QModelIndex):
    if not current.isValid():
      self.detail_actividad.load(None)
      return
    actividadID = self.table_activitats.model().rows[current.row()]["id"]
    self.detail_actividad.load(actividadID)

  def _dialog_nova_actividad(self):
      curso_id = self._curso_selector.currentData()

      # Determinar curso actual por fecha si no hay uno seleccionado
      if curso_id is None:
          from datetime import date
          hoy = date.today()
          cursos = listar_cursosA()
          for c in cursos:
              if c["fechaInicio"] <= hoy <= c["fechaFin"]:
                  curso_id = c["id"]
                  break

      dlg = ActividadDialog(self, cursoAcademico_id=curso_id)
      if dlg.exec():
          self._refresh_activitats()

  def _eliminar_actividad(self):
    sel = self.table_activitats.selectionModel().selectedRows()
    if not sel:
      return
    row = sel[0].row()
    actividad = self.table_activitats.model().rows[row]
    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(
      f"Vols eliminar l'activitat «{actividad['nombre']}» (ID {actividad['id']})?\n"
      "Aquesta acció no es pot desfer."
    )
    box.setIcon(QMessageBox.Warning)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.button(QMessageBox.Yes).setText("Sí")
    box.button(QMessageBox.No).setText("No")
    reply = box.exec()
    if reply != QMessageBox.Yes:
      return
    eliminar_actividad(actividad["id"])
    self._refresh_activitats()
    self.detail_actividad.load(None)

  def _actualizar_cursos(self):
      self._curso_selector.blockSignals(True)
      curso_actual = self._curso_selector.currentData()
      self._curso_selector.clear()
      self._curso_selector.addItem("Tots els cursos", None)
      for curso in listar_cursosA():
          self._curso_selector.addItem(curso["nombre"], curso["id"])
      index = self._curso_selector.findData(curso_actual)
      self._curso_selector.setCurrentIndex(index if index >= 0 else 0)
      self._curso_selector.blockSignals(False)

  def eventFilter(self, source, event):
      from PySide6.QtCore import QEvent
      if event.type() == QEvent.Show and source is self._curso_selector.view().window():
          self._actualizar_cursos()
      return super().eventFilter(source, event)
  
  def showEvent(self, event):
      super().showEvent(event)
      self._refresh_activitats()