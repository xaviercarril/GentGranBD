"""
Controlador de SOCIOS — capa de negocio
Solo expone funciones que reciben/retornan dicts (DTOs) y
usan SessionLocal internamente.  La UI nunca ve objetos ORM.
"""

from __future__ import annotations


from datetime import date
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError


from controladores.dtos_models import SocioDTO, SocioUpdateDTO
from database import SessionLocal  # fábrica de sesiones
from models import AsistenciaSocio, FirmaLOPD, InscripcionSocio, Socio
from controladores.dtos import asistencia_to_dto, firma_to_dto, inscripcion_to_dto, socio_to_dto

# ───────────────── CRUD ─────────────────
def registrar_socio(datos: dict) -> int:
    """Crea un socio y devuelve su ID."""
    try:
        dto = SocioDTO(**datos)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    nuevo = Socio(
        dniNie=dto.dniNie,
        nombre=dto.nombre,
        apellido1=dto.apellido1,
        apellido2=dto.apellido2,
        direccion=dto.direccion,
        telefonoFijo=dto.telefonoFijo,
        telefonoMovil=dto.telefonoMovil,
        email=dto.email,
        grupoDifusion=dto.grupoDifusion,
        fechaAlta=dto.fechaAlta or date.today(),
        fechaBaja=dto.fechaBaja,
        observaciones=dto.observaciones,
        foto=dto.foto,
    )
        # 🔸 Solo si el ID está explícitamente en los datos, se fuerza
    if "id" in datos and datos["id"] is not None:
        nuevo.id = datos["id"]

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


def modificar_socio(socioID: int, cambios: dict) -> None:
    try:
        dto = SocioUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
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

def consultar_socio(socioID: int) -> dict | None:
    """Retorna TOT el soci (inclosa foto) com a dict o None."""
    try:
        with SessionLocal() as db:
            s = db.get(Socio, socioID)
            return socio_to_dto(s).model_dump() if s else None
    except Exception as e:
        raise ValueError(f"Error al consultar soci: {e}")

def eliminar_socio(socioID: int) -> None:
    try:
        with SessionLocal() as db:
            socio = db.get(Socio, socioID)
            if not socio:
                raise ValueError("Soci inexistent")
            db.delete(socio)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar soci: {e.orig}")

# ────────────────── Generadores ──────────────────
def adjuntar_foto_socio(socioID: int, filename: str) -> None:
    """Adjunta/actualiza foto a un socio."""
    with open(filename, "rb") as fh:
        foto_bytes = fh.read()

    if not foto_bytes:
        raise ValueError("Fitxer de foto buit")

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")
        socio.foto = foto_bytes
        db.commit()

def eliminar_foto_socio(socioID: int) -> None:
    """Elimina la foto d'un soci."""
    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")
        socio.foto = None
        db.commit()

# ────────────────── Consultas ──────────────────
def listar_socios() -> list[dict]:
    """Retorna una llista de dicts amb tots els socis."""
    try:
        with SessionLocal() as db:
            socios = db.query(Socio).all()
            if not socios:
                return None
            return [socio_to_dto(s).model_dump() for s in socios]
    except Exception as e:
        raise ValueError(f"Error al llistar socis: {e}")

def listar_socios_activos() -> list[dict]:
    """Retorna una llista de dicts amb els socis actius."""
    try:
        with SessionLocal() as db:
            socios = db.query(Socio).filter(Socio.fechaBaja.is_(None)).all()
            return [socio_to_dto(s).model_dump() for s in socios]
    except Exception as e:
        raise ValueError(f"Error al llistar socis actius: {e}")

def listar_asistencias_por_socio_clase(socioID: int, claseID: int) -> list[dict]:
    """Lista las asistencias de un socio a una clase específica."""
    try:
        with SessionLocal() as db:
            asistencias = db.query(AsistenciaSocio).filter(
                AsistenciaSocio.socioID == socioID,
                AsistenciaSocio.claseID == claseID
            ).all()
            return [asistencia_to_dto(a).model_dump() for a in asistencias]
    except Exception as e:
        raise ValueError(f"Error al listar asistencias: {e}")
    
def listar_asistencia_por_Socio(socioID: int) -> list[dict]:
    """Consulta todas las asistencias de un socio específico."""
    try:
        with SessionLocal() as session:
            asistencias = session.query(AsistenciaSocio).filter_by(socioID=socioID).all()
            return [asistencia.model_dump() for asistencia in asistencias]
    except Exception as e:
        raise ValueError(f"Error al consultar asistencias: {e}")
    
def listar_inscripciones_por_socio(socioID: int) -> list[dict]:
    """Lista las inscripciones de un socio."""
    try:
        with SessionLocal() as db:
            inscripciones = db.query(InscripcionSocio).filter(InscripcionSocio.socioID == socioID).all()
            return [inscripcion_to_dto(ins).model_dump() for ins in inscripciones]
    except Exception as e:
        raise ValueError(f"Error al listar inscripciones: {e}")
    
def consultar_firma_LOPD(socioID: int) -> dict | None:
    """Consulta la firma LOPD de un socio."""
    try:
        with SessionLocal() as db:
            firma = db.get(FirmaLOPD, socioID)
            if not firma:
                return None
            return firma_to_dto(firma).model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar firma LOPD: {e}")
    
# ────────────────── Exportación ──────────────────

def generar_carnet_pdf(socioID: int, ruta_pdf: str) -> None:
    """
    Genera un carnet de soci en format PDF.
    Implementació simplificada, no inclou logo ni foto.
    """
    from exportador.pdf_carnet import generar_carnet_socio
    import os

    logo_path = "./extra/logo.png"  # Ruta del logo opcional
    if not os.path.exists(logo_path):
        # No bloquear la generación si falta el logo; es opcional
        logo_path = None
    with SessionLocal() as db:
        generar_carnet_socio(db, socioID, ruta_pdf, logo_path=logo_path)

# Añadido: generar_pdf_LOPD para exportar consentimiento de protección de datos
def generar_pdf_LOPD(socioID: int, ruta_pdf: str) -> None:
    """
    Genera el PDF de consentiment de protecció de dades (LOPD) per a un soci.
    """
    from exportador.pdf_LOPD import generar_pdf_lopd

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")
        nombre_completo = f"{socio.nombre} {socio.apellido1 or ''} {socio.apellido2 or ''}".strip()
        generar_pdf_lopd(nombre_completo, socio.dniNie, ruta_pdf)
