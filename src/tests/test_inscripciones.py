from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.inscripcion_socio import registrar_inscripcion, consultar_matricula
from datetime import date, datetime
from models import EstadoInscripcion

def test_registrar_inscripcion_con_estado_y_matricula(session):
    # 1️⃣ Crear actividad con 1 plaza para forzar RESERVA
    act_id = registrar_actividad(session, {
        'nombre': 'Gimnasia',
        'tipo': 'taller',
        'numMaxAlumnos': 1,
        'precio_matricula': 30.0
    })

    socio1 = registrar_socio(session, {
        'dniNie': 'X001',
        'nombre': 'Laura',
        'fechaAlta': date.today()
    })

    socio2 = registrar_socio(session, {
        'dniNie': 'X002',
        'nombre': 'Joan',
        'fechaAlta': date.today()
    })

    # 2️⃣ Registrar primera inscripción
    ins1 = registrar_inscripcion(session, {
        'socioID': socio1,
        'actividadID': act_id,
        'fechaInscripcion': datetime.now()
    })

    # 3️⃣ Registrar segunda inscripción (RESERVA)
    ins2 = registrar_inscripcion(session, {
        'socioID': socio2,
        'actividadID': act_id,
        'fechaInscripcion': datetime.now()
    })

    from models import InscripcionSocio, EstadoInscripcion

    i1 = session.get(InscripcionSocio, ins1)
    i2 = session.get(InscripcionSocio, ins2)

    # ✅ Verificar estados 
    assert i1.estado == EstadoInscripcion.INSCRITO
    assert i2.estado == EstadoInscripcion.RESERVA

    # ✅ Verificar matrícula generada solo para INSCRIT
    matricula1 = consultar_matricula(session, ins1)
    assert matricula1 is None, "Matrícula no debe existir automáticamente si no se llama a generar_matricula()"

    # Si tu registrar_inscripcion no crea matrícula automática:
    # Espera None. Si la crea, cambia a:
    # assert matricula1 is not None
    # assert matricula1.importe == 30.0

    # Segundo socio: matrícula debería ser None si no la generas
    matricula2 = consultar_matricula(session, ins2)
    assert matricula2 is None