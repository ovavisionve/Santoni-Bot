"""Seed contabilidad: asientos contables, balance general."""

import random
from datetime import date
from decimal import Decimal

from app.models.demo_data import DemoAsientoContable, DemoBalanceGeneral


def seed_contabilidad(db) -> dict:
    # Asientos Contables
    cuentas_contables = [
        ("1.1.01", "Caja"),
        ("1.1.02", "Bancos"),
        ("1.1.03", "Cuentas por Cobrar"),
        ("1.1.04", "Inventario de Productos Terminados"),
        ("1.1.05", "Inventario de Materia Prima"),
        ("1.2.01", "Maquinaria y Equipos"),
        ("1.2.02", "Mobiliario"),
        ("2.1.01", "Cuentas por Pagar Proveedores"),
        ("2.1.02", "Impuestos por Pagar"),
        ("2.1.03", "Nómina por Pagar"),
        ("2.2.01", "Préstamos Bancarios LP"),
        ("3.1.01", "Capital Social"),
        ("3.1.02", "Utilidades Retenidas"),
        ("4.1.01", "Ingresos por Ventas"),
        ("5.1.01", "Costo de Ventas"),
        ("6.1.01", "Gastos de Administración"),
        ("6.2.01", "Gastos de Ventas"),
    ]

    asientos = []
    for i in range(80):
        mes = random.randint(1, 6)
        dia = random.randint(1, 28)
        fecha = date(2025, mes, dia)
        periodo = f"2025-{mes:02d}"
        cuenta_code, cuenta_name = random.choice(cuentas_contables)
        monto_asiento = Decimal(str(random.randint(10000, 800000)))
        es_debe = random.random() < 0.5

        asientos.append(DemoAsientoContable(
            numero_asiento=f"AS-{2025}{mes:02d}-{i+1:04d}",
            fecha=fecha,
            cuenta_contable=cuenta_code,
            nombre_cuenta=cuenta_name,
            descripcion=f"Registro contable - {cuenta_name}",
            debe=monto_asiento if es_debe else Decimal("0"),
            haber=Decimal("0") if es_debe else monto_asiento,
            periodo=periodo,
        ))

    db.add_all(asientos)
    db.flush()

    # Balance General
    balance_items = [
        # Activos Circulantes
        ("activo", "Activo Circulante", "Caja y Bancos", 4500000),
        ("activo", "Activo Circulante", "Cuentas por Cobrar Comerciales", 8200000),
        ("activo", "Activo Circulante", "Inventario Productos Terminados", 6300000),
        ("activo", "Activo Circulante", "Inventario Materia Prima", 3800000),
        ("activo", "Activo Circulante", "Anticipos a Proveedores", 1200000),
        # Activos Fijos
        ("activo", "Activo Fijo", "Maquinaria y Equipos", 15000000),
        ("activo", "Activo Fijo", "Terrenos y Edificaciones", 22000000),
        ("activo", "Activo Fijo", "Vehículos", 5500000),
        ("activo", "Activo Fijo", "Depreciación Acumulada", -8500000),
        # Pasivos Circulantes
        ("pasivo", "Pasivo Circulante", "Cuentas por Pagar Proveedores", 5800000),
        ("pasivo", "Pasivo Circulante", "Impuestos por Pagar", 1900000),
        ("pasivo", "Pasivo Circulante", "Nómina por Pagar", 2100000),
        ("pasivo", "Pasivo Circulante", "Retenciones por Pagar", 800000),
        # Pasivos Largo Plazo
        ("pasivo", "Pasivo Largo Plazo", "Préstamos Bancarios", 12000000),
        ("pasivo", "Pasivo Largo Plazo", "Prestaciones Sociales por Pagar", 4500000),
        # Patrimonio
        ("patrimonio", "Patrimonio", "Capital Social", 18000000),
        ("patrimonio", "Patrimonio", "Reserva Legal", 3600000),
        ("patrimonio", "Patrimonio", "Utilidades Retenidas", 9500000),
    ]

    balance_records = []
    for mes in range(1, 7):
        periodo = f"2025-{mes:02d}"
        for tipo_cuenta, grupo, cuenta, saldo_base in balance_items:
            variacion = Decimal(str(round(random.uniform(0.95, 1.08), 3)))
            saldo = (Decimal(str(saldo_base)) * variacion).quantize(Decimal("0.01"))
            balance_records.append(DemoBalanceGeneral(
                periodo=periodo,
                tipo_cuenta=tipo_cuenta,
                grupo=grupo,
                cuenta=cuenta,
                saldo=saldo,
            ))

    db.add_all(balance_records)
    db.flush()

    return {
        "asientos": len(asientos),
        "balance_records": len(balance_records),
    }
