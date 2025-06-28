
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Ruta de la base de datos SQLite (archivo local)
DATABASE_URL = 'sqlite:///gentgran.db'

# Crear el motor de conexión
engine = create_engine(DATABASE_URL, echo=False)

# Crear clase de sesión
SessionLocal = sessionmaker(bind=engine)

# Crear todas las tablas si no existen
def init_db():
    Base.metadata.create_all(bind=engine)

# Obtener una sesión nueva
def get_session():
    return SessionLocal()
