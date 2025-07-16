import os, sys
from stat import *
from exportador.pdf_inscripciones import generar_pdf_inscripciones
from controladores.socios import registrar_socio
from controladores.actividades import registrar_actividad
from controladores.inscripcion_socio import registrar_inscripcion, generar_matricula
from models import EstadoPago
from controladores.personal import registrar_personal
from datetime import date, datetime

def test_generar_pdf_inscripciones(session):
    personalID = registrar_personal(session, {
        'dniNie': '12345678A',
        'nombre': 'Mariano',
        'apellido1': 'Perez'
    }, 'profesor')

    actividadID = registrar_actividad(session, {
        'nombre': 'Piscina',
        'tipo': 'curso',
        'numMaxAlumnos': 9,
        'curso_academico': '2025-2026',
        'personalID': personalID,
        'duracion': 60
    })


    for i in range(10):
        socioID = registrar_socio(session, {
            'dniNie': f'12345678{i:03}',
            'nombre': f'Juan{i}',
            'apellido1': f'Ramiro{i}',
            'telefonoMovil': f'60000000{i}',
            'fechaAlta': datetime(2025, 6, 20-i, 14, 30)
        })


        inscripcion_id = registrar_inscripcion(session, {
            'socioID': socioID,
            'actividadID': actividadID,
            'fechaInscripcion': datetime(2025, 6, 20-i, 14, 30)
        })
        if ( i % 2 == 0):
            generar_matricula(session, inscripcion_id, date(2025, 6, 20-i), EstadoPago.PAGADO)

    output_file = "./informe_inscripciones.pdf"
    generar_pdf_inscripciones(session, actividadID, output_file)

    assert os.stat(output_file).st_size > 0
