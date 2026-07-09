from ui import curso_academico_preferences as preferencias


class _SettingsFake:
    values = {}

    def __init__(self, *_args):
        pass

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        pass


def test_guarda_y_valida_el_curso_predeterminado(monkeypatch):
    monkeypatch.setattr(preferencias, "QSettings", _SettingsFake)
    _SettingsFake.values = {}
    cursos = [{"id": 4}, {"id": 8}]

    preferencias.establecer_curso_academico_predeterminado(8)

    assert preferencias.obtener_curso_academico_predeterminado(cursos) == 8
    assert preferencias.obtener_curso_academico_predeterminado([{"id": 4}]) is None


def test_borrar_el_curso_predeterminado_limpia_la_preferencia(monkeypatch):
    monkeypatch.setattr(preferencias, "QSettings", _SettingsFake)
    _SettingsFake.values = {}
    preferencias.establecer_curso_academico_predeterminado(8)

    preferencias.establecer_curso_academico_predeterminado(None)

    assert preferencias.obtener_curso_academico_predeterminado() is None
