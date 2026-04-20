"""Seed ventas: clientes, facturas, líneas, cobranzas, metas."""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.models.demo_data import (
    DemoCliente,
    DemoCobranza,
    DemoFacturaVenta,
    DemoLineaFacturaVenta,
    DemoMetaVenta,
)

from .common import _random_date, _rif_juridico, _telefono


def seed_ventas(db) -> dict:
    """Create clients, invoices, lines, collections and sales goals. Returns counts."""
    vendedores = ["Carlos Matias", "Lenny Silva", "Yuleidys Gutierrez"]
    zonas_info = {
        "Portuguesa": ["Acarigua", "Araure", "Guanare", "Agua Blanca", "Ospino"],
        "Barinas": ["Barinas", "Barinitas", "Socopó", "Santa Bárbara"],
        "Lara": ["Barquisimeto", "Cabudare", "Carora", "Quíbor"],
        "Carabobo": ["Valencia", "Naguanagua", "Guacara", "Puerto Cabello"],
        "Aragua": ["Maracay", "Turmero", "La Victoria", "Cagua"],
        "Zulia": ["Maracaibo", "Cabimas", "Ciudad Ojeda", "San Francisco"],
    }
    zonas = list(zonas_info.keys())
    tipologias = ["mayorista", "detallista", "supermercado", "institucional"]

    nombre_prefixes = [
        "Distribuidora", "Abastos", "Comercializadora", "Supermercado",
        "Bodega", "Inversiones", "Víveres", "Auto Mercado", "Hipermercado",
        "Central de Alimentos", "Almacén", "Mercal Express", "Frigorífico",
    ]
    nombre_suffixes = [
        "El Llano", "La Sabana", "Los Andes", "El Progreso", "San José",
        "Santa Rosa", "El Río", "La Montaña", "El Valle", "El Centro",
        "La Esperanza", "Don Pedro", "Doña María", "San Antonio", "El Trébol",
        "La Colina", "Mi Tierra", "El Paisa", "Los Hermanos", "La Familia",
        "Don Carlos", "El Diamante", "La Estrella", "El Sol", "Los Primos",
        "El Portal", "La Gran Esquina", "Don Julio", "El Buen Precio",
        "La Economía", "El Campesino", "Don Rafael", "La Nueva", "El Porvenir",
        "San Miguel", "La Cascada", "El Manantial", "Don Luis", "Los Altos",
        "El Trigal", "La Floresta", "El Marqués", "San Cristóbal", "El Rosal",
        "La Pradera", "Don Simón", "El Samán", "La Ceiba", "El Palmar",
        "Los Robles",
    ]

    clientes = []
    for i in range(50):
        zona = zonas[i % len(zonas)]
        ciudad = random.choice(zonas_info[zona])
        vendedor = vendedores[i % len(vendedores)]
        tipologia = random.choice(tipologias)
        prefix = nombre_prefixes[i % len(nombre_prefixes)]
        suffix = nombre_suffixes[i]
        fecha_reg = _random_date(date(2020, 1, 1), date(2024, 6, 30))
        ultima = _random_date(date(2025, 1, 1), date(2025, 12, 31)) if random.random() > 0.1 else None
        limite = Decimal(str(random.choice([5000, 10000, 20000, 50000, 100000, 200000, 500000])))

        c = DemoCliente(
            codigo=f"CLI-{i+1:04d}",
            nombre=f"{prefix} {suffix}",
            rif=_rif_juridico(),
            zona=zona,
            vendedor=vendedor,
            tipologia=tipologia,
            telefono=_telefono(),
            direccion=f"Calle Principal, {ciudad}, {zona}",
            estado=zona,
            ciudad=ciudad,
            activo=True,
            fecha_registro=fecha_reg,
            ultima_compra=ultima,
            limite_credito=limite,
        )
        clientes.append(c)

    db.add_all(clientes)
    db.flush()

    # Facturas
    productos_venta = [
        ("Arroz Santoni Premium 1kg", "Arroz", Decimal("45.50")),
        ("Arroz Santoni 5kg", "Arroz", Decimal("215.00")),
        ("Harina de Maíz Santoni 1kg", "Harina de Maíz", Decimal("38.75")),
        ("Arroz Integral Santoni 1kg", "Arroz", Decimal("52.00")),
        ("Arroz Parboiled Santoni 1kg", "Arroz", Decimal("48.25")),
    ]

    facturas = []
    lineas_factura = []
    for i in range(200):
        cliente = random.choice(clientes)
        fecha = _random_date(date(2025, 1, 1), date(2025, 12, 31))
        vendedor = cliente.vendedor
        zona = cliente.zona

        num_lines = random.randint(2, 4)
        lines_data = []
        monto_neto = Decimal("0")
        for _ in range(num_lines):
            prod_name, cat, precio_base = random.choice(productos_venta)
            precio = precio_base * Decimal(str(round(random.uniform(0.95, 1.10), 2)))
            precio = precio.quantize(Decimal("0.01"))
            cantidad = Decimal(str(random.randint(10, 500)))
            line_monto = (precio * cantidad).quantize(Decimal("0.01"))
            monto_neto += line_monto
            lines_data.append((prod_name, cat, cantidad, precio, line_monto))

        monto_iva = (monto_neto * Decimal("0.16")).quantize(Decimal("0.01"))
        monto_total = monto_neto + monto_iva

        r = random.random()
        if r < 0.70:
            estado = "pagada"
        elif r < 0.90:
            estado = "pendiente"
        else:
            estado = "anulada"

        f = DemoFacturaVenta(
            numero_factura=f"F-{10000 + i + 1:05d}",
            cliente_id=cliente.id,
            vendedor=vendedor,
            zona=zona,
            fecha=fecha,
            monto_total=monto_total,
            monto_iva=monto_iva,
            monto_neto=monto_neto,
            estado=estado,
            fecha_vencimiento=fecha + timedelta(days=random.choice([15, 30, 45, 60])),
            moneda="VES",
        )
        facturas.append(f)

    db.add_all(facturas)
    db.flush()

    # Líneas de factura
    for idx, f in enumerate(facturas):
        cliente = random.choice(clientes)
        num_lines = random.randint(2, 4)
        for ln in range(num_lines):
            prod_name, cat, precio_base = random.choice(productos_venta)
            precio = precio_base * Decimal(str(round(random.uniform(0.95, 1.10), 2)))
            precio = precio.quantize(Decimal("0.01"))
            cantidad = Decimal(str(random.randint(10, 500)))
            line_monto = (precio * cantidad).quantize(Decimal("0.01"))

            lineas_factura.append(DemoLineaFacturaVenta(
                factura_id=f.id,
                producto=prod_name,
                categoria=cat,
                cantidad=cantidad,
                precio_unitario=precio,
                monto=line_monto,
            ))

    db.add_all(lineas_factura)
    db.flush()

    # Cobranzas
    metodos_pago = ["efectivo", "transferencia", "cheque", "punto_de_venta"]
    facturas_pagadas = [f for f in facturas if f.estado == "pagada"]
    cobranzas = []
    for i in range(150):
        if facturas_pagadas:
            fact = facturas_pagadas[i % len(facturas_pagadas)]
        else:
            fact = facturas[i % len(facturas)]
        cliente_cob = next((c for c in clientes if c.id == fact.cliente_id), clientes[0])
        fecha_cob = fact.fecha + timedelta(days=random.randint(1, 30))
        if fecha_cob > date(2025, 12, 31):
            fecha_cob = date(2025, 12, 31)

        cobranzas.append(DemoCobranza(
            numero_recibo=f"REC-{i+1:05d}",
            cliente_id=cliente_cob.id,
            factura_id=fact.id,
            vendedor=fact.vendedor,
            zona=fact.zona,
            fecha=fecha_cob,
            monto=fact.monto_total,
            metodo_pago=random.choice(metodos_pago),
        ))

    db.add_all(cobranzas)
    db.flush()

    # Metas
    vendedor_zonas = {
        "Carlos Matias": "Portuguesa",
        "Lenny Silva": "Barinas",
        "Yuleidys Gutierrez": "Lara",
    }
    metas = []
    for vendedor, zona in vendedor_zonas.items():
        for mes in range(1, 13):
            base_meta = Decimal(str(random.randint(800000, 1500000)))
            meta_cob = (base_meta * Decimal("0.85")).quantize(Decimal("0.01"))
            metas.append(DemoMetaVenta(
                vendedor=vendedor,
                zona=zona,
                mes=mes,
                anio=2025,
                meta_venta=base_meta,
                meta_cobranza=meta_cob,
            ))

    db.add_all(metas)
    db.flush()

    return {
        "clientes": len(clientes),
        "facturas": len(facturas),
        "lineas_factura": len(lineas_factura),
        "cobranzas": len(cobranzas),
        "metas": len(metas),
    }
