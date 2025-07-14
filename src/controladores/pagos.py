
from sqlalchemy.orm import Session
from models import MatriculaPago
from datetime import date

def registrar_pago(session: Session, datos: dict):
    print(f"Registrando pago: {datos}")
    pago = MatriculaPago(
        socio_id=datos['socio_id'],
        actividad_id=datos['actividad_id'],
        fecha=datos.get('fecha', date.today()),
        importe=datos.get('importe', 0),
        estado=datos['estado'],
        observaciones=datos.get('observaciones'),
    )

    session.add(pago)
    session.commit()
    return pago.id

def modificar_pago(session: Session, pago_id: int, nuevos_datos: dict):
    pago = session.query(MatriculaPago).filter(MatriculaPago.id == pago_id).first()
    if not pago:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(pago, clave, valor)
    session.commit()
    return True

def consultar_pagos_por_inscripcion(session: Session, socio_id: int, actividad_id: int):
    return session.query(MatriculaPago).filter(
        MatriculaPago.socio_id == socio_id,
        MatriculaPago.actividad_id == actividad_id,
    ).all()

def consultar_matricula_por_inscripcion(session: Session, socio_id: int, actividad_id: int):
    return session.query(MatriculaPago).filter(
        MatriculaPago.socio_id == socio_id,
        MatriculaPago.actividad_id == actividad_id,
    ).first()

def consultar_pago(session: Session, pago_id: int):
    return session.query(MatriculaPago).filter(MatriculaPago.id == pago_id).first()

def eliminar_pago(session: Session, pago_id: int):
    pago = session.query(MatriculaPago).filter(MatriculaPago.id == pago_id).first()
    if not pago:
        return False
    session.delete(pago)
    session.commit()
    return True
