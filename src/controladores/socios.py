"""
Controlador de SOCIOS — capa de negocio
Solo expone funciones que reciben/retornan dicts (DTOs) y
usan SessionLocal internamente.  La UI nunca ve objetos ORM.
"""

from __future__ import annotations


from datetime import date
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError


from database import SessionLocal  # fábrica de sesiones
from models import AsistenciaSocio, CursoAcademico, FirmaLOPD, InscripcionSocio, Lugar, Socio


# ───────────────────── DTO ─────────────────────
class SocioDTO(BaseModel):

    id: int | None = None
    dni_nie: str
    nombre: str
    apellido1: str
    apellido2: str | None = None
    direccion: str | None = None
    telefono_fijo: str | None = None
    telefono_movil: str | None = None
    email: str | None = None
    grupo_difusion: str | None = None
    fecha_alta: date
    fecha_baja: date | None = None
    observaciones: str | None = None
    foto: bytes | None = None


class SocioUpdateDTO(BaseModel):
    dni_nie: str | None = None
    nombre: str | None = None
    apellido1: str | None = None
    apellido2: str | None = None
    direccion: str | None = None
    telefono_fijo: str | None = None
    telefono_movil: str | None = None
    email: str | None = None
    grupo_difusion: str | None = None
    fecha_alta: date | None = None
    fecha_baja: date | None = None
    observaciones: str | None = None
    foto: bytes | None = None


def _to_dto(obj: Socio) -> SocioDTO:
    return SocioDTO(
        id=obj.id,
        dni_nie=obj.dni_nie,
        nombre=obj.nombre,
        apellido1=obj.apellido1,
        apellido2=obj.apellido2,
        direccion=obj.direccion,
        telefono_fijo=obj.telefono_fijo,
        telefono_movil=obj.telefono_movil,
        email=obj.email,
        grupo_difusion=obj.grupo_difusion,
        fecha_alta=obj.fecha_alta,
        fecha_baja=obj.fecha_baja,
        observaciones=obj.observaciones,
        foto=obj.foto,
    )


# ───────────────── CRUD ─────────────────
def registrar_socio(datos: dict) -> int:
    """Crea un socio y devuelve su ID."""
    try:
        dto = SocioDTO(**datos)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    nuevo = Socio(
        dni_nie=dto.dni_nie,
        nombre=dto.nombre,
        apellido1=dto.apellido1,
        apellido2=dto.apellido2,
        direccion=dto.direccion,
        telefono_fijo=dto.telefono_fijo,
        telefono_movil=dto.telefono_movil,
        email=dto.email,
        grupo_difusion=dto.grupo_difusion,
        fecha_alta=dto.fecha_alta or date.today(),
        fecha_baja=dto.fecha_baja,
        observaciones=dto.observaciones,
        foto=dto.foto,
    )
    with SessionLocal() as db:
        db.add(nuevo)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("Error al registrar socio: DNI/NIE duplicado")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al registrar socio: {e}")
        db.refresh(nuevo)
        return nuevo.id


def modificar_socio(socio_id: int, cambios: dict) -> None:
    try:
        dto = SocioUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        socio = db.get(Socio, socio_id)
        if not socio:
            raise ValueError("Soci inexistent")

        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(socio, k, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Camp desconegut: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar socio: {e.orig}")

def consultar_socio(socio_id: int) -> dict | None:
    """Retorna TOT el soci (inclosa foto) com a dict o None."""
    try:
        with SessionLocal() as db:
            s = db.get(Socio, socio_id)
            return _to_dto(s).model_dump() if s else None
    except Exception as e:
        raise ValueError(f"Error al consultar soci: {e}")

def eliminar_socio(socio_id: int) -> None:
    try:
        with SessionLocal() as db:
            socio = db.get(Socio, socio_id)
            if not socio:
                raise ValueError("Soci inexistent")
            db.delete(socio)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar soci: {e.orig}")

# ────────────────── Generadores ──────────────────
def adjuntar_foto_socio(socio_id: int, filename: str) -> None:
    """Adjunta/actualiza foto a un socio."""
    with open(filename, "rb") as fh:
        foto_bytes = fh.read()

    if not foto_bytes:
        raise ValueError("Fitxer de foto buit")

    with SessionLocal() as db:
        socio = db.get(Socio, socio_id)
        if not socio:
            raise ValueError("Soci inexistent")
        socio.foto = foto_bytes
        db.commit()

def eliminar_foto_socio(socio_id: int) -> None:
    """Elimina la foto d'un soci."""
    with SessionLocal() as db:
        socio = db.get(Socio, socio_id)
        if not socio:
            raise ValueError("Soci inexistent")
        socio.foto = None
        db.commit()

# ────────────────── Consultas ──────────────────

def listar_asistencias_por_socio_clase(socio_id: int, clase_id: int) -> list[dict]:
    """Lista las asistencias de un socio a una clase específica."""
    try:
        with SessionLocal() as db:
            asistencias = db.query(AsistenciaSocio).filter(
                AsistenciaSocio.socio_id == socio_id,
                AsistenciaSocio.clase_id == clase_id
            ).all()
            return [a.model_dump() for a in asistencias]
    except Exception as e:
        raise ValueError(f"Error al listar asistencias: {e}")
    
def listar_asistencia_por_Socio(socio_id: int) -> list[dict]:
    """Consulta todas las asistencias de un socio específico."""
    try:
        with SessionLocal() as session:
            asistencias = session.query(AsistenciaSocio).filter_by(socio_id=socio_id).all()
            return [asistencia.model_dump() for asistencia in asistencias]
    except Exception as e:
        raise ValueError(f"Error al consultar asistencias: {e}")
    
def consultar_firma_LOPD(socio_id: int) -> dict | None:
    """Consulta la firma LOPD de un socio."""
    try:
        with SessionLocal() as db:
            firma = db.get(FirmaLOPD, socio_id)
            if not firma:
                return None
            return firma.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar firma LOPD: {e}")
    
# ────────────────── Exportación ──────────────────
def generar_carnet_pdf(socio_id: int, ruta_pdf: str) -> None:
    """
    Genera un carnet de soci en format PDF.
    Implementació simplificada, no inclou logo ni foto.
    """
    from exportador.pdf_carnet import generar_carnet_socio
    import os

    logo_path = "./extra/logo.png"  # Ruta del logo opcional
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"El archivo de logo no existe en la ruta: {logo_path}")
    with SessionLocal() as db:
        generar_carnet_socio(db, socio_id, ruta_pdf, logo_path=logo_path)
