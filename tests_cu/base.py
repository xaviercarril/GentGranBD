import unittest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ensure src is on the path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models import Base
import controladores.socios as socios
import controladores.actividades as actividades
import controladores.clase as clase
import controladores.curso_academico as curso_academico

class ControllerTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()
        # patch controllers to use in-memory SessionLocal
        socios.SessionLocal = self.SessionLocal
        actividades.SessionLocal = self.SessionLocal
        clase.SessionLocal = self.SessionLocal
        curso_academico.SessionLocal = self.SessionLocal

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
