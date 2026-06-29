import subprocess
import sys
import tempfile

# src/ui/tab_socios.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QLineEdit, QMessageBox, QMenu, QSplitter, QScrollArea, QComboBox
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QAction
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from ui.table_models import DictTableModel
from ui.socio_detail import SocioDetailWidget
from controladores.socios import (
    listar_socios_tabla, eliminar_socio, consultar_socio, generar_carnet_pdf,
    generar_ficha_socio_pdf, generar_hoja_ficha_carnet_pdf, generar_socios_tabla_pdf
)
from ui.socio_dialog import SocioDialog
from ui.lopd_dialog import LOPDFirmaDialog
from ui.table_utils import add_table_copy_actions, enable_table_copy
from ui.theme import set_button_icon, set_button_variant

class SociosTab(QWidget):
  # ==========================================================
  #   SOCIS
  # ==========================================================
  def __init__(self, parent=None):
    super().__init__(parent)
    self._restoring_selection = False
    self._sort_key = "id"
    self._sort_order = Qt.AscendingOrder
    self._all_socios = []
    self._search_text_by_field_by_id = {}
    self._socios_loaded = False
    self._table_headers = [
      ("Num Soci", "id"),
      ("Primer Cognom", "apellido1"),
      ("Segon Cognom", "apellido2"),
      ("Nom", "nombre"),
      ("DNI", "dniNie"),
      ("Telf. Movil", "telefonoMovil"),
      ("Telf. Fixe", "telefonoFijo"),
      ("Adreça", "direccion"),
      ("Data alta", "fechaAlta"),
      ("Data naixement", "fechaNacimiento"),
      ("Grup difusió", "grupoDifusion"),
      ("Email", "email"),
    ]
    self._column_widths = {
      "id": 90,
      "apellido1": 150,
      "apellido2": 150,
      "nombre": 140,
      "dniNie": 110,
      "telefonoMovil": 110,
      "telefonoFijo": 110,
      "direccion": 220,
      "fechaAlta": 105,
      "fechaNacimiento": 125,
      "grupoDifusion": 130,
      "email": 220,
    }
    # Taula esquerra
    self.table_socis = QTableView()

    # Caixa de cerca
    self._search_field_combo = QComboBox()
    for label, key in self._table_headers:
      self._search_field_combo.addItem(label, key)
    default_search_field = self._search_field_combo.findData("nombre")
    if default_search_field >= 0:
      self._search_field_combo.setCurrentIndex(default_search_field)
    self._search_field_combo.currentIndexChanged.connect(self._filtrar_socios)

    self._search_box = QLineEdit()
    self._search_box.setPlaceholderText("Cerca...")
    self._search_timer = QTimer(self)
    self._search_timer.setSingleShot(True)
    self._search_timer.setInterval(150)
    self._search_timer.timeout.connect(self._apply_current_filter)
    self._search_box.textChanged.connect(self._filtrar_socios)

    # Oculta la columna de número de fila
    self.table_socis.verticalHeader().setVisible(False)
    # -- Configuració de selecció i estil --
    self.table_socis.setSelectionBehavior(QTableView.SelectRows)
    # Permetre selecció múltiple de files
    self.table_socis.setSelectionMode(QTableView.ExtendedSelection)
    enable_table_copy(self.table_socis)
    self.table_socis.setAlternatingRowColors(True)
    self.table_socis.setContextMenuPolicy(Qt.CustomContextMenu)
    self.table_socis.customContextMenuRequested.connect(self._show_socio_context_menu)
    header = self.table_socis.horizontalHeader()
    header.setSectionsClickable(True)
    header.sectionClicked.connect(self._sort_by_header)
    self._refresh_socios()

    # Panell de detall dreta
    self.detail = SocioDetailWidget()
    self.detail.saved.connect(self._on_socio_saved)

    # Quan seleccionem fila → carregar detall
    self.table_socis.selectionModel().currentRowChanged.connect(self._row_changed)
    self.table_socis.doubleClicked.connect(self._abrir_inscripciones_socio)
    # Splitter horitzontal perquè la taula i el detall s'adaptin al resize.
    self.splitter = QSplitter(Qt.Horizontal)
    self.splitter.addWidget(self.table_socis)

    self.detail_scroll = QScrollArea()
    self.detail_scroll.setWidgetResizable(True)
    self.detail_scroll.setFrameShape(QScrollArea.NoFrame)
    self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.detail.setMinimumWidth(430)
    self.detail.setMaximumWidth(480)
    self.detail_scroll.setMinimumWidth(450)
    self.detail_scroll.setMaximumWidth(510)
    self.detail_scroll.setWidget(self.detail)
    self.splitter.addWidget(self.detail_scroll)
    self.splitter.setStretchFactor(0, 1)
    self.splitter.setStretchFactor(1, 0)
    self.splitter.setCollapsible(0, False)
    self.splitter.setCollapsible(1, False)
    self.splitter.setSizes([850, 450])

    # Botons alta / baixa
    btn_nou = QPushButton("Nou soci")
    set_button_icon(btn_nou, "ui/assets/plus.svg")
    set_button_variant(btn_nou, "primary")
    btn_nou.clicked.connect(self._dialog_nou_socio)

    btn_exportar_pdf = QPushButton("Exportar PDF")
    set_button_icon(btn_exportar_pdf, "ui/assets/pdf.svg")
    set_button_variant(btn_exportar_pdf, "secondary")
    btn_exportar_pdf.clicked.connect(self._exportar_socios_pdf)

    top_buttons = QHBoxLayout()
    top_buttons.addWidget(btn_nou)
    top_buttons.addWidget(btn_exportar_pdf)
    top_buttons.addStretch()

    page = QWidget()
    ly = QVBoxLayout(page)
    ly.addLayout(top_buttons)
    search_bar = QHBoxLayout()
    search_bar.addWidget(self._search_field_combo)
    search_bar.addWidget(self._search_box, 1)
    ly.addLayout(search_bar)
    ly.addWidget(self.splitter, 1)
    self.setLayout(ly)
    self.table_socis.installEventFilter(self)

  def refresh(self):
    """Actualitza la taula de socis (wrapping públic)."""
    if hasattr(self, "detail") and not self.detail.confirm_pending_changes():
      return
    self._refresh_socios()

  def _selected_socio_id(self):
    sel_model = self.table_socis.selectionModel()
    if not sel_model:
      return None
    current = sel_model.currentIndex()
    if current.isValid():
      try:
        return self.table_socis.model().rows[current.row()]["id"]
      except Exception:
        pass
    rows = sel_model.selectedRows()
    if rows:
      try:
        return self.table_socis.model().rows[rows[0].row()]["id"]
      except Exception:
        pass
    return None

  def _select_socio_id(self, socio_id):
    if socio_id is None:
      return
    model = self.table_socis.model()
    if not model:
      return
    for row_idx, row in enumerate(getattr(model, "rows", [])):
      if row.get("id") == socio_id:
        idx = model.index(row_idx, 0)
        self.table_socis.setCurrentIndex(idx)
        self.table_socis.selectionModel().select(
          idx,
          QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
        )
        self.table_socis.scrollTo(idx, QTableView.PositionAtCenter)
        return

  def _refresh_socios(self, keep_socio_id=None):
    if keep_socio_id is None:
      keep_socio_id = self._selected_socio_id()
    rows = listar_socios_tabla() or []
    self._all_socios = rows
    self._socios_loaded = True
    self._rebuild_search_index()
    self._apply_current_filter(keep_socio_id=keep_socio_id, resize_columns=True)

  def _set_table_rows(self, rows, keep_socio_id=None, resize_columns=False):
    headers = self._headers_with_sort_indicator(self._table_headers)
    model = DictTableModel(rows, headers)
    self.table_socis.setModel(model)
    if resize_columns:
      self._apply_column_widths()

    new_sel = self.table_socis.selectionModel()
    try:
      new_sel.currentRowChanged.disconnect()
    except (TypeError, RuntimeError):
      pass
    if hasattr(self, "detail"):
      new_sel.currentRowChanged.connect(self._row_changed)
    self._sel_model = new_sel
    self._select_socio_id(keep_socio_id)

  def _apply_column_widths(self):
    model = self.table_socis.model()
    if not model:
      return
    for column, key in enumerate(getattr(model, "keys", [])):
      width = self._column_widths.get(key)
      if width:
        self.table_socis.setColumnWidth(column, width)

  def _headers_with_sort_indicator(self, headers):
    indicator = "▲" if self._sort_order == Qt.AscendingOrder else "▼"
    return [
      (f"{label} {indicator}" if key == self._sort_key else label, key)
      for label, key in headers
    ]

  def _sort_rows(self, rows):
    def value_for_sort(row):
      value = row.get(self._sort_key)
      if value is None:
        return (1, "")
      if self._sort_key == "id":
        try:
          return (0, int(value))
        except (TypeError, ValueError):
          return (0, str(value))
      if isinstance(value, str):
        return (0, value.casefold())
      return (0, str(value).casefold())

    return sorted(
      rows,
      key=value_for_sort,
      reverse=self._sort_order == Qt.DescendingOrder,
    )

  def _sort_by_header(self, section):
    model = self.table_socis.model()
    if not model or section < 0 or section >= len(getattr(model, "keys", [])):
      return

    key = model.keys[section]
    if key == self._sort_key:
      self._sort_order = (
        Qt.DescendingOrder
        if self._sort_order == Qt.AscendingOrder
        else Qt.AscendingOrder
      )
    else:
      self._sort_key = key
      self._sort_order = Qt.AscendingOrder

    self._apply_current_filter(keep_socio_id=self._selected_socio_id())

  def _dialog_nou_socio(self):
    dlg = SocioDialog(self)
    if dlg.exec():
      self._refresh_socios()

  def _show_socio_context_menu(self, pos):
    index = self.table_socis.indexAt(pos)
    if not index.isValid():
      return

    sel_model = self.table_socis.selectionModel()
    row_already_selected = (
      sel_model
      and any(selected.row() == index.row() for selected in sel_model.selectedRows())
    )
    if sel_model and not row_already_selected:
      self.table_socis.setCurrentIndex(index)
      sel_model.select(
        index,
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
      )

    menu = QMenu(self)
    add_table_copy_actions(menu, self.table_socis, index)
    menu.addSeparator()

    inscripciones_action = QAction("Obrir inscripcions", self)
    inscripciones_action.triggered.connect(
      lambda _checked=False, idx=index: self._abrir_inscripciones_socio(idx)
    )
    menu.addAction(inscripciones_action)
    menu.addSeparator()

    carnet_action = QAction("Visualitzar Carnet", self)
    carnet_action.triggered.connect(self._generar_carnet_socio)
    menu.addAction(carnet_action)

    ficha_action = QAction("Visualitzar Fitxa", self)
    ficha_action.triggered.connect(self._generar_ficha_socio)
    menu.addAction(ficha_action)

    hoja_action = QAction("Imprimir Fitxa i Carnet", self)
    hoja_action.triggered.connect(self._generar_hoja_ficha_carnet_socio)
    menu.addAction(hoja_action)

    menu.addSeparator()
    
    lopd_action = QAction("LOPD - Signatura", self)
    lopd_action.triggered.connect(self._abrir_lopd_dialog)
    menu.addAction(lopd_action)

    menu.addSeparator()

    eliminar_action = QAction("Eliminar", self)
    eliminar_action.triggered.connect(self._eliminar_socio)
    menu.addAction(eliminar_action)

    menu.exec(self.table_socis.viewport().mapToGlobal(pos))

  def _on_socio_saved(self, socio_id):
    self._refresh_socios(keep_socio_id=socio_id)

  def _eliminar_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    # Recollir socis seleccionats
    model = self.table_socis.model()
    seleccionats = []
    for idx in sel:
      try:
        r = idx.row()
        seleccionats.append(model.rows[r])
      except Exception:
        continue

    if not seleccionats:
      QMessageBox.warning(self, "Error", "No s'ha pogut obtenir la selecció.")
      return

    if len(seleccionats) == 1:
      socio = seleccionats[0]
      nom_complet = f"{socio['nombre']} {socio.get('apellido1', '')}".strip()
      text = (
        f"Vols eliminar el soci «{nom_complet}» (ID {socio['id']})?\n"
        "Aquesta acció no es pot desfer."
      )
    else:
      # Mostra un resum (primeres 5 línies) i el recompte total
      mostrats = ", ".join(
        [f"{s['nombre']} {s.get('apellido1','')} (ID {s['id']})".strip() for s in seleccionats[:5]]
      )
      resta = len(seleccionats) - 5
      extra = f" i {resta} més" if resta > 0 else ""
      text = (
        f"Vols eliminar {len(seleccionats)} socis seleccionats?\n"
        f"{mostrats}{extra}\n"
        "Aquesta acció no es pot desfer."
      )

    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(text)
    icon_path = "ui/assets/trash.svg"
    pix = QPixmap(icon_path)
    if pix.isNull() and icon_path.lower().endswith(".svg"):
      icon = QIcon(icon_path)
      pix = icon.pixmap(48, 48)
    if not pix.isNull():
      box.setIconPixmap(pix)
    else:
      box.setIcon(QMessageBox.Warning)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.button(QMessageBox.Yes).setText("Sí")
    box.button(QMessageBox.No).setText("No")

    reply = box.exec()
    if reply != QMessageBox.Yes:
      return

    # Eliminar en bloc amb resum de resultats
    errors = []
    eliminats = 0
    for s in seleccionats:
      try:
        eliminar_socio(s["id"])
        eliminats += 1
      except Exception as e:
        nom = f"{s['nombre']} {s.get('apellido1','')}".strip()
        errors.append(f"{nom} (ID {s['id']}): {e}")

    self._refresh_socios()
    self.detail.load(None)

    if errors:
      QMessageBox.warning(
        self,
        "Resultat eliminació",
        f"S'han eliminat {eliminats} de {len(seleccionats)} socis.\nErrors:\n" + "\n".join(errors[:5]) + ("\n…" if len(errors) > 5 else "")
      )
    else:
      QMessageBox.information(self, "Resultat eliminació", f"S'han eliminat {eliminats} socis.")

  def _row_changed(self, curr, _prev):
    if self._restoring_selection:
      return
    if hasattr(self, "detail") and self.detail.has_pending_changes():
      desired_socio_id = None
      if curr.isValid():
        try:
          desired_socio_id = self.table_socis.model().rows[curr.row()]["id"]
        except Exception:
          desired_socio_id = None

      if not self.detail.confirm_pending_changes(emit_saved=False):
        self._restoring_selection = True
        try:
          if _prev.isValid():
            self.table_socis.setCurrentIndex(_prev)
            self.table_socis.selectionModel().select(
              _prev,
              QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
            )
          else:
            self.table_socis.clearSelection()
        finally:
          self._restoring_selection = False
        return

      if desired_socio_id is not None:
        self._restoring_selection = True
        try:
          self._refresh_socios(keep_socio_id=desired_socio_id)
        finally:
          self._restoring_selection = False
        self.detail.load(desired_socio_id)
        return

    if not curr.isValid():
      self.detail.load(None)
      return
    socioID = self.table_socis.model().rows[curr.row()]["id"]
    self.detail.load(socioID)

  def _generar_carnet_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    row = sel[0].row()
    socio = self.table_socis.model().rows[row]

    pdf_path = self._temporary_pdf_path(f"carnet_{socio['id']:06d}_")
    try:
      generar_carnet_pdf(socio['id'], pdf_path)
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar el carnet:\n{e}")
      return

    try:
      self._open_file(pdf_path)
    except Exception:
      QMessageBox.information(
        self,
        "Carnet generat",
        f"El carnet s'ha generat correctament:\n{pdf_path}",
      )

  def _generar_ficha_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    row = sel[0].row()
    socio = self.table_socis.model().rows[row]

    pdf_path = self._temporary_pdf_path(f"fitxa_socio_{socio['id']:06d}_")
    try:
      generar_ficha_socio_pdf(socio["id"], pdf_path)
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar la fitxa:\n{e}")
      return

    try:
      self._open_file(pdf_path)
    except Exception:
      QMessageBox.information(
        self,
        "Fitxa generada",
        f"La fitxa s'ha generat correctament:\n{pdf_path}",
      )

  def _generar_hoja_ficha_carnet_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    row = sel[0].row()
    socio = self.table_socis.model().rows[row]

    pdf_path = self._temporary_pdf_path(f"fitxa_carnet_socio_{socio['id']:06d}_")
    try:
      generar_hoja_ficha_carnet_pdf(socio["id"], pdf_path)
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar la fulla imprimible:\n{e}")
      return

    try:
      self._open_file(pdf_path)
    except Exception:
      QMessageBox.information(
        self,
        "Fulla generada",
        f"La fulla imprimible s'ha generat correctament:\n{pdf_path}",
      )

  def _exportar_socios_pdf(self):
    model = self.table_socis.model()
    rows = list(getattr(model, "rows", []) or [])
    if not rows:
      QMessageBox.warning(self, "Error", "No hi ha socis per exportar.")
      return

    try:
      with tempfile.NamedTemporaryFile(
        prefix="socis-",
        suffix=".pdf",
        delete=False,
      ) as tmp:
        ruta = tmp.name
      generar_socios_tabla_pdf(rows, ruta)
      if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
        QMessageBox.warning(
          self,
          "Avís",
          f"No s'ha pogut obrir el visor PDF del sistema.\nPDF temporal: {ruta}",
        )
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")

  def _temporary_pdf_path(self, prefix: str) -> str:
    tmp = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".pdf", delete=False)
    tmp.close()
    return tmp.name

  def _open_file(self, path: str):
    if sys.platform.startswith("darwin"):
      subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
      import os
      os.startfile(path)
    else:
      subprocess.Popen(["xdg-open", path])

  def _filtrar_socios(self):
    self._search_timer.start()

  def _apply_current_filter(self, keep_socio_id=None, resize_columns=False):
    if hasattr(self, "detail") and not self.detail.confirm_pending_changes():
      return
    if keep_socio_id is None:
      keep_socio_id = self._selected_socio_id()
    filtered_rows = self._filter_rows(self._search_box.text())
    filtered_rows = self._sort_rows(filtered_rows)
    self._set_table_rows(
      filtered_rows,
      keep_socio_id=keep_socio_id,
      resize_columns=resize_columns,
    )

  def _filter_rows(self, text):
    text = text.strip().casefold()
    if not text:
      return self._all_socios
    field_key = self._selected_search_field()
    return [
      row for row in self._all_socios
      if text in self._search_text_by_field_by_id.get(row.get("id"), {}).get(field_key, "")
    ]

  def _rebuild_search_index(self):
    self._search_text_by_field_by_id = {
      row.get("id"): self._row_search_text_by_field(row)
      for row in self._all_socios
    }

  def _row_search_text_by_field(self, row):
    text_by_field = {}
    for _label, key in self._table_headers:
      value = row.get(key)
      if value is None:
        text_by_field[key] = ""
        continue
      values = [str(value)]
      if hasattr(value, "strftime"):
        values.append(value.strftime("%d/%m/%Y"))
      text_by_field[key] = " ".join(values).casefold()
    return text_by_field

  def _selected_search_field(self):
    if not hasattr(self, "_search_field_combo"):
      return "nombre"
    return self._search_field_combo.currentData() or "nombre"

  def _abrir_inscripciones_socio(self, index):
      if not index.isValid():
          return
      socio = self.table_socis.model().rows[index.row()]
      from ui.inscripciones_dialog import InscripcionesDialog
      dlg = InscripcionesDialog(socio["id"], self)
      dlg.exec()

  def showEvent(self, event):
      super().showEvent(event)
      if not self._socios_loaded:
          self._refresh_socios()

  def confirm_pending_changes(self):
      return self.detail.confirm_pending_changes()
  def eventFilter(self, obj, event):
      if hasattr(self, "table_socis") and obj == self.table_socis and event.type() == QEvent.KeyPress:
          if event.key() == Qt.Key_Delete:
              self._eliminar_socio()
              return True
      return super().eventFilter(obj, event)
  
  def _abrir_lopd_dialog(self):
      sel = self.table_socis.selectionModel().selectedRows()
      if not sel:
          QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
          return

      row = sel[0].row()
      socio = self.table_socis.model().rows[row]

      dialog = LOPDFirmaDialog(socio['id'], self)
      dialog.exec()
