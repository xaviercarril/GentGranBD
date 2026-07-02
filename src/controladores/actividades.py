"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from controladores.dtos_models import ActividadDTO, ActividadUpdateDTO
from controladores.dtos import actividad_to_dto, inscripcion_to_dto
from controladores.inscripcion_socio import consultar_socioID_InscripcionSocio, modificar_inscripcion
from controladores.dtos import normalize_phone
from controladores.socios import consultar_socio
from database import SessionLocal
from models import (
    Actividad, Clase, EstadoInscripcion, EstadoPago, InscripcionSocio, Pago, Personal, Socio, TipoActividadEnum
)

def _normalizar_tipo_actividad(tipo) -> TipoActividadEnum | None:
    if tipo is None:
        return None
    if isinstance(tipo, TipoActividadEnum):
        return tipo
    text = str(tipo).strip().upper()
    aliases = {
        "CURSO": "CURS",
        "CURSOS": "CURS",
        "CURS": "CURS",
        "TALLER": "CURS",
        "TALLERS": "CURS",
        "TALLERES": "CURS",
        "VIAJE": "VIATGE",
        "VIAJES": "VIATGE",
        "VIATGE": "VIATGE",
        "VIATGES": "VIATGE",
    }
    return TipoActividadEnum(aliases.get(text, text))


# ───────────────── CRUD ─────────────────
def registrar_actividad(data: dict) -> int:
    """Crea actividad; recibe dict, valida con DTO y devuelve ID."""
    try:
        data = {**data, "tipo": _normalizar_tipo_actividad(data.get("tipo")) or TipoActividadEnum.CURS}
        dto = ActividadDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")
    try:
        nueva = Actividad(
            nombre=dto.nombre,
            tipo=dto.tipo,
            descripcion=dto.descripcion,
            numMaxAlumnos=dto.numMaxAlumnos,
            cursoAcademicoID=dto.cursoAcademico_id,
            lugarID=dto.lugarID,
            personalID=dto.personalID,
            precio_matricula=dto.precio_matricula,
        )
        with SessionLocal() as db:
            db.add(nueva)
            db.commit()
            db.refresh(nueva)
            return nueva.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar actividad: {e.orig}")

def modificar_actividad(actividadID: int, newData: dict) -> None:
    try:
        if "tipo" in newData:
            newData = {**newData, "tipo": _normalizar_tipo_actividad(newData.get("tipo"))}
        dto = ActividadUpdateDTO(**newData)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos al modificar clase: {e}")
    
    with SessionLocal() as db:
        act = db.get(Actividad, actividadID)
        if not act:
            raise ValueError("Actividad no encontrada")
        try:
            mapeo = {
                "numMaxAlumnos": "numMaxAlumnos",
                "cursoAcademico_id": "cursoAcademicoID",
                "personalID": "personalID",
                "lugarID": "lugarID",  # Este ya coincide, pero lo puedes mantener por consistencia
            }

            for k, v in dto.model_dump(exclude_unset=True).items():
                attr = mapeo.get(k, k)  # Usa el mapeo si existe, si no el mismo nombre
                setattr(act, attr, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo no válido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar actividad: {e.orig}")

def consultar_actividad(actividadID: int) -> dict | None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividadID)
        return actividad_to_dto(act).model_dump() if act else None

def eliminar_actividad(actividadID: int) -> None:
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            if not act:
                raise ValueError("Actividad no encontrada")
            db.delete(act)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar actividad: {e.orig}")


# ────────────────── Consultas ────────────

def listar_actividades(tipo=None) -> list[dict]:
    """Devuelve todas las actividades como lista de dicts."""
    try:
        tipo_enum = _normalizar_tipo_actividad(tipo)
        with SessionLocal() as db:
            query = db.query(Actividad)
            if tipo_enum is not None:
                query = query.filter(Actividad.tipo == tipo_enum)
            acts = query.order_by(Actividad.nombre).all()
            return [actividad_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades: {e}")


def listar_actividades_resumen(curso_id: int | None = None, tipo=None) -> list[dict]:
    """Lista actividades con personal e inscritos en una consulta agregada."""
    try:
        tipo_enum = _normalizar_tipo_actividad(tipo)
        with SessionLocal() as db:
            inscritos_subq = (
                db.query(
                    InscripcionSocio.actividadID.label("actividadID"),
                    func.count(InscripcionSocio.id).label("inscritos"),
                )
                .filter(InscripcionSocio.estado == EstadoInscripcion.INSCRIT)
                .group_by(InscripcionSocio.actividadID)
                .subquery()
            )
            query = (
                db.query(
                    Actividad.id,
                    Actividad.nombre,
                    Actividad.tipo,
                    Actividad.descripcion,
                    Actividad.numMaxAlumnos,
                    Actividad.cursoAcademicoID,
                    Actividad.lugarID,
                    Actividad.precio_matricula,
                    Actividad.personalID,
                    Personal.nombre.label("personal_nombre"),
                    Personal.apellido1.label("personal_apellido1"),
                    func.coalesce(inscritos_subq.c.inscritos, 0).label("inscritos"),
                )
                .outerjoin(Personal, Personal.id == Actividad.personalID)
                .outerjoin(inscritos_subq, inscritos_subq.c.actividadID == Actividad.id)
            )
            if curso_id:
                query = query.filter(Actividad.cursoAcademicoID == curso_id)
            if tipo_enum is not None:
                query = query.filter(Actividad.tipo == tipo_enum)
            rows = query.order_by(Actividad.nombre).all()
            result = []
            for row in rows:
                personal_nombre = "Desconegut"
                if row.personal_nombre:
                    personal_nombre = f"{row.personal_nombre} {row.personal_apellido1 or ''}".strip()
                result.append(
                    {
                        "id": row.id,
                        "nombre": row.nombre,
                        "tipo": row.tipo,
                        "descripcion": row.descripcion,
                        "numMaxAlumnos": row.numMaxAlumnos,
                        "cursoAcademico_id": row.cursoAcademicoID,
                        "lugarID": row.lugarID,
                        "precio_matricula": row.precio_matricula,
                        "personalID": row.personalID,
                        "personal_nombre": personal_nombre,
                        "inscritos": int(row.inscritos or 0),
                    }
                )
            return result
    except Exception as e:
        raise ValueError(f"Error al listar resumen de actividades: {e}")

def listar_actividades_por_tipo(tipo) -> list[dict]:
    """Devuelve actividades filtradas por tipo."""
    try:
        tipo_enum = _normalizar_tipo_actividad(tipo)
        with SessionLocal() as db:
            query = db.query(Actividad)
            if tipo_enum is not None:
                query = query.filter(Actividad.tipo == tipo_enum)
            acts = query.order_by(Actividad.nombre).all()
            return [actividad_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por tipo: {e}")

def listar_inscripciones_por_Actividad(actividadID: int) -> list[dict]:
    """Devuelve inscripciones de una actividad."""
    try:
        with SessionLocal() as db:
            inscripciones = db.query(InscripcionSocio).filter(InscripcionSocio.actividadID == actividadID).all()
            return [inscripcion_to_dto(i).model_dump() for i in inscripciones]
    except Exception as e:
        raise ValueError(f"Error al listar inscripciones por actividad: {e}")


def listar_inscripciones_detalle_por_Actividad(actividadID: int) -> list[dict]:
    """Lista inscripciones con datos básicos del socio y último pago en lote."""
    try:
        with SessionLocal() as db:
            rows = (
                db.query(
                    InscripcionSocio,
                    Socio.nombre.label("socio_nombre"),
                    Socio.apellido1.label("socio_apellido1"),
                    Socio.apellido2.label("socio_apellido2"),
                    Socio.dniNie.label("socio_dniNie"),
                    Socio.telefonoMovil.label("socio_telefonoMovil"),
                )
                .outerjoin(Socio, Socio.id == InscripcionSocio.socioID)
                .filter(InscripcionSocio.actividadID == actividadID)
                .order_by(InscripcionSocio.fechaInscripcion, InscripcionSocio.id)
                .all()
            )
            inscripciones = [inscripcion_to_dto(row[0]).model_dump() for row in rows]
            by_id = {ins["id"]: ins for ins in inscripciones}
            by_pair = {
                (ins.get("socioID"), ins.get("actividadID")): ins
                for ins in inscripciones
                if ins.get("socioID")
            }

            for row in rows:
                inscripcion_orm = row[0]
                inscripcion = by_id[inscripcion_orm.id]
                if row.socio_nombre:
                    inscripcion["nombre"] = row.socio_nombre or ""
                    inscripcion["apellido1"] = row.socio_apellido1 or ""
                    inscripcion["apellido2"] = row.socio_apellido2 or ""
                    inscripcion["dniNie"] = row.socio_dniNie or ""
                    inscripcion["telefonoMovil"] = normalize_phone(row.socio_telefonoMovil) or ""
                    inscripcion["esSocio"] = inscripcion_orm.socioID
                else:
                    inscripcion["nombre"] = inscripcion.get("noSocioNombre") or "Desconegut"
                    inscripcion["apellido1"] = inscripcion.get("noSocioApellido1") or ""
                    inscripcion["apellido2"] = inscripcion.get("noSocioApellido2") or ""
                    inscripcion["dniNie"] = inscripcion.get("noSocioDni") or ""
                    inscripcion["telefonoMovil"] = normalize_phone(inscripcion.get("noSocioTelefono")) or ""
                    inscripcion["esSocio"] = "-"

            pagos = (
                db.query(Pago)
                .filter(Pago.actividadID == actividadID)
                .order_by(Pago.fecha, Pago.id)
                .all()
            )
            for pago in pagos:
                inscripcion = None
                if pago.inscripcionID:
                    inscripcion = by_id.get(pago.inscripcionID)
                if inscripcion is None:
                    inscripcion = by_pair.get((pago.socioID, pago.actividadID))
                if inscripcion is None:
                    continue
                inscripcion["_pago_id"] = pago.id
                estado = getattr(pago.estado, "value", pago.estado)
                inscripcion["pagat"] = "Sí" if estado == EstadoPago.PAGAT.value else "No"

            for inscripcion in inscripciones:
                inscripcion.setdefault("_pago_id", None)
                inscripcion.setdefault("pagat", "No")

            return inscripciones
    except Exception as e:
        raise ValueError(f"Error al listar detalle de inscripciones por actividad: {e}")
    
def listar_clases_por_Actividad(actividadID: int) -> list[dict] :
    """Devuelve clases de una actividad."""
    try:
        with SessionLocal() as db:
            clases = db.query(Clase).filter(Clase.actividadID == actividadID).all()
            return [c.model_dump() for c in clases] if clases else None
    except Exception as e:
        raise ValueError(f"Error al listar clases por actividad: {e}")
    
    
def consultar_lugarID_Actividad(actividadID: int) -> int | None:
    """Consulta el lugar de una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.lugarID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar lugar: {e}")

def consultar_cursoAcademicoID_Actividad(actividadID: int) -> int | None:
    """Consulta el curso académico de una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.cursoAcademicoID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar curso académico: {e}")
    
def consultar_personalID_Actividad(actividadID: int) -> int | None:
    """Consulta el personal asignado a una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.personalID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar personal de actividad: {e}")

def contar_inscripciones_Actividad(actividadID: int) -> int:
    """Cuenta las inscripciones a una actividad."""
    try:
        with SessionLocal() as db:
            count = db.query(InscripcionSocio).filter(InscripcionSocio.actividadID == actividadID).count()
            return count
    except Exception as e:
        raise ValueError(f"Error al contar inscripciones: {e}")
    

def actualizar_estados_inscripciones(actividadID: int) -> list[dict] | None:
    act = consultar_actividad(actividadID)
    if not act:
        return

    todas = listar_inscripciones_por_Actividad(actividadID)
    todas.sort(key=lambda i: (i["fechaInscripcion"], i["id"]))

    max_alumnes = max(0, act.get("numMaxAlumnos") or 0)

    # La fecha de inscripción determina la prioridad, con el ID como
    # desempate estable para inscripciones registradas el mismo día.
    nuevos_inscritos = todas[:max_alumnes]
    nuevos_reservas = todas[max_alumnes:]

    actualizados = []
    for ins in nuevos_inscritos:
        if ins["estado"].value != "INSCRIT":
            try:
                modificar_inscripcion(ins["id"], {"estado": "INSCRIT"})
                socioID = consultar_socioID_InscripcionSocio(ins["id"])
                socio = consultar_socio(socioID) if socioID else None
                if socio:
                    actualizados.append(socio)
            except Exception as e:
                print(f"Error promovent a INSCRIT: {e}")

    for ins in nuevos_reservas:
        if ins["estado"].value != "RESERVA":
            try:
                modificar_inscripcion(ins["id"], {"estado": "RESERVA"})
            except Exception as e:
                print(f"Error passant a RESERVA: {e}")

    return actualizados
