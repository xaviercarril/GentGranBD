from dataclasses import dataclass
from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import ActividadPersonal, Personal

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class ActividadPersonalDTO(BaseModel):
    id: int | None = None
    actividad_id: int
    personal_id: int
    rol: str | None = None

class ActividadPersonalUpdateDTO(BaseModel):
    rol: str | None = None

def _to_dto(actividad_personal: ActividadPersonal) -> ActividadPersonalDTO:
    return ActividadPersonalDTO(
        id=actividad_personal.id,
        actividad_id=actividad_personal.actividad_id,
        personal_id=actividad_personal.personal_id,
        rol=actividad_personal.rol
    )

# ───────────────── CRUD ─────────────────
def registrar_actividad_personal(data: dict) -> int:
    """Registra la participación de un personal en una actividad; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = ActividadPersonalDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    nueva_actividad_personal = ActividadPersonal(
        actividad_id=dto.actividad_id,
        personal_id=dto.personal_id,
        rol=dto.rol
    )

    try:
        with SessionLocal() as db:
            db.add(nueva_actividad_personal)
            db.commit()
            db.refresh(nueva_actividad_personal)
            return nueva_actividad_personal.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar actividad personal: {e.orig}")
    
def modificar_actividad_personal(id: int, cambios: dict) -> None:
    """Modifica la participación de un personal en una actividad; recibe ID y dict con cambios."""
    try:
        dto = ActividadPersonalUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        actividad_personal = db.get(ActividadPersonal, id)
        if not actividad_personal:
            raise ValueError("Actividad personal inexistent")

        if dto.rol is not None:
            actividad_personal.rol = dto.rol

        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar actividad personal: {e.orig}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al modificar actividad personal: {e}")
        
def consultar_actividad_personal(id: int) -> dict | None:
    """Consulta una participación de personal en una actividad por ID."""
    with SessionLocal() as db:
        actividad_personal = db.get(ActividadPersonal, id)
        return _to_dto(actividad_personal).model_dump() if actividad_personal else None
    
def eliminar_actividad_personal(id: int) -> None:
    """Elimina una participación de personal en una actividad por ID."""
    with SessionLocal() as db:
        actividad_personal = db.get(ActividadPersonal, id)
        if not actividad_personal:
            raise ValueError("Actividad personal inexistent")
        db.delete(actividad_personal)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar actividad personal: {e.orig}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al eliminar actividad personal: {e}")
        

# ───────────────── Consultas ─────────────────
def consultar_personal_ActividadPersonal(actividadPersonal_id: int) -> dict | None:
    """Consulta personal asociado a una actividad y devuelve lista de dicts."""
    try:
        with SessionLocal() as db:
            personal = db.get(ActividadPersonal, actividadPersonal_id)
            if not personal:
                return None
            return personal.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar personal de actividad: {e}")
    
def consultar_actividad_ActividadPersonal(actividadPersonal_id: int) -> dict | None:
    """Consulta actividad asociada a un personal y devuelve lista de dicts."""
    try:
        with SessionLocal() as db:
            actividad = db.get(ActividadPersonal, actividadPersonal_id)
            if not actividad:
                return None
            return actividad.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar actividad de personal: {e}")