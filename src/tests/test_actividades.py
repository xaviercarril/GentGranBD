
from controladores.actividades import registrar_actividad, consultar_actividad

def test_registrar_curso(session):
    datos = {'nombre': 'Informàtica', 'tipo': 'curso', 'numero_maximo_alumnos': 2}
    actividad_id = registrar_actividad(session, datos)
    actividad = consultar_actividad(session, actividad_id)
    assert actividad is not None
    assert actividad.tipo == 'curso'
