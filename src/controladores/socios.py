"""
Controlador de SOCIOS — capa de negocio
Solo expone funciones que reciben/retornan dicts (DTOs) y
usan SessionLocal internamente.  La UI nunca ve objetos ORM.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from sqlalchemy.exc import IntegrityError

from database import SessionLocal          # fábrica de sesiones
from models import Socio


# ────────────────────────────────────────────────
# DTO
# ────────────────────────────────────────────────
@dataclass(slots=True)
class SocioDTO:
    id: int
    dni_nie: str
    nombre: str
    apellido1: str
    apellido2: str | None
    direccion: str | None
    telefonoFijo: str | None
    telefonoMovil: str | None
    email: str | None
    grupoDifusion: str | None
    fechaAlta: date | None
    fechaBaja: date | None
    observaciones: str | None
    foto: bytes | None


def _to_dto(obj: Socio) -> SocioDTO:
    return SocioDTO(
        id=obj.id,
        dni_nie=obj.dni_nie,
        nombre=obj.nombre,
        apellido1=obj.apellido1,
        apellido2=obj.apellido2,
        direccion=obj.direccion,
        telefonoFijo=obj.telefonoFijo,
        telefonoMovil=obj.telefonoMovil,
        email=obj.email,
        grupoDifusion=obj.grupoDifusion,
        fechaAlta=obj.fechaAlta,
        fechaBaja=obj.fechaBaja,
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
        return [asdict(_to_dto(s)) for s in socios]


def registrar_socio(datos: dict) -> int:
    """Crea un socio y devuelve su ID."""
    nuevo = Socio(
        dni_nie=datos.get("dni_nie"),
        nombre=datos.get("nombre"),
        apellido1=datos.get("apellido1"),
        apellido2=datos.get("apellido2"),
        direccion=datos.get("direccion"),
        telefonoFijo=datos.get("telefonoFijo"),
        telefonoMovil=datos.get("telefonoMovil"),
        email=datos.get("email"),
        grupoDifusion=datos.get("grupoDifusion"),
        fechaAlta=datos.get("fecha_alta", date.today()),
        fechaBaja=datos.get("fechaBaja"),
        observaciones=datos.get("observaciones"),
        foto=datos.get("foto"),
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
    with SessionLocal() as db:
        socio = db.get(Socio, socio_id)
        if not socio:
            raise ValueError("Soci inexistent")

        try:
            for k, v in cambios.items():
                setattr(socio, k, v)
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
        return asdict(_to_dto(s)) if s else None


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