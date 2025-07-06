
from sqlalchemy.orm import Session
from models import Pago, matriculaPago, mensualidadPago
from datetime import date

def registrar_pago(session: Session, datos: dict, tipo: str):
    clase =  matriculaPago if (tipo == 'matricula') else mensualidadPago

    print(f"Registrando pago: {datos}, fecha: {datos.get('fecha')}, tipo: {tipo}")
    pago = clase(
        inscripcion_id=datos['inscripcion_id'],
        fecha=datos.get('fecha'),
        importe=datos.get('importe', 0),
        estado=datos['estado'],
        observaciones=datos.get('observaciones'),
        tipo=tipo
    )

    session.add(pago)
    session.commit()
    return pago.id

def modificar_pago(session: Session, pago_id: int, nuevos_datos: dict):
    pago = session.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(pago, clave, valor)
    session.commit()
    return True

def consultar_pagos_por_inscripcion(session: Session, inscripcion_id: int):
    return session.query(Pago).filter(Pago.inscripcion_id == inscripcion_id).all()

def consultar_matricula_por_inscripcion(session: Session, inscripcion_id: int):
    return session.query(matriculaPago).filter(matriculaPago.inscripcion_id == inscripcion_id).first()

def consultar_pago(session: Session, pago_id: int):
    return session.query(Pago).filter(Pago.id == pago_id).first()

def eliminar_pago(session: Session, pago_id: int):
    pago = session.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        return False
    session.delete(pago)
    session.commit()
    return True
