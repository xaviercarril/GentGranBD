"""
Controlador de SOCIOS — capa de negocio
Solo expone funciones que reciben/retornan dicts (DTOs) y
usan SessionLocal internamente.  La UI nunca ve objetos ORM.
"""

from __future__ import annotations


from dataclasses import asdict
from datetime import date
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError


from database import SessionLocal  # fábrica de sesiones
from models import Socio


# ────────────────────────────────────────────────
# DTO
# ────────────────────────────────────────────────
class SocioDTO(BaseModel):

    id: int | None = None
    dni_nie: str
    nombre: str
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
        telefono_fijo=obj.telefonoFijo,
        telefono_movil=obj.telefonoMovil,
        email=obj.email,
        grupo_difusion=obj.grupoDifusion,
        fecha_alta=obj.fechaAlta,
        fecha_baja=obj.fechaBaja,
        observaciones=obj.observaciones,
        foto=obj.foto,
    )


# ────────────────────────────────────────────────
# API Pública
# ────────────────────────────────────────────────
def listar_socios() -> list[dict]:
    """Devuelve todos los socios como lista de dicts ordenados por nombre."""
    with SessionLocal() as db:
        socios = db.query(Socio).order_by(Socio.nombre).all()
        return [_to_dto(s).model_dump() for s in socios]


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
        telefonoFijo=dto.telefono_fijo,
        telefonoMovil=dto.telefono_movil,
        email=dto.email,
        grupoDifusion=dto.grupo_difusion,
        fechaAlta=dto.fecha_alta or date.today(),
        fechaBaja=dto.fecha_baja,
        observaciones=dto.observaciones,
        foto=dto.foto,
    )
    with SessionLocal() as db:
        db.add(nuevo)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("DNI/NIE duplicado")
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

        mapping = {
            "telefono_fijo": "telefonoFijo",
            "telefono_movil": "telefonoMovil",
            "grupo_difusion": "grupoDifusion",
            "fecha_alta": "fechaAlta",
            "fecha_baja": "fechaBaja",
        }

        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(socio, mapping.get(k, k), v)

            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Camp desconegut: {e}")


def eliminar_socio(socio_id: int) -> None:
    with SessionLocal() as db:
        socio = db.get(Socio, socio_id)
        if not socio:
            raise ValueError("Soci inexistent")
        db.delete(socio)
        db.commit()


def consultar_socio(socio_id: int) -> dict | None:
    """Retorna TOT el soci (inclosa foto) com a dict o None."""
    with SessionLocal() as db:
        s = db.get(Socio, socio_id)
        return _to_dto(s).model_dump() if s else None


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
