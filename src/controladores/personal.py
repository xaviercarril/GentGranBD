from controladores.dtos import actividad_to_dto, personal_to_dto
from controladores.dtos_models import PersonalDTO, PersonalUpdateDTO
from models import Actividad, Personal, Profesor, Voluntario
from pydantic import BaseModel, ValidationError
from database import SessionLocal
from sqlalchemy.exc import IntegrityError
from dataclasses import dataclass
# ───────────────────── DTO ─────────────────────


# ───────────────── CRUD ─────────────────
def registrar_personal(data: dict, tipo: str) -> int:
    """Registra un nuevo personal; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = PersonalDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    if tipo == 'profesor':
        nuevo_personal = Profesor(
            nombre=dto.nombre,
            apellido1=dto.apellido1,
            apellido2=dto.apellido2,
            email=dto.email,
            telfMovil=dto.telfMovil,
            observaciones=dto.observaciones,
        )
    elif tipo == 'voluntario':
        nuevo_personal = Voluntario(
            nombre=dto.nombre,
            apellido1=dto.apellido1,
            apellido2=dto.apellido2,
            email=dto.email,
            telfMovil=dto.telfMovil,
            observaciones=dto.observaciones,
        )
    else:
        raise ValueError("Tipo de personal no válido")

    try:
        with SessionLocal() as db:
            db.add(nuevo_personal)
            db.commit()
            db.refresh(nuevo_personal)
            return nuevo_personal.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar personal: {e.orig}")

def modificar_personal(personalID: int, cambios: dict) -> None:
    """Modifica un personal; recibe ID y dict con cambios."""
    try:
        dto = PersonalUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        personal = db.get(Personal, personalID)
        if not personal:
            raise ValueError("Personal inexistente")

        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(personal, k, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar personal: {e.orig}")

def eliminar_personal(personalID: int) -> None:
    with SessionLocal() as db:
        persona = db.get(Personal, personalID)
        if not persona:
            raise ValueError("Personal inexistente")
        db.delete(persona)
        db.commit()

def consultar_personal(personalID: int) -> dict | None:
    """Consulta un personal por su ID y devuelve sus datos."""
    if not isinstance(personalID, int):
        raise ValueError("El ID debe ser un número entero")
    try:
        with SessionLocal() as db:
            pers = db.get(Personal, personalID)
            return personal_to_dto(pers).model_dump() if pers else None
    except Exception as e:
        raise ValueError(f"Error al consultar personal: {e}")

# ────────────────── Listados ──────────────────
def listar_personal() -> list[dict]:
    """Lista todo el personal registrado."""
    try:
        with SessionLocal() as db:
            personal_list = db.query(Personal).all()
            return [personal_to_dto(p).model_dump() for p in personal_list]
    except Exception as e:
        raise ValueError(f"Error al listar personal: {e}")
    
def listar_profesores() -> list[dict]:
    """Lista todos los profesores registrados."""
    try:
        with SessionLocal() as db:
            profesores = db.query(Profesor).all()
            return [personal_to_dto(p).model_dump() for p in profesores]
    except Exception as e:
        raise ValueError(f"Error al listar profesores: {e}")
    
def listar_voluntarios() -> list[dict]:
    """Lista todos los voluntarios registrados."""
    try:
        with SessionLocal() as db:
            voluntarios = db.query(Voluntario).all()
            return [personal_to_dto(v).model_dump() for v in voluntarios]
    except Exception as e:
        raise ValueError(f"Error al listar voluntarios: {e}")
    
def listar_actividades_por_Personal(personalID: int) -> list[dict]:
    """Lista las actividades en las que un personal está asignado."""
    try:
        with SessionLocal() as db:
            actividades = db.query(Actividad).filter(Actividad.personalID == personalID).all()
            return [actividad_to_dto(a).model_dump() for a in actividades]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por personal: {e}")
