
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import InscripcionSocio, Actividad, EstadoInscripcion, Pago, EstadoPago, Pago, Socio
from controladores.pagos import registrar_pago
from sqlalchemy.exc import IntegrityError
from datetime import date

# ────────────────────── DTO ──────────────────────
class InscripcionSocioDTO(BaseModel):
    socioID: int
    actividadID: int
    fechaInscripcion: date
    estado: EstadoInscripcion = EstadoInscripcion.RESERVA
    observaciones: str | None = None
    fechaBaja: date | None = None

class InscripcionSocioUpdateDTO(BaseModel):
    estado: EstadoInscripcion | None = None
    observaciones: str | None = None
    fechaBaja: date | None = None

def _to_dto(inscripcion: InscripcionSocio) -> InscripcionSocioDTO:
    return InscripcionSocioDTO(
        socioID=inscripcion.socioID,
        actividadID=inscripcion.actividadID,
        fechaInscripcion=inscripcion.fechaInscripcion,
        estado=inscripcion.estado,
        observaciones=inscripcion.observaciones,
        fechaBaja=inscripcion.fechaBaja
    )

# ───────────────── CRUD ─────────────────
def registrar_inscripcion(data: dict) -> int:
    """Registra inscripción de un socio a una actividad; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = InscripcionSocioDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    nueva_inscripcion = InscripcionSocio(
        socioID=dto.socioID,
        actividadID=dto.actividadID,
        fechaInscripcion=dto.fechaInscripcion,
        estado=dto.estado,
        observaciones=dto.observaciones,
        fechaBaja=dto.fechaBaja
    )

    with SessionLocal() as db:
        db.add(nueva_inscripcion)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al registrar inscripción: {e.orig}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al registrar inscripción: {e}")
        db.refresh(nueva_inscripcion)
        return nueva_inscripcion.id

def modificar_inscripcion(inscripcion_id: int, cambios: dict) -> None:
    """Modifica inscripción de un socio a una actividad; recibe ID y dict con cambios."""
    try:
        dto = InscripcionSocioUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        inscripcion = db.get(InscripcionSocio, inscripcion_id)
        if not inscripcion:
            raise ValueError("Inscripción no encontrada")

        try:
            for key, value in dto.dict(exclude_unset=True).items():
                setattr(inscripcion, key, value)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar inscripción: {e.orig}")

def consultar_inscripcion(inscripcion_id: int) -> dict | None:
    """Consulta una inscripción por su ID."""
    try:
        with SessionLocal() as db:
            inscripcion = db.get(InscripcionSocio, inscripcion_id)
            if not inscripcion:
                return None
            return _to_dto(inscripcion).model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar inscripción: {e}")

def eliminar_inscripcion(inscripcion_id: int) -> None:
    """Elimina inscripción de un socio a una actividad."""
    with SessionLocal() as db:
        inscripcion = db.get(InscripcionSocio, inscripcion_id)
        if not inscripcion:
            raise ValueError("Inscripción no encontrada")
        
        try:
            db.delete(inscripcion)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar inscripción: {e.orig}")

# ────────────────── Consultas ──────────────────
def consultar_actividad_InscripcionSocio(inscripcion_id: int) -> dict | None:
    """Consulta una actividad por la inscripción de un socio."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, inscripcion_id)
            if not act:
                return None
            return act.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")

def consultar_socio_InscripcionSocio(inscripcion_id: int) -> dict | None:
    """Consulta un socio por la inscripción a una actividad."""
    try:
        with SessionLocal() as db:
            socio = db.get(Socio, inscripcion_id)
            if not socio:
                return None
            return socio.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar socio: {e}")
    
def listar_pagos_por_InscripcionSocio(inscripcion_id: int) -> list[dict]:
    """Lista los pagos asociados a una inscripción de socio."""
    try:
        with SessionLocal() as db:
            pagos = db.query(Pago).filter(Pago.inscripcion.id == inscripcion_id).all()
            return [pago.model_dump() for pago in pagos]
    except Exception as e:
        raise ValueError(f"Error al listar pagos: {e}")
    