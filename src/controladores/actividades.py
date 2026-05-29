"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError

from controladores.dtos_models import ActividadDTO, ActividadUpdateDTO
from controladores.dtos import actividad_to_dto, inscripcion_to_dto
from controladores.inscripcion_socio import consultar_socioID_InscripcionSocio, modificar_inscripcion
from controladores.socios import consultar_socio
from database import SessionLocal
from models import (
    Actividad, Clase, InscripcionSocio, TipoActividadEnum
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

    # Separar inscripciones
    reservas = [i for i in todas if i["estado"].value == "RESERVA"]
    inscritos = [i for i in todas if i["estado"].value == "INSCRIT"]

    # Ordenar por fecha
    reservas.sort(key=lambda i: i["fechaInscripcion"])
    inscritos.sort(key=lambda i: i["fechaInscripcion"])

    max_alumnes = act.get("numMaxAlumnos", 0)

    # Determinar quién debe estar inscrito y quién en reserva
    nuevos_inscritos = inscritos[:max_alumnes] + reservas[: max(0, max_alumnes - len(inscritos))]
    nuevos_reservas = inscritos[max_alumnes:] + reservas[max(0, max_alumnes - len(inscritos)) :]

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
