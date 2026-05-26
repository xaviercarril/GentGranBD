# Nuevo módulo para convertir instancias de SQLAlchemy a DTOs
import math
from decimal import Decimal
from datetime import datetime
from controladores.dtos_models import AsistenciaSocioDTO, ClaseDTO, CursoAcademicoDTO, FirmaLOPDDTO, InscripcionSocioDTO, LugarDTO, PagoDTO, SocioDTO, ActividadDTO, PersonalDTO, TrimestreDTO
from models import AsistenciaSocio, Clase, CursoAcademico, FirmaLOPD, InscripcionSocio, Lugar, Pago, Socio, Actividad, Personal, Trimestre


def normalize_phone(value) -> str | None:
    """Normalitza telèfons provinents de decimals o floats (p. ex. '6.0')."""
    if value is None:
        return None

    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return str(int(value))
        text = format(value, "f").rstrip("0").rstrip(".")
        return text or "0"

    if isinstance(value, Decimal):
        if value == value.to_integral():
            return str(int(value))
        text = format(value, "f").rstrip("0").rstrip(".")
        return text or "0"

    text = str(value).strip()
    if not text:
        return None

    lowered = text.lower()
    if lowered in {"nan", "none", "na"}:
        return None

    if "." in text:
        whole, frac = text.split(".", 1)
        if frac and set(frac) <= {"0"}:
            text = whole

    return text


def inscripcion_to_dto(inscripcion: InscripcionSocio) -> InscripcionSocioDTO:
    return InscripcionSocioDTO(
        id=inscripcion.id,
        socioID=inscripcion.socioID,
        actividadID=inscripcion.actividadID,
        fechaInscripcion=inscripcion.fechaInscripcion,
        estado=inscripcion.estado,
        observaciones=inscripcion.observaciones,
        fechaBaja=inscripcion.fechaBaja
    )


def socio_to_dto(socio: Socio) -> SocioDTO:
    return SocioDTO(
        id=socio.id,
        dniNie=socio.dniNie,
        nombre=socio.nombre,
        apellido1=socio.apellido1,
        apellido2=socio.apellido2,
        direccion=socio.direccion,
        telefonoFijo=normalize_phone(socio.telefonoFijo),
        telefonoMovil=normalize_phone(socio.telefonoMovil),
        email=socio.email,
        grupoDifusion=socio.grupoDifusion,
        fechaNacimiento=socio.fechaNacimiento,
        fechaAlta=socio.fechaAlta,
        fechaBaja=socio.fechaBaja,
        observaciones=socio.observaciones,
        foto=socio.foto,
    )


def actividad_to_dto(act: Actividad) -> ActividadDTO:
    return ActividadDTO(
        id=act.id,
        nombre=act.nombre,
        descripcion=act.descripcion,
        numMaxAlumnos=act.numMaxAlumnos,
        cursoAcademico_id=act.cursoAcademicoID,
        lugarID=act.lugarID,
        precio_matricula=act.precio_matricula,
        personalID=act.personalID
    )


def personal_to_dto(p: Personal) -> PersonalDTO:
    return PersonalDTO(
        id=p.id,
        nombre=p.nombre,
        apellido1=p.apellido1,
        apellido2=p.apellido2,
        email=p.email,
        telfMovil=p.telfMovil,
        observaciones=p.observaciones
    )

def asistencia_to_dto(asistencia: AsistenciaSocio) -> AsistenciaSocioDTO:
    return AsistenciaSocioDTO(
        socioID=asistencia.socioID,
        claseID=asistencia.claseID,
        presente=asistencia.presente,
        observaciones=asistencia.observaciones
    )

def clase_to_dto(clase: Clase) -> ClaseDTO:
    return ClaseDTO(
        id=clase.id,
        actividadID=clase.actividadID,
        trimestreID=clase.trimestreID,
        fecha=clase.fecha,
        horaInicio=clase.horaInicio.time() if isinstance(clase.horaInicio, datetime) else clase.horaInicio,
        horaFin=clase.horaFin.time() if isinstance(clase.horaFin, datetime) else clase.horaFin,
        duracion=clase.duracion
    )
    
def cursoA_to_dto(curso: CursoAcademico) -> CursoAcademicoDTO:
  return CursoAcademicoDTO(
    id=curso.id,
    nombre=curso.nombre,
    fechaInicio=curso.fechaInicio,
    fechaFin=curso.fechaFin
  )

def firma_to_dto(firma: FirmaLOPD) -> FirmaLOPDDTO:
    return FirmaLOPDDTO(
        socioID=firma.socioID,
        fechaFirma=firma.fechaFirma,
        documento=firma.documento
    )

def lugar_to_dto(lugar: Lugar) -> LugarDTO:
    return LugarDTO(
        id=lugar.id,
        nombre=lugar.nombre,
        direccion=lugar.direccion
    )

def pago_to_dto(pago: Pago) -> PagoDTO:
    return PagoDTO(
        id=pago.id,
        socioID=pago.socioID,
        actividadID=pago.actividadID,
        fecha_pago=pago.fecha,
        importe=pago.importe,
        estado=pago.estado,
        observaciones=pago.observaciones
    )

def trimestre_to_dto(trimestre: Trimestre) -> TrimestreDTO:
    return TrimestreDTO(
        id=trimestre.id,
        nombre=trimestre.nombre,
        fechaInicio=trimestre.fechaInicio,
        fechaFin=trimestre.fechaFin,
        cursoAcademicoID=trimestre.cursoAcademicoID
    )
