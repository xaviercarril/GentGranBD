from models import FirmaLOPD, Socio
from sqlalchemy import Column, Integer, String, Date, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ValidationError
from database import SessionLocal
from sqlalchemy.exc import IntegrityError
from dataclasses import dataclass

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class FirmaLOPDDTO(BaseModel):
    socioID: int
    fecha: Date | None = None
    firma: bytes | None = None

class FirmaLOPDUpdateDTO(BaseModel):
    fecha: Date | None = None
    firma: bytes | None = None

def _to_dto(firma: FirmaLOPD) -> FirmaLOPDDTO:
    return FirmaLOPDDTO(
        socioID=firma.socioID,
        fecha=firma.fecha,
        firma=firma.firma
    )

# ───────────────── CRUD ─────────────────
def registrar_firmaLOPD(datos: dict) -> int:
    """Registra una nueva firma LOPD; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = FirmaLOPDDTO(**datos)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    nueva_firma = FirmaLOPD(
        socioID=dto.socioID,
        fecha=dto.fecha,
        firma=dto.firma
    )

    try:
        with SessionLocal() as db:
            db.add(nueva_firma)
            db.commit()
            db.refresh(nueva_firma)
            return nueva_firma.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar firma LOPD: {e.orig}")
    
def modificar_firmaLOPD(socioID: int, cambios: dict) -> None:
    """Modifica una firma LOPD; recibe ID de socio y dict con cambios."""
    try:
        dto = FirmaLOPDUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            raise ValueError("Firma LOPD inexistent")

        try:
            for key, value in dto.model_dump().items():
                setattr(firma, key, value)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error de integridad: {e.orig}")

def consultar_firmaLOPD(socioID: int) -> dict:
    """Consulta una firma LOPD por ID de socio."""
    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            raise ValueError("Firma LOPD no encontrada")
        return _to_dto(firma).model_dump()
        
def eliminar_firmaLOPD(socioID: int) -> None:
    """Elimina una firma LOPD por ID de socio."""
    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            raise ValueError("Firma LOPD no encontrada")
        db.delete(firma)
        db.commit()

# ────────────────── Consultas ──────────────────
def consultar_socio_por_FirmaLOPD(firma_id: int) -> dict | None:
    """Consulta un socio por ID de firma LOPD y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            firma = db.get(FirmaLOPD, firma_id)
            if not firma:
                return None
            socio = db.get(Socio, firma.socioID)
            if not socio:
                return None
            return socio.model_dump() if socio else None
    except Exception as e:
        raise ValueError(f"Error al consultar socio por firma LOPD: {e}")