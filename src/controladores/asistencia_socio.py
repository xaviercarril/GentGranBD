from dataclasses import dataclass
from sqlalchemy.orm import Session
from models import AsistenciaSocio, InscripcionSocio, Clase
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError

# ─────────────────DTO────────────────────────────
@dataclass(slots=True)
class AsistenciaSocioDTO(BaseModel):
    socio_id: int
    clase_id: int
    presente: bool = False
    observaciones: str | None = None

def _to_dto(asistencia: AsistenciaSocio) -> AsistenciaSocioDTO:
    return AsistenciaSocioDTO(
        socio_id=asistencia.socio_id,
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
        raise ValueError(f"Datos inválidos: {e}")

    clase = session.get(Clase, dto.clase_id)

    asistencia = AsistenciaSocio(
        socio_id=dto.socio_id,
        clase_id=dto.clase_id,
        presente=dto.presente,
        observaciones=dto.observaciones
    )
    session.add(asistencia)
    try:
        session.commit()
        return {'socio_id': asistencia.socio_id, 'clase_id': asistencia.clase_id}
    except IntegrityError:
        session.rollback()
        return None

def consultar_asistencia(session: Session, socio_id: int, clase_id: int):
    return session.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})

def consultar_asistencia_por_actividad(session: Session, actividad_id: int):
    return session.query(AsistenciaSocio).join(InscripcionSocio).filter(InscripcionSocio.actividad_id == actividad_id).all()

def consultar_asistencia_por_fecha(session: Session, clase_id: int):
    return session.query(AsistenciaSocio).filter_by(clase_id=clase_id).all()

def consultar_asistencia_por_inscripcion(session: Session, socio_id: int, actividad_id: int):
    return session.query(AsistenciaSocio).join(Clase).filter(
        AsistenciaSocio.socio_id == socio_id,
        Clase.actividad_id == actividad_id
    ).all()

def eliminar_asistencia(session: Session, socio_id: int, clase_id: int):
    asistencia = session.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})
    if not asistencia:
        return False
    session.delete(asistencia)
    session.commit()
    return True

def modificar_asistencia(session: Session, socio_id: int, clase_id: int, nuevos_datos: dict):
    asistencia = session.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})
    if not asistencia:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(asistencia, clave, valor)
    session.commit()
    return True