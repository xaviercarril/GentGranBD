from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph

from exportador.pdf_actividades import (
    PAGE_MARGIN,
    PAGE_SIZE,
    TABLE_COLUMN_WIDTHS,
    _build_activities_table,
    _build_styles,
    generar_pdf_actividades_curso,
)


def test_generar_pdf_actividades_curso(tmp_path):
    output = tmp_path / "activitats.pdf"
    generar_pdf_actividades_curso(
        "2025-2026",
        [
            {
                "nombre": "Anglès",
                "personal_nombre": "Ricardo Vidal",
                "precio_matricula": "20.00 €",
                "inscritos": 12,
                "numMaxAlumnos": 18,
                "descripcion": "Dimecres tarda",
            }
        ],
        str(output),
    )

    assert output.stat().st_size > 0


def test_pdf_actividades_es_apaisado_y_ajusta_textos_largos(tmp_path):
    actividad = {
        "nombre": "Taller de memòria i estimulació cognitiva per a persones grans",
        "personal_nombre": "Montserrat García Fernández de los Ríos",
        "precio_matricula": "120.00 €",
        "inscritos": 28,
        "numMaxAlumnos": 30,
        "descripcion": (
            "Activitat amb una descripció prou llarga per comprovar que el text "
            "es reparteix en diverses línies sense envair les cel·les veïnes."
        ),
    }
    output = tmp_path / "activitats-llargues.pdf"

    generar_pdf_actividades_curso("2025-2026", [actividad], str(output))
    table = _build_activities_table([actividad], _build_styles())

    assert PAGE_SIZE == landscape(A4)
    assert sum(TABLE_COLUMN_WIDTHS) <= PAGE_SIZE[0] - (2 * PAGE_MARGIN)
    assert all(isinstance(cell, Paragraph) for cell in table._cellvalues[1])
    assert table.wrap(sum(TABLE_COLUMN_WIDTHS), 200 * mm)[1] > 12 * mm
    assert output.stat().st_size > 0
