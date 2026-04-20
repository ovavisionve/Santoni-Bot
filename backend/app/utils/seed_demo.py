"""
Seed script for demo data across all 7 departments of Alimentos Santoni, C.A.
Populates realistic Venezuelan business data for development and testing.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models.demo_data import (
    DemoCliente,
    DemoFacturaVenta,
    DemoLineaFacturaVenta,
    DemoCobranza,
    DemoMetaVenta,
    DemoCuentaBancaria,
    DemoMovimientoBancario,
    DemoCuentaPorPagar,
    DemoAsientoContable,
    DemoBalanceGeneral,
    DemoEmpleado,
    DemoNomina,
    DemoAsistencia,
    DemoProduccionDiaria,
    DemoOrdenProduccion,
    DemoProveedorInsumo,
    DemoOrdenCompraInsumo,
    DemoProductor,
    DemoCompraProductor,
)

random.seed(42)


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _rif_juridico() -> str:
    return f"J-{random.randint(10000000, 49999999)}-{random.randint(0, 9)}"


def _cedula() -> str:
    return f"V-{random.randint(5000000, 28000000)}"


def _telefono() -> str:
    prefixes = ["0414", "0424", "0412", "0416", "0426"]
    return f"{random.choice(prefixes)}-{random.randint(1000000, 9999999)}"


def seed_demo_data():
    """Populate all demo tables with realistic Venezuelan business data."""
    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(DemoCliente).count()
        if existing > 0:
            print(f"[SantoniBot] Demo data already exists ({existing} clients). Skipping seed.")
            return

        # ============================================================
        # VENTAS - Clientes (50 clients)
        # ============================================================
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

        # ============================================================
        # VENTAS - Facturas (200 invoices)
        # ============================================================
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

            # Generate 2-4 invoice lines first to calculate totals
            num_lines = random.randint(2, 4)
            lines_data = []
            monto_neto = Decimal("0")
            for _ in range(num_lines):
                prod_name, cat, precio_base = random.choice(productos_venta)
                # Vary price slightly
                precio = precio_base * Decimal(str(round(random.uniform(0.95, 1.10), 2)))
                precio = precio.quantize(Decimal("0.01"))
                cantidad = Decimal(str(random.randint(10, 500)))
                line_monto = (precio * cantidad).quantize(Decimal("0.01"))
                monto_neto += line_monto
                lines_data.append((prod_name, cat, cantidad, precio, line_monto))

            monto_iva = (monto_neto * Decimal("0.16")).quantize(Decimal("0.01"))
            monto_total = monto_neto + monto_iva

            # Estado distribution: 70% pagada, 20% pendiente, 10% anulada
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

        # Create invoice lines
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

        # ============================================================
        # VENTAS - Cobranzas (150 collections)
        # ============================================================
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

        # ============================================================
        # VENTAS - Metas (3 vendedores x 12 meses)
        # ============================================================
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

        # ============================================================
        # FINANZAS - Cuentas Bancarias (5 accounts)
        # ============================================================
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

        # ============================================================
        # FINANZAS - Movimientos Bancarios (100 movements)
        # ============================================================
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

        # ============================================================
        # FINANZAS - Cuentas por Pagar (30 records)
        # ============================================================
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

        # ============================================================
        # CONTABILIDAD - Asientos Contables (80 entries)
        # ============================================================
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

        # ============================================================
        # CONTABILIDAD - Balance General (6 periodos)
        # ============================================================
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
                # Add slight monthly variation
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

        # ============================================================
        # RRHH - Empleados (45 employees)
        # ============================================================
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
                    # Scale to realistic monthly VES (multiply by some factor)
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

        # ============================================================
        # RRHH - Nómina (Jan-Jun 2025)
        # ============================================================
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

        # ============================================================
        # RRHH - Asistencia (January 2025 weekdays)
        # ============================================================
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

        # ============================================================
        # PRODUCCION - Producción Diaria (120 records)
        # ============================================================
        plantas = ["Planta 1", "Planta 2"]
        lineas_prod = {
            "Línea Arroz": ["Arroz Santoni Premium", "Arroz Integral Santoni", "Arroz Parboiled Santoni"],
            "Línea Maíz": ["Harina de Maíz Santoni"],
        }
        turnos_prod = ["diurno", "nocturno"]
        motivos_parada = [
            None, None, None, None,  # Most have no stop
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

        # ============================================================
        # PRODUCCION - Órdenes de Producción (40 orders)
        # ============================================================
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

        # ============================================================
        # COMPRAS INSUMOS - Proveedores (15 suppliers)
        # ============================================================
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

        # ============================================================
        # COMPRAS INSUMOS - Órdenes de Compra (50 orders)
        # ============================================================
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

        # ============================================================
        # COMPRAS PRODUCTORES - Productores (80: 60 arroz + 20 maíz)
        # ============================================================
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

        # ============================================================
        # COMPRAS PRODUCTORES - Compras (200 records)
        # ============================================================
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
            # Discount tare weight (vehicle, etc.)
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

        # Commit everything
        db.commit()

        print(
            f"[SantoniBot] Demo data seeded: "
            f"{len(clientes)} clients, "
            f"{len(facturas)} invoices, "
            f"{len(lineas_factura)} invoice lines, "
            f"{len(cobranzas)} collections, "
            f"{len(metas)} sales targets, "
            f"{len(cuentas)} bank accounts, "
            f"{len(movimientos)} bank movements, "
            f"{len(cuentas_pagar)} payables, "
            f"{len(asientos)} journal entries, "
            f"{len(balance_records)} balance records, "
            f"{len(empleados)} employees, "
            f"{len(nominas)} payroll records, "
            f"{len(asistencias)} attendance records, "
            f"{len(prod_diaria)} production records, "
            f"{len(ordenes_prod)} production orders, "
            f"{len(proveedores_insumos)} supply vendors, "
            f"{len(ordenes_compra)} supply purchase orders, "
            f"{len(productores)} producers, "
            f"{len(compras_prod)} producer purchases"
        )

    except Exception as e:
        db.rollback()
        print(f"[SantoniBot] Error seeding demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
