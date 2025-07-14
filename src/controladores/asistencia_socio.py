from dataclasses import dataclass
from sqlalchemy.orm import Session
from models import AsistenciaSocio, InscripcionSocio
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError

# ─────────────────DTO────────────────────────────
@dataclass(slots=True)
class AsistenciaSocioDTO(BaseModel):
    id: int | None = None
    inscripcion_id: int
    clase_id: int
    presente: bool = False
    observaciones: str | None = None

def _to_dto(asistencia: AsistenciaSocio) -> AsistenciaSocioDTO:
    return AsistenciaSocioDTO(
        id=asistencia.id,
        inscripcion_id=asistencia.inscripcion_id,
        clase_id=asistencia.clase_id,
        presente=asistencia.presente,
        observaciones=asistencia.observaciones
    )

# ─────────────────CRUD──────────────────────────
def registrar_asistenciaSocio(
    session: Session,
    datos: dict
):
    try:
        dto = AsistenciaSocioDTO(**datos)
    except ValidationError as e:
        print(f"Datos inválidos: {e}")
        return None

    inscripcion = session.get(InscripcionSocio, dto.inscripcion_id)
    if not inscripcion:
        print("Inscripción no encontrada.")
        return None
    
    clase = session.get(AsistenciaSocio, dto.clase_id)
    if not clase:
        print("Clase no encontrada.")
        return None

    asistencia = AsistenciaSocio(
        inscripcion_id=dto.inscripcion_id,
        clase_id=dto.clase_id,
        presente=dto.presente,
        observaciones=dto.observaciones
    )
    session.add(asistencia)
    try:
        session.commit()
        return asistencia.id
    except IntegrityError:
        session.rollback()
        return None

def consultar_asistencia(session: Session, asistencia_id: int):
    return session.query(AsistenciaSocio).filter_by(id=asistencia_id).first()

def consultar_asistencia_por_actividad(session: Session, actividad_id: int):
    return session.query(AsistenciaSocio).join(InscripcionSocio).filter(InscripcionSocio.actividad_id == actividad_id).all()

def consultar_asistencia_por_fecha(session: Session, clase_id: int):
    return session.query(AsistenciaSocio).filter_by(clase_id=clase_id).all()

def consultar_asistencia_por_inscripcion(session: Session, inscripcion_id: int):
    return session.query(AsistenciaSocio).filter_by(inscripcion_id=inscripcion_id).all()

def eliminar_asistencia(session: Session, asistencia_id: int):
    asistencia = session.get(AsistenciaSocio,asistencia_id)
    if not asistencia:
        return False
    session.delete(asistencia)
    session.commit()
    return True

def modificar_asistencia(session: Session, asistencia_id: int, nuevos_datos: dict):
    asistencia = session.get(AsistenciaSocio,asistencia_id)
    if not asistencia:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(asistencia, clave, valor)
    session.commit()
    return True