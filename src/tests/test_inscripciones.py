
from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.inscripciones import registrar_inscripcion
from datetime import date
from models import EstadoInscripcion

def test_registrar_inscripcion_con_estado(session):
    act_id = registrar_actividad(session, {'nombre': 'Gimnasia', 'tipo': 'taller', 'numero_maximo_alumnos': 1})
    socio1 = registrar_socio(session, {
        'dni_nie': 'X001', 'nombre': 'Laura', 'fecha_alta': date.today()
    })
    socio2 = registrar_socio(session, {
        'dni_nie': 'X002', 'nombre': 'Joan', 'fecha_alta': date.today()
    })

    ins1 = registrar_inscripcion(session, {
        'socio_id': socio1, 'actividad_id': act_id, 'fecha_inscripcion': date.today()
    })
    ins2 = registrar_inscripcion(session, {
        'socio_id': socio2, 'actividad_id': act_id, 'fecha_inscripcion': date.today()
    })

    from models import InscripcionSocio
    i1 = session.get(InscripcionSocio, ins1)
    i2 = session.get(InscripcionSocio, ins2)

    assert i1.estado == EstadoInscripcion.INSCRITO
    assert i2.estado == EstadoInscripcion.RESERVA
    assert i1.posicion == 1
    assert i2.posicion == 2
