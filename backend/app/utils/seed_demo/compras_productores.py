"""Seed compras a productores: productores registrados y compras (guías)."""

import random
from datetime import date
from decimal import Decimal

from app.models.demo_data import DemoCompraProductor, DemoProductor

from .common import _cedula, _random_date, _telefono


def seed_compras_productores(db) -> dict:
    estados_productor = {
        "Portuguesa": ["Agua Blanca", "Araure", "Acarigua", "Guanare", "Ospino", "Páez", "Turén", "Santa Rosalía"],
        "Barinas": ["Barinas", "Barinitas", "Obispos", "Socopó", "Santa Bárbara"],
        "Apure": ["San Fernando", "Achaguas", "Biruaca", "Guasdualito"],
        "Lara": ["Carora", "El Tocuyo", "Quíbor"],
        "Cojedes": ["San Carlos", "Tinaco", "Tinaquillo"],
    }
    estados_prod_list = list(estados_productor.keys())

    apellidos_campo = [
        "Pérez", "Rodríguez", "García", "López", "Hernández", "González",
        "Díaz", "Martínez", "Torres", "Ramírez", "Flores", "Morales",
        "Castillo", "Mendoza", "Rojas", "Vargas", "Paredes", "Rivas",
        "Suárez", "Fernández", "Medina", "Briceño", "Quintero", "Pacheco",
        "Contreras", "Zambrano", "Escalona", "Vásquez", "Rangel", "Colmenares",
        "Montilla", "Oropeza", "Baptista", "Andrade", "Lozano", "Gutiérrez",
        "Castellanos", "Villegas", "Parra", "Salazar",
    ]
    nombres_campo = [
        "José", "Luis", "Carlos", "Pedro", "Miguel", "Juan", "Rafael",
        "Andrés", "Francisco", "Jesús", "Manuel", "Antonio", "Ramón",
        "Domingo", "Félix", "Simón", "Gregorio", "Ernesto", "Alfredo",
        "Tomás",
    ]

    productores = []
    for i in range(80):
        tipo = "arroz" if i < 60 else "maiz"
        estado = estados_prod_list[i % len(estados_prod_list)]
        municipio = random.choice(estados_productor[estado])
        nombre = f"{random.choice(nombres_campo)} {random.choice(apellidos_campo)}"
        hectareas = Decimal(str(random.randint(10, 500)))

        productores.append(DemoProductor(
            codigo=f"PROD-{i+1:04d}",
            nombre=nombre,
            cedula=_cedula(),
            telefono=_telefono(),
            estado=estado,
            municipio=municipio,
            tipo_producto=tipo,
            hectareas=hectareas,
            activo=True,
        ))

    db.add_all(productores)
    db.flush()

    # Compras
    compras_prod = []
    for i in range(200):
        productor = random.choice(productores)
        fecha = _random_date(date(2025, 1, 1), date(2025, 12, 31))
        if productor.tipo_producto == "arroz":
            producto = "Arroz Paddy Húmedo"
            humedad = Decimal(str(round(random.uniform(20.0, 28.0), 2)))
            impureza = Decimal(str(round(random.uniform(1.0, 5.0), 2)))
            precio_kg = Decimal(str(round(random.uniform(8.00, 15.00), 4)))
        else:
            producto = "Maíz"
            humedad = Decimal(str(round(random.uniform(13.0, 18.0), 2)))
            impureza = Decimal(str(round(random.uniform(1.0, 4.0), 2)))
            precio_kg = Decimal(str(round(random.uniform(6.00, 12.00), 4)))

        peso_bruto = Decimal(str(random.randint(5000, 30000)))
        tara = Decimal(str(random.randint(3000, 8000)))
        peso_neto = peso_bruto - tara
        if peso_neto < Decimal("1000"):
            peso_neto = Decimal(str(random.randint(3000, 15000)))

        monto_total_cp = (peso_neto * precio_kg).quantize(Decimal("0.01"))
        estado_pago = random.choice(["pagado", "pagado", "pagado", "pendiente"])

        compras_prod.append(DemoCompraProductor(
            numero_guia=f"GR-{2025}{i+1:05d}",
            productor_id=productor.id,
            fecha=fecha,
            producto=producto,
            peso_bruto_kg=peso_bruto,
            peso_neto_kg=peso_neto,
            humedad_porcentaje=humedad,
            impureza_porcentaje=impureza,
            precio_kg=precio_kg,
            monto_total=monto_total_cp,
            estado_pago=estado_pago,
            moneda="VES",
        ))

    db.add_all(compras_prod)

    return {
        "productores": len(productores),
        "compras_prod": len(compras_prod),
    }
