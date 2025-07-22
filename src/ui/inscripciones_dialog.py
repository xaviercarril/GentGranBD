from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from controladores.inscripcion_socio import (
    consultar_actividadID_InscripcionSocio, consultar_socioID_InscripcionSocio, registrar_inscripcion, eliminar_inscripcion
)
from controladores.actividades import consultar_actividad, listar_actividades, listar_inscripciones_por_Actividad
from controladores.socios import consultar_socio, listar_inscripciones_por_socio
from datetime import date
from controladores.inscripcion_socio import modificar_inscripcion

class InscripcionesDialog(QDialog):
    def __init__(self, socio_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'inscripcions del soci")
        self.socio_id = socio_id

        self.layout = QVBoxLayout(self)

        self.combo_cursos = QComboBox()
        self.combo_cursos.currentIndexChanged.connect(self._carregar_inscripcions)
        self.layout.addWidget(QLabel("Curs acadèmic:"))
        self.layout.addWidget(self.combo_cursos)

        self.label = QLabel("Activitats inscrites:")
        self.layout.addWidget(self.label)

        self.lista_inscripciones = QListWidget()
        self.layout.addWidget(self.lista_inscripciones)

        btn_layout = QHBoxLayout()
        self.btn_afegir = QPushButton("Afegir inscripció")
        self.btn_eliminar = QPushButton("Eliminar inscripció")
        btn_layout.addWidget(self.btn_afegir)
        btn_layout.addWidget(self.btn_eliminar)
        self.layout.addLayout(btn_layout)

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
                self.lista_inscripciones.addItem(f"{act['nombre']} - {ins['estado'].value} - {ins['fechaInscripcion'].strftime('%d-%m-%Y')}")

    def _afegir_inscripcio(self):
        curso_id = self.combo_cursos.currentData()
        activitats = [a for a in listar_actividades() if curso_id is None or a["cursoAcademico_id"] == curso_id]
        noms = [a["nombre"] for a in activitats]

        from PySide6.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(self, "Selecciona una activitat", "Activitat:", noms, 0, False)
        if ok and item:
            act = next((a for a in activitats if a["nombre"] == item), None)
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
                    i for i in inscripciones_todas if i["estado"].value == "INSCRITO"
                ]
                estado = "INSCRITO" if len(inscritos_actuales) < act["numMaxAlumnos"] else "RESERVA"
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
        act = consultar_actividad(actividadID)
        if not act:
            return

        todas = listar_inscripciones_por_Actividad(actividadID)

        # Usar el valor correcto del Enum si es un Enum real
        reservas = [i for i in todas if i["estado"].value == "RESERVA"]
        reservas.sort(key=lambda i: i["fechaInscripcion"])

        inscritos = [i for i in todas if i["estado"].value == "INSCRITO"]
        max_alumnes = act.get("numMaxAlumnos", 0)
        vacantes = max_alumnes - len(inscritos)

        actualizados = 0
        for ins in reservas[:vacantes]:
            try:
                modificar_inscripcion(ins["id"], {"estado": "INSCRITO"})
                socioID = consultar_socioID_InscripcionSocio(ins["id"])
                socio = consultar_socio(socioID) if socioID else None
                if socio:
                    QMessageBox.information(
                        self,
                        "Reserva actualitzada",
                        f"Soci ID:{socio['id']}, {socio['nombre'] + ' ' + socio['apellido1']} ha passat de RESERVA a INSCRIT a {act['nombre']}"
                    )
                actualizados += 1
            except Exception as e:
                print(f"Error actualitzant reserva: {e}")
        
        if actualizados > 0:
            self._carregar_inscripcions()