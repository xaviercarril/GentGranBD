"""Helpers per gestionar la firma digital de la LOPD."""

from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from controladores.dtos import firma_to_dto, socio_to_dto
from controladores.dtos_models import FirmaLOPDDTO, FirmaLOPDUpdateDTO
from database import SessionLocal
from models import FirmaLOPD, Socio


def registrar_firma_lopd(datos: dict) -> None:
    """Crea o reemplaza la firma LOPD per a un soci."""

    try:
        dto = FirmaLOPDDTO(**datos)
    except ValidationError as exc:
        raise ValueError(f"Dades de firma invàlides: {exc}") from exc

    with SessionLocal() as db:
        socio = db.get(Socio, dto.socioID)
        if not socio:
            raise ValueError("Soci inexistent")

        firma = db.get(FirmaLOPD, dto.socioID)
        if not firma:
            firma = FirmaLOPD(
                socioID=dto.socioID,
                fechaFirma=dto.fechaFirma,
                documento=dto.documento,
            )
            db.add(firma)
        else:
            firma.fechaFirma = dto.fechaFirma
            firma.documento = dto.documento

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"No s'ha pogut registrar la firma LOPD: {exc.orig}") from exc


def modificar_firma_lopd(socio_id: int, canvis: dict) -> None:
    """Actualitza parcialment una firma LOPD existent."""

    try:
        dto = FirmaLOPDUpdateDTO(**canvis)
    except ValidationError as exc:
        raise ValueError(f"Canvis invàlids: {exc}") from exc

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socio_id)
        if not firma:
            raise ValueError("La firma LOPD no existeix")

        if dto.fechaFirma is not None:
            firma.fechaFirma = dto.fechaFirma
        if dto.documento is not None:
            firma.documento = dto.documento

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Error en modificar la firma: {exc.orig}") from exc


def consultar_firma_lopd(socio_id: int) -> dict | None:
    """Recupera la firma LOPD d'un soci. Retorna dict o ``None``."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socio_id)
        if not firma:
            return None
        return firma_to_dto(firma).model_dump()


def eliminar_firma_lopd(socio_id: int) -> None:
    """Elimina la firma LOPD d'un soci."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socio_id)
        if not firma:
            raise ValueError("La firma LOPD no existeix")
        db.delete(firma)
        db.commit()


def consultar_socio_per_firma(firma_id: int) -> dict | None:
    """Retorna les dades del soci associat a una firma LOPD."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, firma_id)
        if not firma:
            return None
        socio = db.get(Socio, firma.socioID)
        if not socio:
            return None
        return socio_to_dto(socio).model_dump()
