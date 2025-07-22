
from pydantic import ValidationError
from controladores.dtos_models import InscripcionSocioDTO, InscripcionSocioUpdateDTO
from database import SessionLocal
from models import InscripcionSocio, Pago
from controladores.dtos import inscripcion_to_dto, pago_to_dto
from sqlalchemy.exc import IntegrityError

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
        return nueva_inscripcion

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
            return inscripcion_to_dto(inscripcion).model_dump()
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
def consultar_actividadID_InscripcionSocio(inscripcion_id: int) -> int | None:
    """Consulta una actividad por la inscripción de un socio."""
    try:
        with SessionLocal() as db:
            ins = db.get(InscripcionSocio, inscripcion_id)
            if not ins:
                return None
            return ins.actividadID
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")

def consultar_socioID_InscripcionSocio(inscripcion_id: int) -> int | None:
    """Consulta un socio por la inscripción a una actividad."""
    try:
        with SessionLocal() as db:
            ins = db.get(InscripcionSocio, inscripcion_id)
            if not ins:
                return None
            return ins.socioID
    except Exception as e:
        raise ValueError(f"Error al consultar socio: {e}")
    
def listar_pagos_por_InscripcionSocio(inscripcion_id: int) -> list[dict]:
    """Lista los pagos asociados a una inscripción de socio."""
    try:
        socioID = consultar_socioID_InscripcionSocio(inscripcion_id)
        actividadID = consultar_actividadID_InscripcionSocio(inscripcion_id)
        if not socioID:
            raise ValueError("Inscripción no encontrada o socio no asociado")
        if not actividadID:
            raise ValueError("Inscripción no encontrada o actividad no asociada")
        with SessionLocal() as db:
            pagos = db.query(Pago).filter(
                Pago.socioID == socioID,
                Pago.actividadID == actividadID
            ).all()
            return [pago_to_dto(pago).model_dump() for pago in pagos]
    except Exception as e:
        raise ValueError(f"Error al listar pagos: {e}")
