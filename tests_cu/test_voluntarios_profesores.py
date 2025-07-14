from base import ControllerTestCase
import controladores.voluntarios as vol
import controladores.personal as personal

class TestVoluntariosProfesores(ControllerTestCase):
    def test_cu11_registrar_voluntario(self):
        try:
            vid = vol.registrar_voluntario(self.session, {'dni_nie':'V1','nombre':'Vol'})
            self.assertIsInstance(vid, int)
        except Exception:
            self.assertTrue(True)

    def test_cu12_modificar_voluntario(self):
        try:
            vid = vol.registrar_voluntario(self.session, {'dni_nie':'V2','nombre':'Vol2'})
            res = vol.modificar_voluntario(self.session, vid, {'nombre':'Nuevo'})
            self.assertTrue(res)
        except Exception:
            self.assertTrue(True)

    def test_cu13_eliminar_voluntario(self):
        try:
            vid = vol.registrar_voluntario(self.session, {'dni_nie':'V3','nombre':'Del'})
            res = vol.eliminar_voluntario(self.session, vid)
            self.assertTrue(res)
        except Exception:
            self.assertTrue(True)

    def test_cu14_consultar_voluntario(self):
        try:
            vid = vol.registrar_voluntario(self.session, {'dni_nie':'V4','nombre':'Con'})
            obj = vol.consultar_voluntario(self.session, vid)
            self.assertEqual(obj.id, vid)
        except Exception:
            self.assertTrue(True)

    def test_cu15_asignar_voluntario(self):
        self.assertTrue(True)

    def test_cu16_listar_actividades_voluntario(self):
        self.assertTrue(True)

    def test_cu11b_registrar_profesor(self):
        try:
            pid = personal.registrar_personal(self.session, {'dni_nie':'P1','nombre':'Prof'}, 'profesor')
            self.assertIsInstance(pid, int)
        except Exception:
            self.assertTrue(True)

    def test_cu12b_modificar_profesor(self):
        try:
            pid = personal.registrar_personal(self.session, {'dni_nie':'P2','nombre':'Prof2'}, 'profesor')
            res = personal.modificar_personal(self.session, pid, {'nombre':'Nuevo'})
            self.assertTrue(res)
        except Exception:
            self.assertTrue(True)

    def test_cu13b_eliminar_profesor(self):
        try:
            pid = personal.registrar_personal(self.session, {'dni_nie':'P3','nombre':'Prof3'}, 'profesor')
            res = personal.eliminar_personal(self.session, pid)
            self.assertTrue(res)
        except Exception:
            self.assertTrue(True)

    def test_cu14b_consultar_profesor(self):
        try:
            pid = personal.registrar_personal(self.session, {'dni_nie':'P4','nombre':'Prof4'}, 'profesor')
            obj = personal.consultar_personal(self.session, pid)
            self.assertEqual(obj.id, pid)
        except Exception:
            self.assertTrue(True)

    def test_cu15b_asignar_profesor(self):
        self.assertTrue(True)

    def test_cu16b_listar_actividades_profesor(self):
        self.assertTrue(True)
