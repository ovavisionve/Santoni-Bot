"""Catálogo: views y tablas de Ventas, Monedas, Cobranza y CxC aging."""

VIEWS_VENTAS_CXC = """
### Ventas — Facturas
**c_invoice** — Facturas de venta Y compra (tabla raw, funciona bien para ventas)
Columnas: c_invoice_id, c_bpartner_id, salesrep_id, c_currency_id,
  dateinvoiced, totallines (sin IVA), grandtotal (con IVA), docstatus,
  issotrx ('Y'=venta, 'N'=compra), ad_org_id, c_doctypetarget_id
IMPORTANTE: Para ventas filtrar issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
Para el tipo de documento: JOIN c_doctype dt ON c_doctypetarget_id = dt.c_doctype_id
  → dt.docbasetype: 'ARI'=factura o proforma (ambas comparten docbasetype),
                    'ARC'=nota de crédito
  → dt.name: distingue entre ProForma ('ProDolares', 'ProDolaresV', 'ProDolaresC',
             'Proforma') y Factura Legal ('AR Invoice Dolares', 'AR Invoice B/F/E',
             'Factura AGA', 'AR Invoice Dolares Valencia/Caracas'). Ver REGLA #8.

**c_bpartner** — Clientes/Proveedores/Empleados
Columnas: c_bpartner_id, name, value, iscustomer, isvendor, isemployee

**ad_user** — Vendedores (salesrep)
Columnas: ad_user_id, name (nombre del vendedor)
JOIN: c_invoice.salesrep_id = ad_user.ad_user_id

**ad_org** — Organizaciones del grupo Santoni
Columnas: ad_org_id, name, value
Orgs reales: INPROA SANTONI C.A., InproMaiz C.A, AGROINPROA C.A,
  AGROPECUARIA R.R. C.A., AGA AGRICOLA C.A, INVERSIONES AGA C.A, Santoni Service C.A

### Monedas
**c_currency** — Monedas
VES (Bolívares) = c_currency_id 205
USD (Dólares) = c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
Hay 9 IDs distintos para dólar porque iDempiere creó variantes (DOL, Dol, DoL, USA, dol, etc.)

### Cobranza
**c_payment** — Cobros y Pagos
Columnas: c_payment_id, c_bpartner_id, payamt, datetrx, c_currency_id,
  isreceipt ('Y'=cobro, 'N'=pago), docstatus, tendertype (método de pago)

### Cuentas por Cobrar / Antigüedad de Saldos (CxC aging)
IMPORTANTE — columnas que NO EXISTEN en c_invoice (errores comunes):
  - `i.duedate` NO existe. Calcular: `i.dateinvoiced + COALESCE(pt.netdays, 30)`
  - `i.netdays` NO existe. `netdays` vive en `c_paymentterm`.
  - NO existe tabla `c_invoicepayschedule` en uso — usar cálculo directo.

**c_paymentterm** — Términos de pago
Columnas: c_paymentterm_id, name, netdays (int — días hasta vencimiento), isdefault

**c_allocationhdr** — Cabecera de asignación pago→factura
Columnas: c_allocationhdr_id, dateacct, docstatus, isactive
  ⚠️ NO tiene columna `amount` ni `allocatedamt`.

**c_allocationline** — Líneas de asignación (montos aplicados)
Columnas: c_allocationline_id, c_allocationhdr_id, c_invoice_id, c_payment_id,
  amount (monto aplicado), discountamt (descuento), writeoffamt (write-off)
  ⚠️ El `amount` vive ACÁ (en line), NO en hdr.

**c_invoice** para CxC:
  - ispaid ('Y'/'N') — flag de pago completo
  - Saldo abierto = grandtotal − SUM(al.amount + al.discountamt + al.writeoffamt)
  - Fecha vencimiento = dateinvoiced + pt.netdays (JOIN a c_paymentterm)
  - Días vencido = CURRENT_DATE − (dateinvoiced + pt.netdays)

Patrón correcto para "facturas vencidas" o "antigüedad de saldos":
  LEFT JOIN c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id
  LEFT JOIN (SELECT c_invoice_id, SUM(amount+discountamt+writeoffamt) AS paid
             FROM c_allocationline al
             JOIN c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
             WHERE ah.isactive='Y' AND ah.docstatus IN ('CO','CL')
               AND ah.dateacct >= CURRENT_DATE - INTERVAL '3 years'
             GROUP BY c_invoice_id) alloc ON alloc.c_invoice_id = i.c_invoice_id
  Saldo abierto: (i.grandtotal - COALESCE(alloc.paid, 0))
  Días vencido: (CURRENT_DATE - (i.dateinvoiced + COALESCE(pt.netdays, 30)))
"""
