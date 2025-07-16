from models import Personal, Profesor, Voluntario
from pydantic import BaseModel, ValidationError
from database import SessionLocal
from sqlalchemy.exc import IntegrityError
from dataclasses import dataclass
# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class PersonalDTO(BaseModel):
    id: int | None = None
    nombre: str
    apellido1: str
    apellido2: str | None = None
    dni_nie: str

class PersonalUpdateDTO(BaseModel):
    nombre: str | None = None
    apellido1: str | None = None
    apellido2: str | None = None
    dni_nie: str | None = None

def _to_dto(personal: Personal) -> PersonalDTO:
    return PersonalDTO(
        id=personal.id,
        nombre=personal.nombre,
        apellido1=personal.apellido1,
        apellido2=personal.apellido2,
        dni_nie=personal.dni_nie
    )

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
            dni_nie=dto.dni_nie
        )
    elif tipo == 'voluntario':
        nuevo_personal = Voluntario(
            nombre=dto.nombre,
            apellido1=dto.apellido1,
            apellido2=dto.apellido2,
            dni_nie=dto.dni_nie
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

def modificar_personal(personal_id: int, cambios: dict) -> None:
    """Modifica un personal; recibe ID y dict con cambios."""
    try:
        dto = PersonalUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        personal = db.get(Personal, personal_id)
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

def eliminar_personal(personal_id: int) -> None:
    with SessionLocal() as db:
        persona = db.get(Personal, personal_id)
        if not persona:
            raise ValueError("Personal inexistente")
        db.delete(persona)
        db.commit()

def consultar_personal(personal_id: int) -> Personal | None:
    """Consulta un personal por su ID y devuelve sus datos."""
    try:
        with SessionLocal() as db:
            return db.get(Personal, personal_id)
    except Exception as e:
        raise ValueError(f"Error al consultar personal: {e}")

# ────────────────── Listados ──────────────────
def listar_personal() -> list[dict]:
    """Lista todo el personal registrado."""
    try:
        with SessionLocal() as db:
            personal_list = db.query(Personal).all()
            return [_to_dto(p).model_dump() for p in personal_list]
    except Exception as e:
        raise ValueError(f"Error al listar personal: {e}")
    
def listar_profesores() -> list[dict]:
    """Lista todos los profesores registrados."""
    try:
        with SessionLocal() as db:
            profesores = db.query(Profesor).all()
            return [_to_dto(p).model_dump() for p in profesores]
    except Exception as e:
        raise ValueError(f"Error al listar profesores: {e}")
    
def listar_voluntarios() -> list[dict]:
    """Lista todos los voluntarios registrados."""
    try:
        with SessionLocal() as db:
            voluntarios = db.query(Voluntario).all()
            return [_to_dto(v).model_dump() for v in voluntarios]
    except Exception as e:
        raise ValueError(f"Error al listar voluntarios: {e}")
    
def listar_actividades_por_Personal(personal_id: int) -> list[dict]:
    """Lista las actividades en las que un personal está asignado."""
    try:
        with SessionLocal() as db:
            actividades = db.query(Personal.actividades).filter(Personal.id == personal_id).all()
            return [a.model_dump() for a in actividades]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por personal: {e}")