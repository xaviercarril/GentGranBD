import os
from exportador.pdf_asistencias import generar_pdf_parrilla_asistencias
from controladores.actividades import registrar_actividad
from controladores.inscripcion_socio import registrar_inscripcion
from controladores.socios import registrar_socio
from controladores.asistencia_socio import registrar_asistencia
from controladores.clase import agregar_fecha
from controladores.personal import registrar_personal
from datetime import date, timedelta

def test_generar_pdf_parrilla_asistencias(tmp_path, session):
    # Crear actividad
    personalID = registrar_personal(session, {
        'nombre': 'Manolo',
        'dniNie': '12345678A',
        'apellido1': 'Gómez',
        'apellido2': 'Rodríguez'
    }, 'profesor')

    actividadID = registrar_actividad(session, {
        'nombre': 'Català Bàsic',
        'tipo': 'curso',
        'numMaxAlumnos': 15,
        'duracion': 60,
        'lugar': 'Centre Municipal Frederic Mompou',
        'precio_matricula': 0.0,
        'descripcion_fecha': 'DIMARTS de 18:00 a 19:00',
        'curso_academico': '25-26',
        'observaciones': 'Curso de iniciación al catalán',
        'personalID': personalID
    })

    # Crear 10 socios e inscribirlos
    inscripciones = []
    for i in range(1, 21):
        socioID = registrar_socio(session, {
            'dniNie': f'PARR{i:03}',
            'nombre': f'Soci_{i}',
            'fechaAlta': date.today()
        })
        insc_id = registrar_inscripcion(session, {
            'socioID': socioID,
            'actividadID': actividadID,
            'fechaInscripcion': date.today()
        })
        inscripciones.append(insc_id)

    # Crear 15 fechas (5 por mes durante 3 meses consecutivos)
    fechas_ids = []
    for offset in range(0, 35):
        # Espaciado semanal, abarca aprox. tres meses
        fecha_id = agregar_fecha(
            session,
            actividadID,
            date.today() + timedelta(days=offset * 7)
        )
        fechas_ids.append(fecha_id)

    # Registrar asistencias: assegurem que hi hagi tant presents com absents
    for insc_index, insc_id in enumerate(inscripciones):
        for idx_fecha, fecha_id in enumerate(fechas_ids):
            # Farem present cada tercera sessió per cada soci
            presente = (idx_fecha % 3 == 0)
            registrar_asistencia(session, {
                'inscripcion_id': insc_id,
                'fecha_id': fecha_id,
                'presente': presente
            })

    # Generar PDF en carpeta temporal
    output_file = "./parrilla_asistencias.pdf"
    generar_pdf_parrilla_asistencias(session, actividadID, str(output_file))

    assert os.stat(output_file).st_size > 0
