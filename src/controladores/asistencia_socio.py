from dataclasses import dataclass
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AsistenciaSocio, InscripcionSocio, Clase, Socio
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError

# ─────────────────DTO────────────────────────────
@dataclass(slots=True)
class AsistenciaSocioDTO(BaseModel):
    socio_id: int
    clase_id: int
    presente: bool = False
    observaciones: str | None = None

class AsistenciaSocioUpdateDTO(BaseModel):
    presente: bool | None = None
    observaciones: str | None = None

def _to_dto(asistencia: AsistenciaSocio) -> AsistenciaSocioDTO:
    return AsistenciaSocioDTO(
        socio_id=asistencia.socio_id,
        clase_id=asistencia.clase_id,
        presente=asistencia.presente,
        observaciones=asistencia.observaciones
    )

# ─────────────────CRUD──────────────────────────
def registrar_asistenciaSocio(data: dict) -> int:
    """Registra asistencia de un socio a una clase; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = AsistenciaSocioDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    try:
        nueva_asistencia = AsistenciaSocio(
            socio_id=dto.socio_id,
            clase_id=dto.clase_id,
            presente=dto.presente,
            observaciones=dto.observaciones
        )

        with SessionLocal() as db:
            db.add(nueva_asistencia)
            db.commit()
            db.refresh(nueva_asistencia)
            return nueva_asistencia.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar asistencia: {e.orig}")


def modificar_asistenciaSocio(socio_id: int, clase_id: int, nuevos_datos: dict) -> None:
    """Modifica asistencia de un socio a una clase; recibe ID y dict con cambios."""
    try:
        dto = AsistenciaSocioUpdateDTO(**nuevos_datos)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        asistencia = db.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})
        if not asistencia:
            raise ValueError("Asistencia inexistent")
        
        try:
            for key, value in dto.model_dump().items():
                setattr(asistencia, key, value)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo no válido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar asistencia: {e.orig}")
        
def eliminar_asistenciaSocio(socio_id: int, clase_id: int) -> None:
    """Elimina asistencia de un socio a una clase; recibe IDs."""
    try:
        with SessionLocal() as db:
            asistencia = db.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})
            if not asistencia:
                raise ValueError("Asistencia inexistent")
            db.delete(asistencia)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar asistencia: {e.orig}")

def consultar_asistenciaSocio(socio_id: int, clase_id: int) -> dict | None:
    """Consulta asistencia de un socio a una clase; devuelve dict o None."""
    with SessionLocal() as db:
        asistencia = db.get(AsistenciaSocio, {'socio_id': socio_id, 'clase_id': clase_id})
        return _to_dto(asistencia).model_dump() if asistencia else None



# ───────────────── Consultas ─────────────────

def consultar_clase_AsistenciaSocio(asistencia_id: int) -> dict | None:
    """Consulta una clase por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            clase = db.get(Clase, asistencia_id)
            return _to_dto(clase).model_dump() if clase else None
    except Exception as e:
        raise ValueError(f"Error al consultar clase: {e}")
    
def consultar_socio_AsistenciaSocio(asistencia_id: int) -> dict | None:
    """Consulta un socio por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            socio = db.get(Socio, asistencia_id)
            if not socio:
                return None
            return _to_dto(socio).model_dump() if socio else None
    except Exception as e:
        raise ValueError(f"Error al consultar socio: {e}")