from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean, Text, DECIMAL,
    ForeignKey, ForeignKeyConstraint, LargeBinary, Enum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

# ---------------------------------------------
# SQLAlchemy base declarative class
# ---------------------------------------------
Base = declarative_base()

# ---------------------------------------------
# ENUMERATIONS
# ---------------------------------------------
class TrimestreEnum(enum.Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class EstadoInscripcion(enum.Enum):
    INSCRITO = "INSCRITO"
    RESERVA = "RESERVA"


class EstadoPago(enum.Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    ANULADO = "ANULADO"

# ---------------------------------------------
# SOCIO + GDPR CONSENT
# ---------------------------------------------
class Socio(Base):
    __tablename__ = "socios"

    id = Column(Integer, primary_key=True)
    dni_nie = Column(String(15), unique=True, nullable=False)
    nombre = Column(String(50), nullable=False)
    apellido1 = Column(String(50))
    apellido2 = Column(String(50))
    direccion = Column(String(255))
    telefono_fijo = Column(String(20))
    telefono_movil = Column(String(20))
    email = Column(String(100))
    grupo_difusion = Column(String(50))
    fecha_alta = Column(Date, nullable=False)
    fecha_baja = Column(Date)
    observaciones = Column(Text)
    foto = Column(LargeBinary)

    # Relationships
    inscripciones = relationship("InscripcionSocio", back_populates="socio", cascade="all, delete-orphan")
    asistencias = relationship("AsistenciaSocio", back_populates="socio", cascade="all, delete-orphan")
    firma = relationship("FirmaLOPD", back_populates="socio", uselist=False, cascade="all, delete-orphan")


class FirmaLOPD(Base):
    """One-to-one table that stores the GDPR consent signature."""
    __tablename__ = "firma_proteccion_datos"

    socio_id = Column(Integer, ForeignKey("socios.id"), primary_key=True)
    fecha_firma = Column(Date, nullable=False)
    documento = Column(LargeBinary, nullable=False)

    socio = relationship("Socio", back_populates="firma")

# ---------------------------------------------
# PERSONAL HIERARCHY (VOLUNTEER/TEACHER)
# ---------------------------------------------
class Personal(Base):
    __tablename__ = "personal"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    apellido1 = Column(String(50))
    apellido2 = Column(String(50))
    dni_nie = Column(String(15), unique=True, nullable=False)
    tipo = Column(String(50))  # Needed for single-table inheritance discriminator

    # Bridge to activities
    actividades_as_monitor = relationship(
        "ActividadPersonal",
        back_populates="personal",
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {
        "polymorphic_identity": "personal",
        "polymorphic_on": tipo,
    }


class Voluntario(Personal):
    __mapper_args__ = {
        "polymorphic_identity": "voluntario",
    }


class Profesor(Personal):
    __mapper_args__ = {
        "polymorphic_identity": "profesor",
    }

# ---------------------------------------------
# LOCATION
# ---------------------------------------------
class Lugar(Base):
    __tablename__ = "lugares"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(255))

    actividades = relationship("Actividad", back_populates="lugar")

# ---------------------------------------------
# ACADEMIC YEAR & TERM
# ---------------------------------------------
class CursoAcademico(Base):
    __tablename__ = "curso_academico"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)

    actividades = relationship("Actividad", back_populates="curso", cascade="all, delete-orphan")
    trimestres = relationship("Trimestre", back_populates="curso", cascade="all, delete-orphan")


class Trimestre(Base):
    __tablename__ = "trimestres"

    id = Column(Integer, primary_key=True)
    nombre = Column(Enum(TrimestreEnum), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)

    cursoA_id = Column(Integer, ForeignKey("curso_academico.id"), nullable=False)
    curso = relationship("CursoAcademico", back_populates="trimestres")

    clases = relationship("Clase", back_populates="trimestre", cascade="all, delete-orphan")

# ---------------------------------------------
# ACTIVITIES
# ---------------------------------------------
class Actividad(Base):
    __tablename__ = "actividades"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    numero_maximo_alumnos = Column(Integer)
    precio_matricula = Column(DECIMAL(10, 2), default=0.0)
    observaciones = Column(Text)

    # Foreign Keys
    cursoA_id = Column(Integer, ForeignKey("curso_academico.id"))
    lugar_id = Column(Integer, ForeignKey("lugares.id"))

    # Relationships
    curso = relationship("CursoAcademico", back_populates="actividades")
    lugar = relationship("Lugar", back_populates="actividades")

    clases = relationship("Clase", back_populates="actividad", cascade="all, delete-orphan")
    inscripciones = relationship("InscripcionSocio", back_populates="actividad", cascade="all, delete-orphan")
    monitores = relationship("ActividadPersonal", back_populates="actividad", cascade="all, delete-orphan")

# Bridge table allowing multiple monitors per activity and historical tracking
class ActividadPersonal(Base):
    __tablename__ = "actividad_personal"

    actividad_id = Column(Integer, ForeignKey("actividades.id"), primary_key=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), primary_key=True)
    rol = Column(String(50))

    actividad = relationship("Actividad", back_populates="monitores")
    personal = relationship("Personal", back_populates="actividades_as_monitor")

# ---------------------------------------------
# CLASS SESSIONS
# ---------------------------------------------
class Clase(Base):
    __tablename__ = "clases"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    hora_inicio = Column(DateTime)
    hora_fin = Column(DateTime)
    duracion = Column(Integer)

    trimestre_id = Column(Integer, ForeignKey("trimestres.id"), nullable=False)
    actividad_id = Column(Integer, ForeignKey("actividades.id"), nullable=False)

    trimestre = relationship("Trimestre", back_populates="clases")
    actividad = relationship("Actividad", back_populates="clases")

    asistencias = relationship("AsistenciaSocio", back_populates="clase", cascade="all, delete-orphan")

# ---------------------------------------------
# ENROLLMENT OF MEMBERS INTO ACTIVITIES
# ---------------------------------------------
class InscripcionSocio(Base):
    __tablename__ = "inscripciones"

    # Composite primary key (socio_id, actividad_id)
    socio_id = Column(Integer, ForeignKey("socios.id"), primary_key=True)
    actividad_id = Column(Integer, ForeignKey("actividades.id"), primary_key=True)

    fecha_inscripcion = Column(Date, nullable=False)
    fecha_baja = Column(Date)
    estado = Column(Enum(EstadoInscripcion), nullable=False)
    observaciones = Column(Text)

    socio = relationship("Socio", back_populates="inscripciones")
    actividad = relationship("Actividad", back_populates="inscripciones")

    matriculas = relationship("Pago", back_populates="inscripcion", cascade="all, delete-orphan")

# ---------------------------------------------
# ATTENDANCE TRACKING
# ---------------------------------------------
class AsistenciaSocio(Base):
    __tablename__ = "asistencias_socio"

    # Composite primary key (socio_id, clase_id)
    socio_id = Column(Integer, ForeignKey("socios.id"), primary_key=True)
    clase_id = Column(Integer, ForeignKey("clases.id"), primary_key=True)

    presente = Column(Boolean, default=False)
    observaciones = Column(Text)

    socio = relationship("Socio", back_populates="asistencias")
    clase = relationship("Clase", back_populates="asistencias")

# ---------------------------------------------
# ENROLLMENT FEE PAYMENTS
# ---------------------------------------------
class Pago(Base):
    __tablename__ = "matricula_pagos"

    id = Column(Integer, primary_key=True)
    socio_id = Column(Integer, nullable=False)
    actividad_id = Column(Integer, nullable=False)
    fecha = Column(Date, nullable=False)
    importe = Column(DECIMAL(10, 2), nullable=False)
    estado = Column(Enum(EstadoPago), nullable=False)
    observaciones = Column(Text)

    # Composite foreign key to InscripcionSocio
    __table_args__ = (
        ForeignKeyConstraint(
            ["socio_id", "actividad_id"],
            ["inscripciones.socio_id", "inscripciones.actividad_id"],
            name="fk_matricula_inscripcion",
            ondelete="CASCADE",
        ),
    )

    inscripcion = relationship("InscripcionSocio", back_populates="matriculas")
