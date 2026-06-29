"""
Controlador de SOCIOS — capa de negocio
Solo expone funciones que reciben/retornan dicts (DTOs) y
usan SessionLocal internamente.  La UI nunca ve objetos ORM.
"""

from __future__ import annotations


from datetime import date
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError


from controladores.dtos_models import SocioDTO, SocioUpdateDTO
from database import SessionLocal  # fábrica de sesiones
from models import AsistenciaSocio, FirmaLOPD, InscripcionSocio, Socio, Pago
from controladores.dtos import asistencia_to_dto, inscripcion_to_dto, socio_to_dto, firma_to_dto, normalize_phone


def _normalize_phone_fields(datos: dict | None) -> dict:
    """Devuelve una còpia amb els telèfons sense decimals."""
    if datos is None:
        return {}
    cleaned = dict(datos)
    if "telefonoFijo" in cleaned:
        cleaned["telefonoFijo"] = normalize_phone(cleaned.get("telefonoFijo"))
    if "telefonoMovil" in cleaned:
        cleaned["telefonoMovil"] = normalize_phone(cleaned.get("telefonoMovil"))
    return cleaned

# ───────────────── CRUD ─────────────────
def registrar_socio(datos: dict) -> int:
    """Crea un socio y devuelve su ID."""
    datos = _normalize_phone_fields(datos)
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
        fechaNacimiento=dto.fechaNacimiento,
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
        except IntegrityError as e:
            db.rollback()
            msg = str(e.orig).lower() if hasattr(e, "orig") else str(e).lower()
            if "dni" in msg or "nie" in msg:
                raise ValueError("Error al registrar soci: DNI/NIE duplicat")
            if "id" in msg or "primary" in msg:
                raise ValueError("Error al registrar soci: ID duplicat")
            raise ValueError("Error al registrar soci: dades duplicades")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al registrar socio: {e}")
        db.refresh(nuevo)
        return nuevo.id


def construir_socio_modelo(datos: dict) -> Socio:
    """Valida los datos (SocioDTO) y devuelve una instancia ORM `Socio` sin persistir.
    Útil para importaciones en lote con una sola transacción.
    """
    datos = _normalize_phone_fields(datos)

    def _label(campo: str) -> str:
        mapping = {
            "dniNie": "DNI/NIE",
            "nombre": "Nom",
            "apellido1": "1r Cognom",
            "apellido2": "2n Cognom",
            "direccion": "Adreça",
            "telefonoFijo": "Telèfon",
            "telefonoMovil": "Mòbil",
            "email": "E-mail",
            "grupoDifusion": "Grup difusió",
            "fechaNacimiento": "Data naixement",
            "fechaAlta": "Data d'alta",
            "fechaBaja": "Data de baixa",
            "observaciones": "Observacions",
            "foto": "Foto",
        }
        return mapping.get(campo, campo)

    try:
        dto = SocioDTO(**datos)
    except ValidationError as e:
        # Formatea errores de validación en mensajes comprensibles
        msgs = []
        for err in e.errors():
            loc = err.get("loc", [])
            field = loc[-1] if loc else "camp"
            label = _label(str(field))
            msg = err.get("msg", "valor invàlid")
            # Simplifica mensajes comunes
            if "field required" in msg or "missing" in msg or "required" in msg:
                msg = "és obligatori"
            elif "type" in msg or "valid" in msg:
                msg = "té un format no vàlid"
            msgs.append(f"{label}: {msg}")
        raise ValueError("; ".join(msgs) or "Dades invàlides")

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
        fechaNacimiento=dto.fechaNacimiento,
        fechaAlta=dto.fechaAlta or date.today(),
        fechaBaja=dto.fechaBaja,
        observaciones=dto.observaciones,
        foto=dto.foto,
    )
    if "id" in datos and datos["id"] is not None:
        nuevo.id = datos["id"]
    return nuevo


def modificar_socio(socioID: int, cambios: dict) -> None:
    cambios = _normalize_phone_fields(cambios)
    try:
        dto = SocioUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")

        try:
            aplicats = dto.model_dump(exclude_unset=True)
            nou_id = aplicats.pop("id", None)

            for k, v in aplicats.items():
                setattr(socio, k, v)

            if nou_id is not None and nou_id != socio.id:
                if nou_id <= 0:
                    raise ValueError("L'ID ha de ser un enter positiu.")
                existent = db.get(Socio, nou_id)
                if existent:
                    raise ValueError(f"Ja existeix un soci amb l'ID {nou_id}.")

                te_inscripcions = db.query(InscripcionSocio).filter(InscripcionSocio.socioID == socio.id).first()
                te_asistencies = db.query(AsistenciaSocio).filter(AsistenciaSocio.socioID == socio.id).first()
                te_pagaments = db.query(Pago).filter(Pago.socioID == socio.id).first()
                te_lopd = db.query(FirmaLOPD).filter(FirmaLOPD.socioID == socio.id).first()
                if any((te_inscripcions, te_asistencies, te_pagaments, te_lopd)):
                    raise ValueError("No es pot modificar l'ID d'un soci que té registres relacionats.")

                socio.id = nou_id
            db.commit()
        except ValueError:
            db.rollback()
            raise
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Camp desconegut: {e}")
        except IntegrityError as e:
            db.rollback()
            msg = str(e.orig).lower() if hasattr(e, "orig") else str(e).lower()
            if "dni" in msg or "nie" in msg:
                raise ValueError("Error al modificar soci: DNI/NIE duplicat.")
            if "id" in msg or "primary" in msg:
                raise ValueError("Error al modificar soci: ID duplicat.")
            raise ValueError(f"Error al modificar soci: {e.orig}")

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
            socios = db.query(Socio).order_by(Socio.id).all()
            if not socios:
                return None
            result = []
            for s in socios:
                data = socio_to_dto(s).model_dump()
                data["telefonoFijo"] = normalize_phone(data.get("telefonoFijo"))
                data["telefonoMovil"] = normalize_phone(data.get("telefonoMovil"))
                result.append(data)
            return result
    except Exception as e:
        raise ValueError(f"Error al llistar socis: {e}")


def listar_socios_tabla() -> list[dict]:
    """Retorna els camps necessaris per a la taula de socis, sense blobs."""
    try:
        with SessionLocal() as db:
            rows = (
                db.query(
                    Socio.id,
                    Socio.apellido1,
                    Socio.apellido2,
                    Socio.nombre,
                    Socio.dniNie,
                    Socio.telefonoMovil,
                    Socio.telefonoFijo,
                    Socio.direccion,
                    Socio.fechaAlta,
                    Socio.fechaNacimiento,
                    Socio.grupoDifusion,
                    Socio.email,
                )
                .order_by(Socio.id)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "apellido1": row.apellido1,
                    "apellido2": row.apellido2,
                    "nombre": row.nombre,
                    "dniNie": row.dniNie,
                    "telefonoMovil": normalize_phone(row.telefonoMovil),
                    "telefonoFijo": normalize_phone(row.telefonoFijo),
                    "direccion": row.direccion,
                    "fechaAlta": row.fechaAlta,
                    "fechaNacimiento": row.fechaNacimiento,
                    "grupoDifusion": row.grupoDifusion,
                    "email": row.email,
                }
                for row in rows
            ]
    except Exception as e:
        raise ValueError(f"Error al llistar socis per a la taula: {e}")


def listar_socios_activos() -> list[dict]:
    """Retorna una llista de dicts amb els socis actius."""
    try:
        with SessionLocal() as db:
            socios = db.query(Socio).filter(Socio.fechaBaja.is_(None)).order_by(Socio.id).all()
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
    """Consulta l'estat de la firma LOPD d'un soci (sense recuperar el PDF)."""
    try:
        with SessionLocal() as db:
            firma = db.get(FirmaLOPD, socioID)
            if not firma:
                return None
            return {
                "socioID": firma.socioID,
                "fechaFirma": firma.fechaFirma,
                "tieneDocumento": bool(firma.documento),
            }
    except Exception as e:
        raise ValueError(f"Error al consultar firma LOPD: {e}")


def obtener_documento_firma_LOPD(socioID: int) -> tuple[bytes, date]:
    """Retorna el PDF signat i la data de firma."""

    try:
        with SessionLocal() as db:
            firma = db.get(FirmaLOPD, socioID)
            if not firma or not firma.documento:
                raise ValueError("No hi ha cap document signat")
            return firma.documento, firma.fechaFirma
    except Exception as e:
        raise ValueError(f"Error al obtenir el document LOPD: {e}")


def guardar_documento_firma_LOPD(socioID: int, documento: bytes, fechaFirma: date | None = None) -> None:
    """Crea o actualitza el PDF signat de la LOPD."""

    if not documento:
        raise ValueError("El document rebut està buit")

    fecha = fechaFirma or date.today()

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")

        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            firma = FirmaLOPD(socioID=socioID, fechaFirma=fecha, documento=documento)
            db.add(firma)
        else:
            firma.fechaFirma = fecha
            firma.documento = documento
        db.commit()


def eliminar_documento_firma_LOPD(socioID: int) -> None:
    """Elimina el PDF signat de la LOPD per a un soci."""

    with SessionLocal() as db:
        firma = db.get(FirmaLOPD, socioID)
        if not firma:
            raise ValueError("No hi ha cap document registrat")
        db.delete(firma)
        db.commit()
    
# ────────────────── Exportación ──────────────────

def _resolve_logo_path() -> str | None:
    for path in (Path("extra/logo.png"), Path("src/extra/logo.png")):
        if path.exists():
            return str(path)
    return None


def generar_carnet_pdf(socioID: int, ruta_pdf: str) -> None:
    """
    Genera un carnet de soci en format PDF.
    Implementació simplificada, no inclou logo ni foto.
    """
    from exportador.pdf_carnet import generar_carnet_socio

    logo_path = _resolve_logo_path()
    with SessionLocal() as db:
        generar_carnet_socio(db, socioID, ruta_pdf, logo_path=logo_path)


def generar_ficha_socio_pdf(socioID: int, ruta_pdf: str) -> None:
    """Genera una ficha de socio de 10 x 15 cm en format PDF."""
    from exportador.pdf_ficha_socio import generar_ficha_socio

    logo_path = _resolve_logo_path()
    with SessionLocal() as db:
        generar_ficha_socio(db, socioID, ruta_pdf, logo_path=logo_path)


def generar_hoja_ficha_carnet_pdf(socioID: int, ruta_pdf: str) -> None:
    """Genera un A4 imprimible amb la fitxa i el carnet del soci."""
    from exportador.pdf_ficha_carnet import generar_hoja_ficha_carnet_socio

    logo_path = _resolve_logo_path()
    with SessionLocal() as db:
        generar_hoja_ficha_carnet_socio(db, socioID, ruta_pdf, logo_path=logo_path)


def generar_socios_tabla_pdf(socios: list[dict], ruta_pdf: str) -> None:
    """Genera un PDF amb les files visibles de la taula de socis."""
    from exportador.pdf_socios import generar_pdf_socios_tabla

    generar_pdf_socios_tabla(socios or [], ruta_pdf)

# Añadido: generar_pdf_LOPD para exportar consentimiento de protección de datos
def generar_pdf_LOPD(
    socioID: int,
    ruta_pdf: str,
    *,
    firma: bytes | str | Path | None = None,
    fechaFirma: date | None = None,
    abrir: bool = True,
) -> None:
    """Genera el PDF LOPD; pot incrustar una signatura si es facilita."""

    from exportador.pdf_LOPD import generar_pdf_lopd

    with SessionLocal() as db:
        socio = db.get(Socio, socioID)
        if not socio:
            raise ValueError("Soci inexistent")
        nombre_completo = f"{socio.nombre} {socio.apellido1 or ''} {socio.apellido2 or ''}".strip()
        generar_pdf_lopd(
            nombre_completo,
            socio.dniNie,
            ruta_pdf,
            firma=firma,
            fecha_firma=fechaFirma,
            abrir=abrir,
        )
