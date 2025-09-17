# Nuevo módulo para convertir instancias de SQLAlchemy a DTOs
from pydantic import BaseModel
from datetime import date, datetime, time, timedelta
from models import AsistenciaSocio, Clase, CursoAcademico, FirmaLOPD, InscripcionSocio, Lugar, Pago, Socio, Actividad, Personal, Trimestre, EstadoInscripcion, EstadoPago, TrimestreEnum

# ─────────────────────────────── DTOs ───────────────────────────────

class ActividadDTO(BaseModel):
    id: int | None = None
    nombre: str
    descripcion: str | None = None
    numMaxAlumnos: int | None = 0
    cursoAcademico_id: int
    lugarID: int | None = None
    personalID: int | None = None   
    precio_matricula: float = 0.0

class ActividadUpdateDTO(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    numMaxAlumnos: int | None = None
    cursoAcademico_id: int | None = None
    lugarID: int | None = None
    personalID: int | None = None
    precio_matricula: float | None = None

class AsistenciaSocioDTO(BaseModel):
    socioID: int
    claseID: int
    presente: bool = False
    observaciones: str | None = None

class AsistenciaSocioUpdateDTO(BaseModel):
    presente: bool | None = None
    observaciones: str | None = None

class ClaseDTO(BaseModel):
    id: int | None = None
    actividadID: int
    trimestreID: int
    fecha: date | None = None
    horaInicio: time | None = None
    horaFin: time | None = None
    duracion: int | None = None
    diasSemana: list[int] | None = None  # 0=Lunes, 6=Domingo

class ClaseUpdateDTO(BaseModel):
    fecha: date | None = None
    horaInicio: time | None = None
    horaFin: time | None = None
    duracion: int | None = None
    trimestreID: int | None = None

class CursoAcademicoDTO(BaseModel):
  id: int | None = None
  nombre: str
  fechaInicio: date
  fechaFin: date

class CursoAcademicoUpdateDTO(BaseModel):
  nombre: str | None = None
  fechaInicio: date | None = None
  fechaFin: date | None = None

class FirmaLOPDDTO(BaseModel):
    socioID: int
    fechaFirma: date
    documento: bytes


class FirmaLOPDUpdateDTO(BaseModel):
    fechaFirma: date | None = None
    documento: bytes | None = None

class InscripcionSocioDTO(BaseModel):
    id: int | None = None
    socioID: int
    actividadID: int
    fechaInscripcion: date
    estado: EstadoInscripcion = EstadoInscripcion.RESERVA
    observaciones: str | None = None
    fechaBaja: date | None = None

class InscripcionSocioUpdateDTO(BaseModel):
    socioID: int | None = None
    actividadID: int | None = None
    fechaInscripcion: date | None = None
    estado: EstadoInscripcion | None = None
    observaciones: str | None = None
    fechaBaja: date | None = None

class LugarDTO(BaseModel):
    id: int | None = None
    nombre: str
    direccion: str | None = None

class LugarUpdateDTO(BaseModel):
    nombre: str | None = None
    direccion: str | None = None

class PagoDTO(BaseModel):
    id: int | None = None
    socioID: int
    actividadID: int
    fecha_pago: date
    importe: float = 0.0
    estado: str = "PENDENT"  # Estado por defecto

class PagoUpdateDTO(BaseModel):
    fecha_pago: date | None = None
    estado: str | None = None
    importe: float | None = None

class SocioDTO(BaseModel):
    id: int | None = None
    dniNie: str
    nombre: str
    apellido1: str
    apellido2: str | None = None
    direccion: str | None = None
    telefonoFijo: str | None = None
    telefonoMovil: str | None = None
    email: str | None = None
    grupoDifusion: str | None = None
    fechaAlta: date
    fechaBaja: date | None = None
    observaciones: str | None = None
    foto: bytes | None = None


class SocioUpdateDTO(BaseModel):
    dniNie: str | None = None
    nombre: str | None = None
    apellido1: str | None = None
    apellido2: str | None = None
    direccion: str | None = None
    telefonoFijo: str | None = None
    telefonoMovil: str | None = None
    email: str | None = None
    grupoDifusion: str | None = None
    fechaAlta: date | None = None
    fechaBaja: date | None = None
    observaciones: str | None = None
    foto: bytes | None = None


class PersonalDTO(BaseModel):
    id: int | None = None
    nombre: str
    apellido1: str
    apellido2: str | None = None
    dniNie: str | None = None
    email: str | None = None
    telfMovil: str | None = None
    observaciones: str | None = None

class PersonalUpdateDTO(BaseModel):
    nombre: str | None = None
    apellido1: str | None = None
    apellido2: str | None = None
    dniNie: str | None = None
    email: str | None = None
    telfMovil: str | None = None
    observaciones: str | None = None


class TrimestreDTO(BaseModel):
    id: int | None = None
    nombre: TrimestreEnum
    fechaInicio: date
    fechaFin: date
    cursoAcademicoID: int

class TrimestreUpdateDTO(BaseModel):
    nombre: TrimestreEnum | None = None
    fechaInicio: date | None = None
    fechaFin: date | None = None
    cursoAcademicoID: int | None = None
