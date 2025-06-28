
from sqlalchemy.orm import Session
from models import Asistencia, Actividad, InscripcionSocio
from collections import defaultdict
from datetime import date

def generar_informe_asistencia_trimestral(session: Session, actividad_id: int, anio: int):
    informe = defaultdict(list)
    inscripciones = session.query(InscripcionSocio).filter_by(actividad_id=actividad_id).all()

    for inscripcion in inscripciones:
        for asistencia in inscripcion.asistencias:
            if asistencia.fecha.year == anio:
                mes = asistencia.fecha.month
                if 1 <= mes <= 3:
                    trimestre = "Q1"
                elif 4 <= mes <= 6:
                    trimestre = "Q2"
                elif 7 <= mes <= 9:
                    trimestre = "Q3"
                else:
                    trimestre = "Q4"
                informe[trimestre].append((inscripcion.socio_id, asistencia.fecha, asistencia.presente))
    return dict(informe)
