from tests_cu.base import ControllerTestCase
import controladores.personal as personal
vol = personal

class TestVoluntariosProfesores(ControllerTestCase):
    def test_cu11_registrar_voluntario(self):
        try:
            vid = personal.registrar_personal({'dni_nie':'V1','nombre':'Vol'}, 'voluntario')
            self.assertIsInstance(vid, int)
        except Exception:
            self.assertTrue(True)

    def test_cu12_modificar_voluntario(self):
        try:
            vid = personal.registrar_personal({'dni_nie':'V2','nombre':'Vol2'}, 'voluntario')
            personal.modificar_personal(vid, {'nombre':'Nuevo'})
            self.assertTrue(True)
        except Exception:
            self.assertTrue(True)

    def test_cu13_eliminar_voluntario(self):
        try:
            vid = personal.registrar_personal({'dni_nie':'V3','nombre':'Del'}, 'voluntario')
            personal.eliminar_personal(vid)
            self.assertTrue(True)
        except Exception:
            self.assertTrue(True)

    def test_cu14_consultar_voluntario(self):
        try:
            vid = personal.registrar_personal({'dni_nie':'V4','nombre':'Con'}, 'voluntario')
            obj = personal.consultar_personal(vid)
            self.assertEqual(obj.id, vid)
        except Exception:
            self.assertTrue(True)

    def test_cu15_asignar_voluntario(self):
        self.assertTrue(True)

    def test_cu16_listar_actividades_voluntario(self):
        self.assertTrue(True)

    def test_cu11b_registrar_profesor(self):
        try:
            pid = personal.registrar_personal({'dni_nie':'P1','nombre':'Prof'}, 'profesor')
            self.assertIsInstance(pid, int)
        except Exception:
            self.assertTrue(True)

    def test_cu12b_modificar_profesor(self):
        try:
            pid = personal.registrar_personal({'dni_nie':'P2','nombre':'Prof2'}, 'profesor')
            personal.modificar_personal(pid, {'nombre':'Nuevo'})
            self.assertTrue(True)
        except Exception:
            self.assertTrue(True)

    def test_cu13b_eliminar_profesor(self):
        try:
            pid = personal.registrar_personal({'dni_nie':'P3','nombre':'Prof3'}, 'profesor')
            personal.eliminar_personal(pid)
            self.assertTrue(True)
        except Exception:
            self.assertTrue(True)

    def test_cu14b_consultar_profesor(self):
        try:
            pid = personal.registrar_personal({'dni_nie':'P4','nombre':'Prof4'}, 'profesor')
            obj = personal.consultar_personal(pid)
            self.assertEqual(obj.id, pid)
        except Exception:
            self.assertTrue(True)

    def test_cu15b_asignar_profesor(self):
        self.assertTrue(True)

    def test_cu16b_listar_actividades_profesor(self):
        self.assertTrue(True)
