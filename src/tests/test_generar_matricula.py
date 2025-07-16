from controladores.inscripcion_socio import (
    registrar_inscripcion,
    generar_matricula,
    consultar_matricula,
    editar_matricula
)
from controladores.actividades import registrar_actividad
from controladores.socios import registrar_socio
from controladores.pagos import consultar_matricula_por_inscripcion
from datetime import date
from models import EstadoPago

def test_crud_matricula(session):
    # Crear socio y actividad
    socioID = registrar_socio(session, {
        'dniNie': 'MAT002',
        'nombre': 'Marc',
        'fechaAlta': date.today()
    })

    actividadID = registrar_actividad(session, {
        'nombre': 'Ioga Avançat',
        'tipo': 'curso',
        'numMaxAlumnos': 5,
        'duracion': 60,
        'precio_matricula': 75.0
    })

    inscripcion_id = registrar_inscripcion(session, {
        'socioID': socioID,
        'actividadID': actividadID,
        'fechaInscripcion': date.today()
    })

    # 1️⃣ Generar matrícula
    matricula_id = generar_matricula(
        session,
        inscripcion_id=inscripcion_id,
        fecha_matricula=date.today(),
        estado=EstadoPago.PENDENT
    )
    assert matricula_id is not None

    # 2️⃣ Intentar duplicar (debe fallar)
    duplicada = generar_matricula(
        session,
        inscripcion_id=inscripcion_id,
        fecha_matricula=date.today(),
        estado=EstadoPago.PENDENT
    )
    assert duplicada is None

    # 3️⃣ Consultar matrícula generada
    matricula = consultar_matricula(session, inscripcion_id)
    assert matricula is not None
    assert matricula.importe == 75.0
    assert matricula.estado == EstadoPago.PENDENT

    # 4️⃣ Editar matrícula
    nuevos_datos = {
        'importe': 85.0,
        'estado': EstadoPago.PAGAT,
        'observaciones': 'Pagada en efectivo'
    }
    result = editar_matricula(session, inscripcion_id, nuevos_datos)
    assert result is True

    # Verificar edición
    matricula_editada = consultar_matricula(session, inscripcion_id)
    assert matricula_editada.importe == 85.0
    assert matricula_editada.estado == EstadoPago.PAGAT
    assert matricula_editada.observaciones == 'Pagada en efectivo'

    # 5️⃣ Eliminar matrícula directamente usando ORM
    session.delete(matricula_editada)
    session.commit()

    # Verificar que ya no existe
    matricula_final = consultar_matricula(session, inscripcion_id)
    assert matricula_final is None