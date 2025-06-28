
from controladores.pagos import registrar_pago, consultar_pagos_por_inscripcion
from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.inscripciones import registrar_inscripcion
from datetime import date
from models import EstadoPago

def test_registrar_matricula_y_mensualidad(session):
    act_id = registrar_actividad(session, {
        'nombre': 'Dansa',
        'tipo': 'curso',
        'numero_maximo_alumnos': 1,
        'duracion': 60
    })
    socio_id = registrar_socio(session, {
        'dni_nie': 'P00123X',
        'nombre': 'Meritxell',
        'fecha_alta': date.today()
    })
    insc_id = registrar_inscripcion(session, {
        'socio_id': socio_id,
        'actividad_id': act_id,
        'fecha_inscripcion': date.today()
    })

    registrar_pago(session, {
        'inscripcion_id': insc_id,
        'fecha': date.today(),
        'importe': 30.0,
        'estado': EstadoPago.PAGAT,
        'tipo': 'matriculaPago'
    })

    registrar_pago(session, {
        'inscripcion_id': insc_id,
        'fecha': date.today(),
        'importe': 15.0,
        'estado': EstadoPago.PAGAT,
        'tipo': 'mensualidadPago'
    })

    pagos = consultar_pagos_por_inscripcion(session, insc_id)
    tipos = [p.tipo for p in pagos]

    assert len(pagos) == 2
    assert 'matriculaPago' in tipos
    assert 'mensualidadPago' in tipos
