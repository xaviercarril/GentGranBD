
import tkinter as tk
from tkinter import messagebox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Socio, Base
from datetime import date

# Configuración de la base de datos
engine = create_engine('sqlite:///gentgran.db')
Session = sessionmaker(bind=engine)
session = Session()

# Función para insertar un socio
def insertar_socio():
    nombre = entry_nombre.get()
    dni = entry_dni.get()
    if not nombre or not dni:
        messagebox.showwarning("Campos requeridos", "Nombre y DNI/NIE son obligatorios.")
        return
    socio = Socio(
        nombre=nombre,
        dni_nie=dni,
        fecha_alta=date.today()
    )
    session.add(socio)
    session.commit()
    messagebox.showinfo("Éxito", f"Socio '{nombre}' insertado con ID {socio.id}")
    entry_nombre.delete(0, tk.END)
    entry_dni.delete(0, tk.END)
    listar_socios()

# Función para mostrar los socios
def listar_socios():
    lista.delete(0, tk.END)
    socios = session.query(Socio).all()
    for s in socios:
        lista.insert(tk.END, f"{s.id} - {s.nombre} ({s.dni_nie})")

# Crear ventana
root = tk.Tk()
root.title("Gestión de Socios - Gent Gran")

tk.Label(root, text="Nombre:").grid(row=0, column=0, sticky="e")
entry_nombre = tk.Entry(root, width=30)
entry_nombre.grid(row=0, column=1)

tk.Label(root, text="DNI/NIE:").grid(row=1, column=0, sticky="e")
entry_dni = tk.Entry(root, width=30)
entry_dni.grid(row=1, column=1)

tk.Button(root, text="Insertar socio", command=insertar_socio).grid(row=2, column=0, columnspan=2, pady=10)

tk.Label(root, text="Lista de socios:").grid(row=3, column=0, columnspan=2)

lista = tk.Listbox(root, width=50)
lista.grid(row=4, column=0, columnspan=2)

listar_socios()

root.mainloop()
