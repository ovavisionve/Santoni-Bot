"""iDempiere window-name → capability ID mapping.

Window-name patterns are lowercased substrings matched against
`ad_window.name`. When a user's role grants access to a window, they
gain every capability listed alongside that pattern.
"""

# (window_name_pattern, list of capability IDs granted)
WINDOW_CAPABILITY_MAP: list[tuple[str, list[str]]] = [
    # ─── Ventas ───
    ("factura (cliente)", [
        "ventas_facturacion", "ventas_top_clientes", "ventas_cxc",
    ]),
    ("customer invoice", [
        "ventas_facturacion", "ventas_top_clientes", "ventas_cxc",
    ]),
    ("cobros", ["ventas_cobranza"]),
    ("recibo de cobro", ["ventas_cobranza"]),
    ("payment receipt", ["ventas_cobranza"]),
    ("socio del negocio", [
        "ventas_top_clientes", "compras_insumos_facturas",
        "compras_productores_registrados",
    ]),
    ("business partner", [
        "ventas_top_clientes", "compras_insumos_facturas",
        "compras_productores_registrados",
    ]),

    # ─── Finanzas ───
    ("cuenta bancaria", ["finanzas_saldos_bancarios"]),
    ("bank account", ["finanzas_saldos_bancarios"]),
    ("banco", ["finanzas_saldos_bancarios"]),
    ("estado de cuenta", ["finanzas_saldos_bancarios"]),
    ("payment", ["ventas_cobranza", "finanzas_cxc"]),
    ("pago", ["finanzas_cxp"]),

    # ─── Contabilidad ───
    ("esquema contable", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("accounting schema", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("diario contable", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("gl journal", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("asiento", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("cuenta contable", ["contabilidad_cuenta"]),
    ("element value", ["contabilidad_cuenta"]),
    ("plan de cuentas", ["contabilidad_cuenta"]),
    ("informe financiero", ["contabilidad_balance"]),
    ("financial report", ["contabilidad_balance"]),
    ("balance", ["contabilidad_balance"]),
    ("fact_acct", ["contabilidad_balance", "contabilidad_cuenta"]),

    # ─── RRHH ───
    ("empleado", ["rrhh_empleados", "rrhh_lista_empleados", "rrhh_cumpleanos",
                   "rrhh_rotacion"]),
    ("employee", ["rrhh_empleados", "rrhh_lista_empleados", "rrhh_cumpleanos",
                   "rrhh_rotacion"]),
    ("nómina", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("nomina", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("payroll", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("proceso de nómina", ["rrhh_nomina"]),
    ("concepto de nómina", ["rrhh_nomina"]),
    ("payroll concept", ["rrhh_nomina"]),
    ("departamento rrhh", ["rrhh_lista_empleados"]),
    ("hr department", ["rrhh_lista_empleados"]),
    ("puesto", ["rrhh_lista_empleados"]),
    ("hr job", ["rrhh_lista_empleados"]),

    # ─── Producción ───
    ("producción", ["produccion_resumen", "produccion_ordenes"]),
    ("produccion", ["produccion_resumen", "produccion_ordenes"]),
    ("production", ["produccion_resumen", "produccion_ordenes"]),
    ("inventario", ["produccion_inventario", "compras_insumos_inventario"]),
    ("inventory", ["produccion_inventario", "compras_insumos_inventario"]),
    ("almacén", ["produccion_inventario"]),
    ("almacen", ["produccion_inventario"]),
    ("warehouse", ["produccion_inventario"]),
    ("movimiento de inventario", ["produccion_resumen"]),
    ("inventory move", ["produccion_resumen"]),
    ("recibo de material", ["produccion_resumen"]),
    ("material receipt", ["produccion_resumen"]),
    ("entrega", ["produccion_resumen"]),
    ("shipment", ["produccion_resumen"]),

    # ─── Compras Insumos ───
    ("factura (proveedor)", [
        "compras_insumos_facturas", "compras_insumos_historial",
        "compras_insumos_comparacion", "compras_insumos_estado_pago",
    ]),
    ("vendor invoice", [
        "compras_insumos_facturas", "compras_insumos_historial",
        "compras_insumos_comparacion", "compras_insumos_estado_pago",
    ]),
    ("orden de compra", [
        "compras_insumos_oc_pendientes", "compras_productores_compras",
    ]),
    ("purchase order", [
        "compras_insumos_oc_pendientes", "compras_productores_compras",
    ]),

    # ─── Compras Productores ───
    ("recepción", ["compras_productores_compras"]),
    ("recepcion", ["compras_productores_compras"]),
    ("agricultor", ["compras_productores_registrados",
                     "compras_productores_compras"]),
    ("productor", ["compras_productores_registrados",
                    "compras_productores_compras",
                    "compras_productores_pagos_pendientes"]),
]
