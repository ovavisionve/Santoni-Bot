"""Seed compras de insumos: proveedores y órdenes de compra."""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.models.demo_data import DemoOrdenCompraInsumo, DemoProveedorInsumo

from .common import _random_date, _rif_juridico, _telefono


def seed_compras_insumos(db) -> dict:
    proveedores_insumos_data = [
        ("Empaques Flexibles de Venezuela C.A.", "Empaques", 4),
        ("Polímeros del Centro S.A.", "Empaques", 5),
        ("Sacos y Envases Portuguesa", "Empaques", 3),
        ("Químicos Industriales Barinas C.A.", "Químicos", 4),
        ("Productos Químicos del Llano", "Químicos", 3),
        ("Repuestos Industriales Acarigua", "Repuestos", 4),
        ("Maquinaria y Partes La Industrial", "Repuestos", 5),
        ("Rodamientos del Centro C.A.", "Repuestos", 4),
        ("Papelería y Oficina Araure", "Material de Oficina", 3),
        ("Suministros de Oficina Lara", "Material de Oficina", 4),
        ("Combustibles del Llano S.A.", "Combustibles", 5),
        ("Lubricantes Industriales VEN", "Lubricantes", 4),
        ("Etiquetas y Códigos Barras C.A.", "Etiquetas", 3),
        ("Materiales de Limpieza Industrial", "Limpieza", 4),
        ("Equipos de Seguridad Industrial C.A.", "Seguridad Industrial", 5),
    ]

    proveedores_insumos = []
    for i, (nombre, tipo_ins, calif) in enumerate(proveedores_insumos_data):
        proveedores_insumos.append(DemoProveedorInsumo(
            codigo=f"PROV-{i+1:03d}",
            nombre=nombre,
            rif=_rif_juridico(),
            contacto=f"Contacto {nombre.split()[0]}",
            telefono=_telefono(),
            tipo_insumo=tipo_ins,
            calificacion=calif,
        ))

    db.add_all(proveedores_insumos)
    db.flush()

    # Órdenes de Compra
    insumos_por_tipo = {
        "Empaques": [("Bolsas 1kg Arroz", "unidad", 0.50, 2.00), ("Bolsas 5kg Arroz", "unidad", 1.50, 4.00), ("Sacos 50kg", "unidad", 5.00, 12.00)],
        "Químicos": [("Hipoclorito de Sodio", "litro", 8.00, 20.00), ("Desinfectante Industrial", "litro", 15.00, 35.00)],
        "Repuestos": [("Rodamiento 6205", "unidad", 50.00, 150.00), ("Banda Transportadora 5m", "unidad", 200.00, 600.00), ("Filtro de Aceite", "unidad", 30.00, 80.00)],
        "Material de Oficina": [("Resma Papel Carta", "unidad", 15.00, 30.00), ("Tóner Impresora", "unidad", 80.00, 200.00)],
        "Combustibles": [("Diesel", "litro", 0.50, 1.50)],
        "Lubricantes": [("Aceite Industrial 20W50", "litro", 20.00, 50.00)],
        "Etiquetas": [("Etiqueta Arroz Premium", "millar", 100.00, 250.00)],
        "Limpieza": [("Detergente Industrial", "litro", 10.00, 25.00)],
        "Seguridad Industrial": [("Guantes de Nitrilo", "caja", 30.00, 70.00), ("Mascarilla Industrial", "caja", 50.00, 120.00)],
    }

    ordenes_compra = []
    estados_oc = ["pendiente", "recibida", "recibida", "recibida", "parcial"]
    for i in range(50):
        prov = random.choice(proveedores_insumos)
        tipo_ins = prov.tipo_insumo
        if tipo_ins in insumos_por_tipo:
            insumo_data = random.choice(insumos_por_tipo[tipo_ins])
        else:
            insumo_data = ("Insumo General", "unidad", 10.00, 50.00)
        insumo_nombre, unidad, precio_min, precio_max = insumo_data
        precio = Decimal(str(round(random.uniform(precio_min, precio_max), 2)))
        cantidad = Decimal(str(random.randint(50, 5000)))
        monto_total_oc = (precio * cantidad).quantize(Decimal("0.01"))
        fecha_oc = _random_date(date(2025, 1, 1), date(2025, 6, 30))
        fecha_entrega_est = fecha_oc + timedelta(days=random.randint(5, 30))
        estado_oc = random.choice(estados_oc)
        fecha_entrega_real = fecha_entrega_est + timedelta(days=random.randint(-3, 10)) if estado_oc in ["recibida", "parcial"] else None

        ordenes_compra.append(DemoOrdenCompraInsumo(
            numero_orden=f"OCI-{2025}{i+1:04d}",
            proveedor_id=prov.id,
            fecha=fecha_oc,
            fecha_entrega_estimada=fecha_entrega_est,
            fecha_entrega_real=fecha_entrega_real,
            insumo=insumo_nombre,
            cantidad=cantidad,
            unidad=unidad,
            precio_unitario=precio,
            monto_total=monto_total_oc,
            estado=estado_oc,
        ))

    db.add_all(ordenes_compra)
    db.flush()

    return {
        "proveedores_insumos": len(proveedores_insumos),
        "ordenes_compra": len(ordenes_compra),
    }
