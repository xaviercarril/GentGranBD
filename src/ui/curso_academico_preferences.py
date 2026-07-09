"""Preferencia local del curso académico que se propone en la interfaz."""

from PySide6.QtCore import QSettings


DEFAULT_ACADEMIC_YEAR_KEY = "curso_academico/default_id"


def obtener_curso_academico_predeterminado(cursos: list[dict] | None = None) -> int | None:
    """Devuelve el ID configurado, si sigue estando entre los cursos disponibles."""
    value = QSettings("GentGran", "GentGranBD").value(DEFAULT_ACADEMIC_YEAR_KEY, None)
    try:
        curso_id = int(value)
    except (TypeError, ValueError):
        return None

    if cursos is not None and not any(curso.get("id") == curso_id for curso in cursos):
        return None
    return curso_id


def establecer_curso_academico_predeterminado(curso_id: int | None) -> None:
    """Guarda el curso predeterminado para los selectores de esta aplicación."""
    settings = QSettings("GentGran", "GentGranBD")
    if curso_id is None:
        settings.remove(DEFAULT_ACADEMIC_YEAR_KEY)
    else:
        settings.setValue(DEFAULT_ACADEMIC_YEAR_KEY, int(curso_id))
    settings.sync()
