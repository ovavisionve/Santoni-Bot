"""Seed finanzas: cuentas bancarias, movimientos, cuentas por pagar."""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.models.demo_data import (
    DemoCuentaBancaria,
    DemoCuentaPorPagar,
    DemoMovimientoBancario,
)

from .common import _random_date


def seed_finanzas(db) -> dict:
    # Cuentas Bancarias
    bancos_data = [
        ("Banesco", "0134-0123-45-1234567890", "corriente", "VES", Decimal("4500000.00")),
        ("Mercantil", "0105-0234-56-2345678901", "corriente", "VES", Decimal("3200000.00")),
        ("Provincial", "0108-0345-67-3456789012", "corriente", "VES", Decimal("2800000.00")),
        ("BOD", "0116-0456-78-4567890123", "corriente", "USD", Decimal("125000.00")),
        ("BNC", "0191-0567-89-5678901234", "ahorro", "VES", Decimal("1500000.00")),
    ]
    cuentas = []
    for banco, num, tipo, moneda, saldo in bancos_data:
        cuentas.append(DemoCuentaBancaria(
            banco=banco,
            numero_cuenta=num,
            tipo=tipo,
            moneda=moneda,
            saldo=saldo,
            fecha_saldo=date(2025, 6, 30),
        ))

    db.add_all(cuentas)
    db.flush()

    # Movimientos Bancarios
    descripciones_debito = [
        "Pago nómina quincenal", "Pago a proveedor", "Pago servicio eléctrico",
        "Pago INCE", "Pago IVSS", "Transferencia a cuenta USD",
        "Pago alquiler galpón", "Compra materia prima", "Pago transporte",
        "Pago servicio internet", "Pago impuestos municipales", "Pago seguros",
    ]
    descripciones_credito = [
        "Cobro factura cliente", "Depósito en efectivo", "Transferencia recibida",
        "Cobro cheque", "Abono préstamo", "Ingreso por venta directa",
    ]

    movimientos = []
    for i in range(100):
        cuenta = random.choice(cuentas)
        fecha = _random_date(date(2025, 1, 1), date(2025, 12, 31))
        es_debito = random.random() < 0.55
        if es_debito:
            desc = random.choice(descripciones_debito)
            tipo = "debito"
            monto = Decimal(str(random.randint(5000, 500000)))
        else:
            desc = random.choice(descripciones_credito)
            tipo = "credito"
            monto = Decimal(str(random.randint(10000, 800000)))

        if cuenta.moneda == "USD":
            monto = (monto / Decimal("36")).quantize(Decimal("0.01"))

        movimientos.append(DemoMovimientoBancario(
            cuenta_id=cuenta.id,
            fecha=fecha,
            descripcion=desc,
            referencia=f"REF-{random.randint(100000, 999999)}",
            tipo=tipo,
            monto=monto,
            saldo=cuenta.saldo + (monto if tipo == "credito" else -monto),
        ))

    db.add_all(movimientos)
    db.flush()

    # Cuentas por Pagar
    proveedores_pagar = [
        "Empaques Flexibles C.A.", "Quimicos Industriales del Centro",
        "Repuestos y Maquinaria Llanos", "Transporte La Ceiba C.A.",
        "Electricidad Industrial Aragua", "Plásticos del Oeste S.A.",
        "Gases Industriales Venezuela", "Ferretería Industrial Portuguesa",
        "Lubricantes y Filtros Barinas", "Seguridad Industrial VEN",
        "Papelería Comercial Araure", "Servicios Técnicos Acarigua",
        "Fumigaciones del Llano", "Impresiones Gráficas Lara",
        "Mantenimiento Integral C.A.",
    ]

    cuentas_pagar = []
    for i in range(30):
        prov = random.choice(proveedores_pagar)
        fecha_fact = _random_date(date(2025, 1, 1), date(2025, 6, 30))
        monto_orig = Decimal(str(random.randint(15000, 600000)))
        pagado = random.random() < 0.5
        monto_pend = Decimal("0") if pagado else monto_orig
        estado_cp = "pagada" if pagado else "pendiente"

        cuentas_pagar.append(DemoCuentaPorPagar(
            proveedor=prov,
            numero_factura=f"FP-{random.randint(10000, 99999)}",
            fecha_factura=fecha_fact,
            fecha_vencimiento=fecha_fact + timedelta(days=random.choice([30, 45, 60, 90])),
            monto_original=monto_orig,
            monto_pendiente=monto_pend,
            moneda="VES",
            estado=estado_cp,
        ))

    db.add_all(cuentas_pagar)
    db.flush()

    return {
        "cuentas": len(cuentas),
        "movimientos": len(movimientos),
        "cuentas_pagar": len(cuentas_pagar),
    }
