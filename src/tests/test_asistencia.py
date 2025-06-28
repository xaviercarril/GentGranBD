
from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.inscripciones import registrar_inscripcion
from controladores.asistencia import registrar_asistencia, consultar_asistencia
from datetime import date

def test_registrar_y_consultar_asistencia(session):
    actividad_id = registrar_actividad(session, {'nombre': 'Ioga', 'tipo': 'curso', 'numero_maximo_alumnos': 5})
    socio_id = registrar_socio(session, {'dni_nie': '12345678A', 'nombre': 'Clara', 'fecha_alta': date.today()})
    insc_id = registrar_inscripcion(session, {'socio_id': socio_id, 'actividad_id': actividad_id, 'fecha_inscripcion': date.today()})

    asistencia_id = registrar_asistencia(session, {
        'inscripcion_id': insc_id, 'fecha': date.today(), 'presente': True
    })
    registros = consultar_asistencia(session, insc_id)
    assert len(registros) == 1
    assert registros[0].presente is True
