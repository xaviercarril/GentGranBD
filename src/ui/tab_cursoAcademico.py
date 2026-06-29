from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QDateEdit, QFormLayout, QTableWidget, QTableWidgetItem, QMessageBox, QTableView, QGroupBox, QHBoxLayout, QInputDialog, QLineEdit
from PySide6.QtCore import QDate, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from datetime import date
from controladores.curso_academico import duplicar_cursoA, eliminar_cursoA, listar_trimestres_por_cursoA, listar_cursosA, generar_T1, generar_T2, generar_T3, generar_T4
from controladores.trimestre import modificar_trimestre
from ui.table_models import DictTableModel
from ui.table_utils import enable_table_copy
from ui.theme import set_button_icon, set_button_variant

class CursoAcademicoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nou Curs Acadèmic")

        main_layout = QVBoxLayout()
        btn_nou = QPushButton("Nou Curs Acadèmic")
        set_button_icon(btn_nou, "ui/assets/plus.svg")
        set_button_variant(btn_nou, "primary")
        btn_nou.clicked.connect(self._mostrar_dialog_crear)
        btn_duplicar = QPushButton("Duplicar Curs Acadèmic")
        set_button_icon(btn_duplicar, "ui/assets/plus.svg")
        set_button_variant(btn_duplicar, "secondary")
        btn_duplicar.clicked.connect(self._duplicar_curso)
        btn_borrar = QPushButton("Eliminar Curs Acadèmic")
        set_button_icon(btn_borrar, "ui/assets/minus.svg")
        set_button_variant(btn_borrar, "danger")
        btn_borrar.clicked.connect(self._eliminar_curso)
        
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.addWidget(btn_nou)
        top_buttons_layout.addWidget(btn_duplicar)
        top_buttons_layout.addWidget(btn_borrar)
        top_buttons_layout.addStretch()
        main_layout.addLayout(top_buttons_layout)

        top_layout = QHBoxLayout()

        self.tabla = QTableView()
        self.tabla.setSelectionBehavior(QTableView.SelectRows)
        self.tabla.setSelectionMode(QTableView.SingleSelection)
        enable_table_copy(self.tabla)
        self.tabla.setAlternatingRowColors(True)
        self._refresh_table()

        # --- Trimestre group box ---
        self.trimestre_box = QGroupBox("Trimestres")
        trimestre_layout = QFormLayout()
        self.trimestres_edits = []
        for i in range(4):
            inicio = QDateEdit()
            fin = QDateEdit()
            inicio.setCalendarPopup(True)
            fin.setCalendarPopup(True)
            inicio.setDisplayFormat("dd-MM-yyyy")
            fin.setDisplayFormat("dd-MM-yyyy")
            self.trimestres_edits.append((inicio, fin))
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"Trimestre {i+1} Inici:"))
            row_layout.addWidget(inicio)
            row_layout.addWidget(QLabel("Fi:"))
            row_layout.addWidget(fin)
            trimestre_layout.addRow(row_layout)

            inicio.dateChanged.connect(lambda _, i=i: self._guardar_trimestre(i))
            fin.dateChanged.connect(lambda _, i=i: self._guardar_trimestre(i))
        self.trimestre_box.setLayout(trimestre_layout)
        self.trimestre_box.setEnabled(False)

        top_layout.addWidget(self.tabla)
        top_layout.addWidget(self.trimestre_box)

        main_layout.addLayout(top_layout)

        self.setLayout(main_layout)

    def _mostrar_dialog_crear(self):
        from ui.cursoAcademico_dialog import CursoAcademicoFormDialog
        dlg = CursoAcademicoFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_table()

    def _refresh_table(self):
        """Actualiza la tabla con los cursos académicos."""
        cursos = listar_cursosA()
        for curso in cursos:
            curso["fechaInicio"] = curso["fechaInicio"].strftime("%d-%m-%Y")
            curso["fechaFin"] = curso["fechaFin"].strftime("%d-%m-%Y")
        self._all_cursos = cursos  # Guardar para eliminar
        headers = [("Nom", "nombre"), 
                   ("Inici", "fechaInicio"),
                   ("Fi", "fechaFin")]
        model = DictTableModel(cursos, headers)
        self.tabla.setModel(model)
        self.tabla.resizeColumnsToContents()

        new_sel = self.tabla.selectionModel()
        try:
            new_sel.currentRowChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        new_sel.currentRowChanged.connect(self._row_changed)
        self._sel_model = new_sel

    def _eliminar_curso(self):
      sel = self.tabla.selectionModel().selectedRows()
      if not sel:
          return

      row = sel[0].row()
      curso = self.tabla.model().rows[row]
      nom_complet = f"{curso['nombre']} {curso.get('apellido1', '')}".strip()

      box = QMessageBox(self)
      box.setWindowTitle("Confirmar eliminació")
      box.setText(
        f"Vols eliminar el curs «{nom_complet}» (ID {curso['id']})?\n"
        "Aquesta acció no es pot desfer."
      )
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

      eliminar_cursoA(curso["id"])
      self._refresh_table()

    def _duplicar_curso(self):
      sel = self.tabla.selectionModel().selectedRows()
      if not sel:
        QMessageBox.information(
          self,
          "Duplicar curs acadèmic",
          "Selecciona el curs acadèmic que vols duplicar.",
        )
        return

      curso = self.tabla.model().rows[sel[0].row()]
      nuevo_nombre, aceptado = QInputDialog.getText(
        self,
        "Duplicar curs acadèmic",
        "Nom del nou curs:",
        QLineEdit.Normal,
        f"{curso['nombre']} - còpia",
      )
      if not aceptado:
        return

      try:
        nuevo_id = duplicar_cursoA(curso["id"], nuevo_nombre)
        self._refresh_table()
        for row, item in enumerate(self.tabla.model().rows):
          if item["id"] == nuevo_id:
            self.tabla.selectRow(row)
            break
      except ValueError as e:
        QMessageBox.warning(self, "No s'ha pogut duplicar", str(e))

    def _filter_rows(self, text):
      if not text.strip():
        return self._all_cursos
      text = text.lower()

    def _row_changed(self, curr, _prev):
      if not curr.isValid():
        self.trimestre_box.setEnabled(False)
        self._trimestres_actuales = []  # Clear cache
        return

      curso_id = self.tabla.model().rows[curr.row()]["id"]
      trimestres = listar_trimestres_por_cursoA(curso_id)
      self._trimestres_actuales = trimestres  # Cache trimestres for later use

      for i, (inicio_edit, fin_edit) in enumerate(self.trimestres_edits):
        if i < len(trimestres):
          trimestre = trimestres[i]
          inicio_edit.setDate(QDate(trimestre["fechaInicio"].year, trimestre["fechaInicio"].month, trimestre["fechaInicio"].day))
          fin_edit.setDate(QDate(trimestre["fechaFin"].year, trimestre["fechaFin"].month, trimestre["fechaFin"].day))
        else:
          inicio_edit.setDate(QDate.currentDate())
          fin_edit.setDate(QDate.currentDate().addMonths(3))

        # self._generar_trimestre(curso_id, i, inicio_edit, fin_edit)
        self._guardar_trimestre(i)

      self.trimestre_box.setEnabled(True)

    # def _generar_trimestre(self, curso_id, index, inicio_edit, fin_edit):
    #   trimestre_generators = [generar_T1, generar_T2, generar_T3, generar_T4]
    #   if index < len(trimestre_generators):
    #     trimestre_generators[index](curso_id, inicio_edit.date().toPython(), fin_edit.date().toPython())
    #   else:
    #     inicio_edit.setEnabled(False)
    #     fin_edit.setEnabled(False)


    def _guardar_trimestre(self, index):
      if not hasattr(self, "_trimestres_actuales") or index >= len(self._trimestres_actuales):
        return
      trimestre_id = self._trimestres_actuales[index]["id"]
      inicio, fin = self.trimestres_edits[index]
      datos = {
        "fechaInicio": inicio.date().toPython(),
        "fechaFin": fin.date().toPython()
      }
      modificar_trimestre(trimestre_id, datos)
