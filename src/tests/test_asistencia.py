from controladores.actividades import registrar_actividad
from controladores.asistencia import registrar_asistencia
from controladores.fecha import agregar_fecha
from controladores.socios import registrar_socio
from controladores.inscripciones import registrar_inscripcion
from datetime import date

def test_registrar_y_consultar_asistencia(session):
    actividad_id = registrar_actividad(session, {
        'nombre': 'Ioga',
        'tipo': 'curso',
        'numero_maximo_alumnos': 5
    })
    socio_id = registrar_socio(session, {
        'dni_nie': '12345678A',
        'nombre': 'Clara',
        'fecha_alta': date.today()
    })
    insc_id = registrar_inscripcion(session, {
        'socio_id': socio_id,
        'actividad_id': actividad_id,
        'fecha_inscripcion': date.today()
    })
    fecha_id = agregar_fecha(session, actividad_id, date.today(), 'Clase de prueba')

    asistencia_id = registrar_asistencia(
        session,
        {
            "inscripcion_id": insc_id,
            "fecha_id": fecha_id,
            "presente": True,
            "observaciones": "Primera asistencia"
        }
    )

    # Consultar por ID directo
    from controladores.asistencia import consultar_asistencia, modificar_asistencia, eliminar_asistencia, consultar_asistencia_por_inscripcion

    registro = consultar_asistencia(session, asistencia_id)
    assert registro is not None
    assert registro.presente is True
    assert registro.observaciones == "Primera asistencia"

    # Consultar por inscripción
    registros = consultar_asistencia_por_inscripcion(session, insc_id)
    assert len(registros) == 1

    # Modificar asistencia
    modificar_asistencia(session, asistencia_id, {
        'presente': False,
        'observaciones': "No asistió"
    })
    registro_mod = consultar_asistencia(session, asistencia_id)
    assert registro_mod.presente is False
    assert registro_mod.observaciones == "No asistió"

    # Eliminar asistencia
    eliminado = eliminar_asistencia(session, asistencia_id)
    assert eliminado is True
    assert consultar_asistencia(session, asistencia_id) is None
