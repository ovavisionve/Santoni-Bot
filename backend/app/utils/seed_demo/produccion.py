"""Seed producción: producción diaria, órdenes de producción."""

import random
from datetime import date
from decimal import Decimal

from app.models.demo_data import DemoOrdenProduccion, DemoProduccionDiaria

from .common import _random_date


def seed_produccion(db) -> dict:
    plantas = ["Planta 1", "Planta 2"]
    lineas_prod = {
        "Línea Arroz": ["Arroz Santoni Premium", "Arroz Integral Santoni", "Arroz Parboiled Santoni"],
        "Línea Maíz": ["Harina de Maíz Santoni"],
    }
    turnos_prod = ["diurno", "nocturno"]
    motivos_parada = [
        None, None, None, None,
        "Mantenimiento preventivo", "Falla mecánica", "Falta de materia prima",
        "Cambio de producto", "Limpieza de línea", "Falla eléctrica",
    ]

    prod_diaria = []
    for i in range(120):
        fecha = _random_date(date(2025, 1, 1), date(2025, 6, 30))
        planta = random.choice(plantas)
        linea = random.choice(list(lineas_prod.keys()))
        producto = random.choice(lineas_prod[linea])
        turno = random.choice(turnos_prod)
        cantidad = Decimal(str(random.randint(5000, 25000)))
        desperdicio = (cantidad * Decimal(str(round(random.uniform(0.01, 0.05), 3)))).quantize(Decimal("0.01"))
        horas_op = Decimal(str(round(random.uniform(6.0, 8.0), 2)))
        motivo = random.choice(motivos_parada)
        horas_parada = Decimal(str(round(random.uniform(0.5, 3.0), 2))) if motivo else Decimal("0")

        prod_diaria.append(DemoProduccionDiaria(
            fecha=fecha,
            planta=planta,
            linea=linea,
            turno=turno,
            producto=producto,
            cantidad_kg=cantidad,
            desperdicio_kg=desperdicio,
            horas_operacion=horas_op,
            horas_parada=horas_parada,
            motivo_parada=motivo,
        ))

    db.add_all(prod_diaria)
    db.flush()

    # Órdenes de Producción
    estados_orden = ["planificada", "en_proceso", "completada", "completada", "completada"]
    ordenes_prod = []
    for i in range(40):
        fecha = _random_date(date(2025, 1, 1), date(2025, 6, 30))
        linea = random.choice(list(lineas_prod.keys()))
        producto = random.choice(lineas_prod[linea])
        planta = random.choice(plantas)
        cant_plan = Decimal(str(random.randint(10000, 50000)))
        estado_ord = random.choice(estados_orden)
        if estado_ord == "completada":
            cant_prod = (cant_plan * Decimal(str(round(random.uniform(0.92, 1.02), 3)))).quantize(Decimal("0.01"))
        elif estado_ord == "en_proceso":
            cant_prod = (cant_plan * Decimal(str(round(random.uniform(0.30, 0.70), 3)))).quantize(Decimal("0.01"))
        else:
            cant_prod = Decimal("0")

        ordenes_prod.append(DemoOrdenProduccion(
            numero_orden=f"OP-{2025}{i+1:04d}",
            fecha=fecha,
            producto=producto,
            cantidad_planificada=cant_plan,
            cantidad_producida=cant_prod,
            estado=estado_ord,
            planta=planta,
        ))

    db.add_all(ordenes_prod)
    db.flush()

    return {
        "prod_diaria": len(prod_diaria),
        "ordenes_prod": len(ordenes_prod),
    }
