
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ruta de la base de datos SQLite (archivo local)
DATABASE_URL = 'sqlite:///gentgran.db'

# Crear el motor de conexión
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Crear clase de sesión
SessionLocal = sessionmaker(bind=engine, 
                            autoflush=False,
                            autocommit=False,
                            expire_on_commit=False)