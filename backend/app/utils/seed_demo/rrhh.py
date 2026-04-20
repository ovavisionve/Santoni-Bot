"""Seed RRHH: empleados, nómina, asistencia."""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.models.demo_data import DemoAsistencia, DemoEmpleado, DemoNomina

from .common import _cedula, _random_date


def seed_rrhh(db) -> dict:
    # Empleados (45)
    departamentos_empleados = {
        "Producción": [
            ("Jefe de Planta", 1), ("Operador de Línea", 8),
            ("Supervisor de Turno", 2), ("Ayudante de Producción", 4),
        ],
        "Ventas": [
            ("Gerente de Ventas", 1), ("Vendedor", 3), ("Facturador", 1),
            ("Asistente de Ventas", 1),
        ],
        "Administración": [
            ("Gerente Administrativo", 1), ("Contador", 2),
            ("Asistente Administrativo", 2), ("Recepcionista", 1),
        ],
        "Recursos Humanos": [
            ("Jefe de RRHH", 1), ("Analista de Nómina", 1),
            ("Asistente de RRHH", 1),
        ],
        "Compras": [
            ("Jefe de Compras", 1), ("Analista de Compras", 2),
            ("Asistente de Compras", 1),
        ],
        "Almacén": [
            ("Jefe de Almacén", 1), ("Almacenista", 3),
            ("Despachador", 2),
        ],
        "Mantenimiento": [
            ("Jefe de Mantenimiento", 1), ("Técnico Mecánico", 2),
            ("Electricista", 1),
        ],
        "Control de Calidad": [
            ("Jefe de Calidad", 1), ("Analista de Laboratorio", 1),
        ],
    }

    nombres_empleados = [
        "Carlos Matias", "Lenny Silva", "Yuleidys Gutierrez",
        "José Rodríguez", "María Pérez", "Luis González",
        "Ana Martínez", "Pedro Hernández", "Carmen López",
        "Juan Díaz", "Rosa Ramírez", "Miguel Torres",
        "Luisa Flores", "Carlos García", "Isabel Morales",
        "Andrés Castillo", "Marta Mendoza", "Francisco Rojas",
        "Teresa Vargas", "Rafael Paredes", "Patricia Rivas",
        "Eduardo Suárez", "Gabriela Fernández", "Héctor Medina",
        "Yolanda Briceño", "Daniel Quintero", "Liliana Pacheco",
        "Omar Contreras", "Nelly Zambrano", "Roberto Escalona",
        "Sandra Vásquez", "Alberto Rangel", "Delia Colmenares",
        "Jesús Montilla", "Karla Oropeza", "Emilio Baptista",
        "Marisol Andrade", "Freddy Lozano", "Norma Gutiérrez",
        "Simón Castellanos", "Adriana Villegas", "Gregorio Parra",
        "Beatriz Salazar", "Ernesto Urdaneta", "Claudia Rivero",
    ]

    empleados = []
    emp_idx = 0
    for depto, cargos in departamentos_empleados.items():
        for cargo, cantidad in cargos:
            for _ in range(cantidad):
                if emp_idx >= 45:
                    break
                nombre = nombres_empleados[emp_idx]
                ubicacion = "Agua Blanca" if depto in ["Producción", "Almacén", "Mantenimiento", "Control de Calidad"] else "Araure"
                turno = "rotativo" if depto == "Producción" and cargo != "Jefe de Planta" else "diurno"
                salario = Decimal(str(random.randint(800, 4500))) if cargo.startswith("Jefe") or cargo.startswith("Gerente") else Decimal(str(random.randint(450, 1200)))
                salario = salario * Decimal("100")

                empleados.append(DemoEmpleado(
                    cedula=_cedula(),
                    nombre=nombre,
                    cargo=cargo,
                    departamento=depto,
                    ubicacion=ubicacion,
                    fecha_ingreso=_random_date(date(2015, 1, 1), date(2024, 12, 31)),
                    salario_basico=salario,
                    turno=turno,
                    activo=True,
                    fecha_nacimiento=_random_date(date(1970, 1, 1), date(2000, 12, 31)),
                ))
                emp_idx += 1

    db.add_all(empleados)
    db.flush()

    # Nómina (Jan-Jun 2025)
    nominas = []
    for emp in empleados:
        for mes in range(1, 7):
            periodo = f"2025-{mes:02d}"
            asignaciones = (emp.salario_basico * Decimal(str(round(random.uniform(0.10, 0.35), 2)))).quantize(Decimal("0.01"))
            deducciones = (emp.salario_basico * Decimal(str(round(random.uniform(0.05, 0.15), 2)))).quantize(Decimal("0.01"))
            neto = emp.salario_basico + asignaciones - deducciones

            nominas.append(DemoNomina(
                empleado_id=emp.id,
                periodo=periodo,
                tipo_nomina="quincenal",
                salario_basico=emp.salario_basico,
                asignaciones=asignaciones,
                deducciones=deducciones,
                neto_pagar=neto,
            ))

    db.add_all(nominas)
    db.flush()

    # Asistencia (January 2025 weekdays)
    asistencias = []
    current = date(2025, 1, 1)
    end_jan = date(2025, 1, 31)
    while current <= end_jan:
        if current.weekday() < 5:  # Monday-Friday
            for emp in empleados:
                r = random.random()
                if r < 0.88:
                    tipo = "asistencia"
                    hora_entrada = f"{random.randint(6, 8):02d}:{random.choice(['00', '05', '10', '15', '20', '30'])}"
                    hora_salida = f"{random.randint(16, 18):02d}:{random.choice(['00', '15', '30', '45'])}"
                elif r < 0.93:
                    tipo = "falta"
                    hora_entrada = None
                    hora_salida = None
                elif r < 0.97:
                    tipo = "permiso"
                    hora_entrada = None
                    hora_salida = None
                else:
                    tipo = "vacacion"
                    hora_entrada = None
                    hora_salida = None

                asistencias.append(DemoAsistencia(
                    empleado_id=emp.id,
                    fecha=current,
                    hora_entrada=hora_entrada,
                    hora_salida=hora_salida,
                    tipo=tipo,
                ))
        current += timedelta(days=1)

    db.add_all(asistencias)
    db.flush()

    return {
        "empleados": len(empleados),
        "nominas": len(nominas),
        "asistencias": len(asistencias),
    }
