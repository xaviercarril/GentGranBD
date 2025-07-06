from sqlalchemy.orm import Session
from models import Asistencia, InscripcionSocio
from sqlalchemy.exc import IntegrityError

def registrar_asistencia(
    session: Session,
    datos: dict
):
    inscripcion = session.get(InscripcionSocio,datos.get('inscripcion_id'))
    fecha_id = datos.get('fecha_id')
    presente = datos.get('presente', False)
    observaciones = datos.get('observaciones', '')

    if not inscripcion :
        print("Inscripción no encontrada.")
        return None
    
    if not fecha_id:
        print("Fecha no proporcionada.")
        return None

    asistencia = Asistencia(
        inscripcion_id=inscripcion.id,
        fecha_id=fecha_id,
        presente=presente,
        observaciones=observaciones
    )
    session.add(asistencia)
    try:
        session.commit()
        return asistencia.id
    except IntegrityError:
        session.rollback()
        return None

def consultar_asistencia(session: Session, asistencia_id: int):
    return session.query(Asistencia).filter_by(id=asistencia_id).first()

def consultar_asistencia_por_actividad(session: Session, actividad_id: int):
    return session.query(Asistencia).join(InscripcionSocio).filter(InscripcionSocio.actividad_id == actividad_id).all()

def consultar_asistencia_por_fecha(session: Session, fecha_id: int):
    return session.query(Asistencia).filter_by(fecha_id=fecha_id).all()

def consultar_asistencia_por_inscripcion(session: Session, inscripcion_id: int):
    return session.query(Asistencia).filter_by(inscripcion_id=inscripcion_id).all()

def eliminar_asistencia(session: Session, asistencia_id: int):
    asistencia = session.get(Asistencia,asistencia_id)
    if not asistencia:
        return False
    session.delete(asistencia)
    session.commit()
    return True

def modificar_asistencia(session: Session, asistencia_id: int, nuevos_datos: dict):
    asistencia = session.get(Asistencia,asistencia_id)
    if not asistencia:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(asistencia, clave, valor)
    session.commit()
    return True