
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from models import Actividad, InscripcionSocio, Socio, Pago
from controladores.inscripcion_socio import consultar_matricula
from sqlalchemy.orm import Session

def generar_pdf_inscripciones(session: Session, actividad_id: int, ruta_pdf: str):
    actividad = session.query(Actividad).filter_by(id=actividad_id).first()
    if not actividad:
        raise ValueError("Actividad no encontrada")

    inscripciones = session.query(InscripcionSocio).filter_by(actividad_id=actividad_id).order_by(InscripcionSocio.fecha_inscripcion).all()

    c = canvas.Canvas(ruta_pdf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    if actividad.curso_academico is not None:
        c.drawString(20*mm, height - 20*mm, f"Inscripcions - {actividad.nombre} (Curso {actividad.curso_academico})")
    else:
        c.drawString(20*mm, height - 20*mm, f"Inscripcions - {actividad.nombre}")
    c.drawString(20*mm, height - 27*mm, f"Profesor: {actividad.personal.nombre} {actividad.personal.apellido1}" if actividad.personal else 'No asignado')
    c.drawString(20*mm, height - 34*mm, f"Máxim Num. Alumnes: {actividad.numero_maximo_alumnos or 'Sense Límit'}")

    c.setFont("Helvetica-Bold", 10)
    encabezado = ["#", "Nombre y Apellidos", "Telefono", "Fecha", "Estado", "Matricula", "Fecha Matricula"]
    x_header = 20 * mm
    for i, texto in enumerate(encabezado):
        c.drawString(x_header, height - 41*mm, texto)
        if i == 0:
            x_header += 10 * mm  # Ajuste para el nombre
        elif i == 1:
            x_header += 40 * mm
        else:
            x_header += 25 * mm
    
    c.setFont("Helvetica", 10)

    y = height - 48*mm
    for i, inscripcion in enumerate(inscripciones, start=1):
        socio = inscripcion.socio
        matricula = consultar_matricula(session, inscripcion.id)
        fila = [
            str(i),
            f"{socio.nombre} {socio.apellido1 or ''}",
            socio.telefonoMovil or socio.telefonoFijo,
            inscripcion.fecha_inscripcion.strftime("%d/%m/%Y"),
            inscripcion.estado.value if inscripcion.estado else "No Definido",
            matricula.estado.value if matricula else "No",
            matricula.fecha.strftime("%d/%m/%Y") if matricula else "No Matriculado"
        ]
        x = 20 * mm
        for j, texto in enumerate(fila):
            c.drawString(x, y, texto)
            if j == 0:
                x += 10 * mm  # Ajuste para el nombre
            elif j == 1:
                x += 40 * mm
            else:
                x += 25 * mm

        y -= 7*mm
        if y < 20*mm:
            c.showPage()
            y = height - 20*mm
    
    if actividad.numero_maximo_alumnos is not None:
        max_inscritos = actividad.numero_maximo_alumnos
        height_line = height - 43*mm - (max_inscritos * 7*mm)
        c.line(15*mm, height_line, 200*mm, height_line)

    c.save()
