
from sqlalchemy.orm import Session
from models import InscripcionSocio, Actividad, EstadoInscripcion, MatriculaPago, EstadoPago
from controladores.pagos import registrar_pago
from sqlalchemy.exc import IntegrityError
from datetime import date

def actualizar_estado_inscripciones(session: Session, actividad_id: int):
    actividad = session.query(Actividad).filter_by(id=actividad_id).first()
    if not actividad:
        print("Actividad no encontrada.")
        return False

    inscripciones = session.query(InscripcionSocio).filter_by(actividad_id=actividad.id).order_by(InscripcionSocio.fecha_inscripcion).all()

    for i, inscripcion in enumerate(inscripciones, start=1):
        if actividad.numero_maximo_alumnos is not None and i > actividad.numero_maximo_alumnos:
            inscripcion.estado = EstadoInscripcion.RESERVA
        else:
            inscripcion.estado = EstadoInscripcion.INSCRIT
        session.add(inscripcion)

    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False
    
def registrar_inscripcion(session: Session, datos: dict):
    actividad = session.query(Actividad).filter_by(id=datos['actividad_id']).first()
    if not actividad:
        print("Actividad no encontrada.")
        return None
    

    inscripcion = InscripcionSocio(
        socio_id=datos['socio_id'],
        actividad_id=datos['actividad_id'],
        fecha_inscripcion=datos['fecha_inscripcion'],
        estado=EstadoInscripcion.RESERVA,
        observaciones=datos.get('observaciones'),
        fecha_baja=datos.get('fecha_baja')
    )

    session.add(inscripcion)
    session.commit()
    actualizar_estado_inscripciones(session, actividad.id)
    return {'socio_id': inscripcion.socio_id, 'actividad_id': inscripcion.actividad_id}

def eliminar_inscripcion(session: Session, socio_id: int, actividad_id: int):
    inscripcion = session.get(InscripcionSocio, {'socio_id': socio_id, 'actividad_id': actividad_id})
    if not inscripcion:
        return False
    session.delete(inscripcion)
    session.commit()
    return True

def consultar_inscripcion(session: Session, socio_id: int, actividad_id: int):
    return session.get(InscripcionSocio, {'socio_id': socio_id, 'actividad_id': actividad_id})

def consultar_actividad(session: Session, actividad_id: int):
    return session.query(Actividad).filter(Actividad.id == actividad_id).first()

def generar_matricula(session: Session, socio_id: int, actividad_id: int, fecha_matricula: date, estado: EstadoPago):
    inscripcion = session.get(InscripcionSocio, {'socio_id': socio_id, 'actividad_id': actividad_id})
    actividad = session.get(Actividad, actividad_id)
    if not inscripcion:
        print("Inscripción no encontrada.")
        return None
    if consultar_matricula(session, socio_id, actividad_id):
        print("Ya existe una matrícula para esta inscripción.")
        return None

    print(f"Generando matrícula para la inscripción socio:{socio_id} act:{actividad_id}, fecha: {fecha_matricula}, estado: {estado.value}")
    # Registrar el pago de matrícula
    matricula_id = registrar_pago(session, {
        'socio_id': socio_id,
        'actividad_id': actividad_id,
        'fecha': fecha_matricula,
        'importe': actividad.precio_matricula,
        'estado': estado
    }, tipo='matricula')
    
    return matricula_id

def consultar_matricula(session: Session, socio_id: int, actividad_id: int):
    return session.query(MatriculaPago).filter(
        MatriculaPago.socio_id == socio_id,
        MatriculaPago.actividad_id == actividad_id
    ).first()

def editar_matricula(session: Session, socio_id: int, actividad_id: int, nuevos_datos: dict):
    matricula = session.query(MatriculaPago).filter(
        MatriculaPago.socio_id == socio_id,
        MatriculaPago.actividad_id == actividad_id
    ).first()
    if not matricula:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(matricula, clave, valor)
    session.commit()
    return True