from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean, Text, DECIMAL,
    ForeignKey, LargeBinary, Enum, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, column_property
import enum

Base = declarative_base()

class Trimestre(enum.Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"

class EstadoInscripcion(enum.Enum):
    INSCRIT = "INSCRIT"
    RESERVA = "RESERVA"

class EstadoPago(enum.Enum):
    PENDENT = "PENDENT"
    PAGAT = "PAGAT"
    ANULADO = "ANUL·LAT"

class Socio(Base):
    __tablename__ = 'socios'

    id = Column(Integer, primary_key=True)
    dni_nie = Column(String(15), unique=True, nullable=False)
    nombre = Column(String(50), nullable=False)
    apellido1 = Column(String(50))
    apellido2 = Column(String(50))
    direccion = Column(String(255))
    telefonoFijo = Column(String(20))
    telefonoMovil = Column(String(20))
    email = Column(String(100))
    grupoDifusion = Column(String(50))
    fechaAlta = Column(Date, nullable=False)
    fechaBaja = Column(Date)
    observaciones = Column(Text)
    foto = Column(LargeBinary)

    inscripciones = relationship("InscripcionSocio", back_populates="socio")


class Personal(Base):
    __tablename__ = 'personal'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    apellido1 = Column(String(50))
    apellido2 = Column(String(50))
    dni_nie = Column(String(15), unique=True, nullable=False)
    tipo = Column(String(50))

    actividades = relationship("Actividad", back_populates="personal")

    __mapper_args__ = {
        'polymorphic_identity': 'personal',
        'polymorphic_on': tipo
    }

class Voluntario(Personal):
    __mapper_args__ = {
        'polymorphic_identity': 'voluntario'
    }

class Profesor(Personal):
    __mapper_args__ = {
        'polymorphic_identity': 'profesor'
    }

class Actividad(Base):
    __tablename__ = 'actividades'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    numero_maximo_alumnos = Column(Integer)
    duracion = Column(Integer)  # Duración en minutos
    tipo = Column(String(50))
    lugar = Column(String(100))
    precio_matricula = Column(DECIMAL(10, 2), default=0.0)
    observaciones = Column(Text)
    personal_id = Column(Integer, ForeignKey('personal.id'))

    personal = relationship("Personal", back_populates="actividades")
    inscripciones = relationship("InscripcionSocio", back_populates="actividad")

    __mapper_args__ = {
        'polymorphic_identity': 'actividad',
        'polymorphic_on': tipo
    }

class Curso(Actividad):
    trimestre = Column(Enum(Trimestre))
    dias_semana = Column(String(50))
    curso = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity': 'curso'
    }

class Taller(Actividad):
    fecha = Column(Date)
    hora_inicio = Column(DateTime)

    __mapper_args__ = {
        'polymorphic_identity': 'taller'
    }

class InscripcionSocio(Base):
    __tablename__ = 'inscripciones'

    id = Column(Integer, primary_key=True)
    socio_id = Column(Integer, ForeignKey('socios.id'), nullable=False)
    actividad_id = Column(Integer, ForeignKey('actividades.id'), nullable=False)
    fecha_inscripcion = Column(Date, nullable=False)
    estado = Column(Enum(EstadoInscripcion), nullable=False)
    observaciones = Column(Text)

    fecha_baja = Column(Date)

    __table_args__ = (
        UniqueConstraint('socio_id', 'actividad_id', name='uq_socio_actividad'),
    )

    socio = relationship("Socio", back_populates="inscripciones")
    actividad = relationship("Actividad", back_populates="inscripciones")
    asistencias = relationship("Asistencia", back_populates="inscripcion")
    mensualidades = relationship("mensualidadPago", back_populates="inscripcion")
    matricula = relationship("matriculaPago", back_populates="inscripcion", uselist=False, foreign_keys="[matriculaPago.inscripcion_id]")

class Asistencia(Base):
    __tablename__ = 'asistencias'

    id = Column(Integer, primary_key=True)
    inscripcion_id = Column(Integer, ForeignKey('inscripciones.id'))
    fecha = Column(Date)
    presente = Column(Boolean)
    observaciones = Column(Text)

    inscripcion = relationship("InscripcionSocio", back_populates="asistencias")

class Pago(Base):
    __tablename__ = 'pagos'

    id = Column(Integer, primary_key=True)
    inscripcion_id = Column(Integer, ForeignKey('inscripciones.id'))
    fecha = Column(Date)
    importe = Column(DECIMAL(10, 2))
    estado = Column(Enum(EstadoPago), nullable=False)
    observaciones = Column(Text)
    tipo = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity': 'pagos',
        'polymorphic_on': tipo
    }

class matriculaPago(Pago):
    __tablename__ = 'matricula_pagos'

    id = Column(Integer, ForeignKey('pagos.id'), primary_key=True)

    inscripcion = relationship("InscripcionSocio", back_populates="matricula", foreign_keys="[Pago.inscripcion_id]")

    __mapper_args__ = {
         'polymorphic_identity': 'matricula',
    }

class mensualidadPago(Pago):
    __tablename__ = 'mensualidad_pagos'
    id = Column(Integer, ForeignKey('pagos.id'), primary_key=True)  # Establish FK relationship
    inscripcion = relationship("InscripcionSocio", back_populates="mensualidades")
    __mapper_args__ = {
        'polymorphic_identity': 'mensualidades'
    }