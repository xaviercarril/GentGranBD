from controladores.actividades import (
    registrar_actividad,
    modificar_actividad,
    eliminar_actividad,
    consultar_actividad,
)
from controladores.trimestre import registrar_trimestre
from datetime import date
from models import Curso, Taller, Trimestre, TrimestreEnum

def test_crud_curso_con_trimestres(session):
    # Registrar un curso
    curso_id = registrar_actividad({
        'nombre': 'Anglès Inicial',
        'tipo': 'curso',
        'numero_maximo_alumnos': 12,
        'lugar': 'Aula 2',
        'curso_academico': '2025-2026',
        'precio_matricula': 25.0,
        'descripcion_fecha': 'Dimarts i Dijous'
    })

    curso = session.query(Curso).filter_by(id=curso_id).first()
    assert curso is not None
    assert curso.nombre == 'Anglès Inicial'

    # Crear trimestres asociados al curso
    trimestre1_id = registrar_trimestre({
        'nombre': TrimestreEnum.T1,
        'fecha_inicio': date(2025, 1, 1),
        'fecha_fin': date(2025, 3, 31),
        'cursoA_id': curso_id
    })

    trimestre2_id = registrar_trimestre({
        'nombre': TrimestreEnum.T2,
        'fecha_inicio': date(2025, 4, 1),
        'fecha_fin': date(2025, 6, 30),
        'cursoA_id': curso_id
    })

    # Verificar que se asocian correctamente
    curso = session.get(Curso,curso_id)
    assert len(curso.trimestres) == 2
    nombres = [t.nombre for t in curso.trimestres]
    assert TrimestreEnum.T1 in nombres
    assert TrimestreEnum.T2 in nombres

    # Modificar
    modificar_actividad(curso_id, {'numero_maximo_alumnos': 15})
    curso = session.get(Curso,curso_id)
    assert curso.numero_maximo_alumnos == 15

    # Eliminar curso (cascade)
    eliminado = eliminar_actividad(curso_id)
    assert eliminado is True
    assert consultar_actividad(curso_id) is None

def test_crud_taller(session):
    taller_id = registrar_actividad({
        'nombre': 'Ceràmica Creativa',
        'tipo': 'taller',
        'numero_maximo_alumnos': 8,
        'lugar': 'Aula Manualitats',
        'duracion': 90,
        'precio_matricula': 12.0
    })

    taller = session.query(Taller).filter_by(id=taller_id).first()
    assert taller is not None
    assert taller.nombre == 'Ceràmica Creativa'

    modificar_actividad(taller_id, {'numero_maximo_alumnos': 10})
    taller = session.get(Taller,taller_id)
    assert taller.numero_maximo_alumnos == 10

    eliminado = eliminar_actividad(taller_id)
    assert eliminado is True
    assert consultar_actividad(taller_id) is None

def test_crear_trimestre_unit(session):
    # Test directo crear trimestre aislado (solo para verificar FK)
    curso_id = registrar_actividad({
        'nombre': 'Francès Bàsic',
        'tipo': 'curso'
    })

    trimestre_id = registrar_trimestre({
        'nombre': TrimestreEnum.T3,
        'fecha_inicio': date(2025, 7, 1),
        'fecha_fin': date(2025, 9, 30),
        'cursoA_id': curso_id
    })

    trimestre = session.get(Trimestre,trimestre_id)
    assert trimestre is not None
    assert trimestre.nombre == TrimestreEnum.T3
    assert trimestre.curso_id == curso_id