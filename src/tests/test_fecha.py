from controladores.clase import (
    generar_fechas,
    generar_fechas_custom,
    agregar_fecha,
    eliminar_fecha,
    consultar_fechas
)
from controladores.actividades import registrar_actividad
from datetime import date

def test_crud_fechas(session):
    # Crear actividad de prueba
    actividadID = registrar_actividad(session, {
        'nombre': 'Català',
        'tipo': 'curso',
        'numMaxAlumnos': 10
    })

    # Probar agregar_fecha
    fecha_id = agregar_fecha(session, actividadID, date(2025, 4, 10), "Primera fecha manual")
    fechas = consultar_fechas(session, actividadID)
    assert len(fechas) == 1
    assert fechas[0].fecha == date(2025, 4, 10)

    # Probar generar_fechas (lunes y miércoles, cada semana)
    generar_fechas(
        session,
        actividadID,
        fechaInicio=date(2025, 4, 1),
        fechaFin=date(2025, 4, 30),
        dias_semana=[0, 2],  # Lunes y miércoles
        cada_n_semanas=1
    )
    fechas = consultar_fechas(session, actividadID)
    assert len(fechas) >= 5  # Al menos las generadas + manual

    # Probar generar_fechas_custom
    generar_fechas_custom(session, actividadID, [date(2025, 5, 15), date(2025, 5, 20)])
    fechas = consultar_fechas(session, actividadID)
    assert any(f.fecha == date(2025, 5, 15) for f in fechas)

    # Probar eliminar_fecha
    deleted = eliminar_fecha(session, fecha_id)
    assert deleted is True
    fechas = consultar_fechas(session, actividadID)
    assert all(f.fecha != date(2025, 4, 10) for f in fechas)