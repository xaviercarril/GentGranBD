
from sqlalchemy.orm import Session
from controladores.dtos import pago_to_dto
from controladores.dtos_models import PagoDTO, PagoUpdateDTO
from models import EstadoPago, InscripcionSocio, Pago
from datetime import date
from pydantic import BaseModel, ValidationError
from database import SessionLocal
from sqlalchemy.exc import IntegrityError

# ───────────────── CRUD ─────────────────
def registrar_pago(data: dict) -> int:
    """Registra un pago; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = PagoDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    nuevo_pago = Pago( # Asegúrate de que el ID sea opcional o generado automáticamente
        socioID=dto.socioID,
        actividadID=dto.actividadID,
        inscripcionID=dto.inscripcionID,
        fecha=dto.fecha_pago,
        importe=dto.importe,
        estado=dto.estado,
        observaciones=dto.observaciones,
    )

    with SessionLocal() as db:
        db.add(nuevo_pago)
        try:
            db.commit()
            db.refresh(nuevo_pago)
            return nuevo_pago.id
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al registrar pago: {e.orig}")

def modificar_pago(pago_id: int, nuevos_datos: dict) -> None:
    """Modifica un pago; recibe ID y dict con cambios."""
    try:
        dto = PagoUpdateDTO(**nuevos_datos)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        pago = db.get(Pago, pago_id)
        if not pago:
            raise ValueError("Pago inexistente")
        try:
            mapeo = {
                "fecha_pago": "fecha",
            }
            for key, value in dto.model_dump(exclude_unset=True).items():
                attr = mapeo.get(key, key)
                if attr == "estado" and value is not None:
                    value = getattr(value, "value", value)
                    value = EstadoPago(value)
                setattr(pago, attr, value)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar pago: {e.orig}")

def consultar_pago(pago_id: int) -> dict | None:
    """Consulta un pago por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            pago = db.get(Pago, pago_id)
            if not pago:
                return None
            return pago_to_dto(pago).model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar pago: {e}")

def eliminar_pago(pago_id: int) -> None:
    """Elimina un pago por su ID."""
    try:
        with SessionLocal() as db:
            pago = db.get(Pago, pago_id)
            if not pago:
                raise ValueError("Pago inexistente")
            db.delete(pago)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar pago: {e.orig}")
    except Exception as e:
        raise ValueError(f"Error inesperado al eliminar pago: {e}")
    
# ────────────────── Consultas ──────────────────
def consultar_inscripcion_por_Pago(pago_id: int) -> list[dict]:
    """Consulta inscripciones asociadas a un pago."""
    try:
        with SessionLocal() as db:
            inscr = db.get(InscripcionSocio, pago_id)
            if not inscr:
                return None
            return inscr.model_dump()
    except Exception as e:
        raise ValueError(f"Error al listar inscripciones por pago: {e}")
