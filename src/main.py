
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Socio
from datetime import date

# Conectar a la base de datos SQLite
engine = create_engine('sqlite:///gentgran.db')
Session = sessionmaker(bind=engine)
session = Session()

# Crear un nuevo socio
nuevo_socio = Socio(
    dni_nie="12345678A",
    nombre="Joan",
    apellido1="Garcia",
    apellido2="Martí",
    direccion="Carrer Major 12",
    telefono_fijo="933445566",
    telefono_movil="600112233",
    email="joan@example.com",
    grupo_difusion="General",
    fecha_alta=date.today(),
    observaciones="Nuevo socio inscrit al gener"
)

# Insertar en la base de datos
session.add(nuevo_socio)
session.commit()
print("Socio insertado con ID:", nuevo_socio.id)

# Consultar todos los socios
print("\nLista de socios:")
for socio in session.query(Socio).all():
    print(f"{socio.id}: {socio.nombre} {socio.apellido1} ({socio.dni_nie})")
