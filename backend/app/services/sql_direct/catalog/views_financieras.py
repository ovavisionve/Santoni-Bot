"""Catálogo: Finanzas, Compras, Contabilidad, Producción, Inventario, Saldos."""

VIEWS_FINANCIERAS = """
### Finanzas — Bancos
**lve_disponibilidadbancaria** — Saldos bancarios disponibles (view oficial de Santoni)
**lve_disponibilidadbancariateso** — Saldos bancarios vista tesorería
**lve_disponibilidadbancariagerencia** — Saldos bancarios vista gerencia
**lve_compromisosbancarios** — Compromisos bancarios pendientes

### Compras a Productores — Guías
**c_order** — Órdenes de compra / Guías de recepción a productores
Columnas: c_order_id, c_bpartner_id, dateordered, issotrx, docstatus, ad_org_id
**c_orderline** — Líneas de orden (qtyordered, m_product_id, linenetamt)
**m_product** — Productos (name, value, m_product_category_id)
IMPORTANTE: compras a productores usan c_order (guías), NO c_invoice

### Compras de Insumos
Usa c_invoice con issotrx='N' (misma tabla que ventas pero filtro opuesto)

### Contabilidad
**fact_acct** — Hechos contables
Columnas: fact_acct_id, account_id, dateacct, amtacctdr (debe), amtacctcr (haber),
  ad_org_id, c_period_id
**c_elementvalue** — Plan de cuentas (nombre y tipo de cuenta)
accounttype: A=Activo, L=Pasivo, O=Patrimonio, R=Ingreso, E=Gasto

### Producción / Inventario
**m_inout** — Movimientos de inventario (recepciones y despachos)
Columnas: m_inout_id, movementdate, movementtype, docstatus, ad_org_id
movementtype: V+=Recepción, C-=Despacho, M+/M-=Mov. interno, P+/P-=Producción
**m_inoutline** — Líneas (movementqty, m_product_id)

### Saldos de clientes/proveedores
**lve_saldosclientes** — Saldos pendientes de clientes
**lve_saldosproveedor** — Saldos pendientes de proveedores
**lve_saldosproductor** — Saldos pendientes de productores agrícolas
**lve_customer_statement** — Estado de cuenta de clientes
**lve_supplier_statement** — Estado de cuenta de proveedores
**lve_analisisvencimientoinproa** — Análisis de vencimiento de facturas INPROA

### Cobranza — Views oficiales
**lve_informepago** — Informe de pagos
**lve_resumencobro** — Resumen de cobros
**lve_payment** — Pagos detallados
**lve_payment_receipt** — Recibos de pago

### Compras — Views oficiales
**lve_buy_book** — Libro de compras
**lve_buy_book_sumary** — Resumen del libro de compras
**lve_anticipoproductor** — Anticipos a productores
**lve_anticipoproveedor** — Anticipos a proveedores
**lve_guiasmovilizacion** — Guías de movilización de productores

### Contabilidad — Views oficiales
**lve_fact_acct** — Hechos contables (versión LVE)
**lve_trialbalance** — Balance de comprobación

### Inventario — Views oficiales
**lve_inventario_terminado** — Inventario de producto terminado
**lve_inventario_paddy** — Inventario de arroz paddy
**lve_inventario_maiz** — Inventario de maíz
**lve_inventario_empaque** — Inventario de materiales de empaque
**lve_inventario_granos** — Inventario de granos
**lve_inventario_repuesto** — Inventario de repuestos
**lve_inventario_comercial** — Inventario comercial
**lve_existenciayubicacion** — Existencias y ubicación por almacén

### Ventas — Views oficiales
**lve_sales_book** — Libro de ventas (por factura, estilo SENIAT)
**lve_sales_books** — Libros de ventas (plural)
"""
