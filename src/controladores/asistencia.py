
from sqlalchemy.orm import Session
from models import Asistencia

def registrar_asistencia(session: Session, datos: dict):
    asistencia = Asistencia(
        inscripcion_id=datos['inscripcion_id'],
        fecha=datos['fecha'],
        presente=datos['presente']
    )
    session.add(asistencia)
    session.commit()
    return asistencia.id

def consultar_asistencia(session: Session, inscripcion_id: int):
    return session.query(Asistencia).filter(Asistencia.inscripcion_id == inscripcion_id).all()
