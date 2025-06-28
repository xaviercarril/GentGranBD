
from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.inscripciones import registrar_inscripcion
from controladores.asistencia import registrar_asistencia
from controladores.informes import generar_informe_asistencia_trimestral
from datetime import date

def test_informe_asistencia_trimestral(session):
    actividad_id = registrar_actividad(session, {'nombre': 'Teatre', 'tipo': 'curso', 'numero_maximo_alumnos': 5})
    socio_id = registrar_socio(session, {'dni_nie': 'T001', 'nombre': 'Teresa', 'fecha_alta': date(2024,1,1)})
    insc_id = registrar_inscripcion(session, {'socio_id': socio_id, 'actividad_id': actividad_id, 'fecha_inscripcion': date(2024,1,5)})

    registrar_asistencia(session, {'inscripcion_id': insc_id, 'fecha': date(2024, 2, 15), 'presente': True})
    registrar_asistencia(session, {'inscripcion_id': insc_id, 'fecha': date(2024, 3, 10), 'presente': False})

    informe = generar_informe_asistencia_trimestral(session, actividad_id, 2024)
    assert 'Q1' in informe
    assert len(informe['Q1']) == 2
