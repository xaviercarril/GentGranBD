from __future__ import annotations

from datetime import date

from controladores.dtos import firma_to_dto
from database import SessionLocal
from models import FirmaLOPD


# ---------------------------------------------------------------------------
# CRUD per a la firma del consentiment LOPD
# ---------------------------------------------------------------------------

def guardar_firma_lopd(socioID: int, documento: bytes, fecha: date | None = None) -> None:
    """Crea o actualitza la firma LOPD d'un soci."""

    fecha = fecha or date.today()

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if firma:
            firma.documento = documento
            firma.fechaFirma = fecha
        else:
            firma = FirmaLOPD(socioID=socioID, documento=documento, fechaFirma=fecha)
            db.add(firma)
        db.commit()


def consultar_firma_lopd(socioID: int) -> dict | None:
    """Retorna la firma LOPD d'un soci com a dict o ``None``."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            return None
        return firma_to_dto(firma).model_dump()


def eliminar_firma_lopd(socioID: int) -> None:
    """Elimina la firma LOPD d'un soci si existeix."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            return
        db.delete(firma)
        db.commit()

