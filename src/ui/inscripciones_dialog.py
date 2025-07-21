from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from controladores.inscripcion_socio import (
    consultar_actividadID_InscripcionSocio, consultar_socioID_InscripcionSocio, registrar_inscripcion, eliminar_inscripcion
)
from controladores.actividades import consultar_actividad, listar_actividades
from controladores.socios import listar_inscripciones_por_socio
from datetime import date


class InscripcionesDialog(QDialog):
    def __init__(self, socio_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestió d'inscripcions del soci")
        self.socio_id = socio_id

        self.layout = QVBoxLayout(self)

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

        self._carregar_inscripcions()

    def _carregar_inscripcions(self):
        self.lista_inscripciones.clear()
        self._inscripcions = listar_inscripciones_por_socio(self.socio_id)
        for ins in self._inscripcions:
            actividadID = consultar_actividadID_InscripcionSocio(ins["id"])
            actividadNombre = consultar_actividad(actividadID)["nombre"] if actividadID else "Desconeguda"
            if actividadID:
                self.lista_inscripciones.addItem(f"{actividadNombre} - {ins['estado'].value} - {ins['fechaInscripcion']}")

    def _afegir_inscripcio(self):
        activitats = listar_actividades()
        noms = [a["nombre"] for a in activitats]

        from PySide6.QtWidgets import QInputDialog
        item, ok = QInputDialog.getItem(self, "Selecciona una activitat", "Activitat:", noms, 0, False)
        if ok and item:
            act = next((a for a in activitats if a["nombre"] == item), None)
            if act:
                try:
                    registrar_inscripcion({
                        "socioID": self.socio_id,
                        "actividadID": act["id"],
                        "fechaInscripcion": date.today(),
                        "estado": "INSCRITO",
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
            self._carregar_inscripcions()