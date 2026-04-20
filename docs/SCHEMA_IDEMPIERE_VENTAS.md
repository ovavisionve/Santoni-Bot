# Schema iDempiere — Referencia autoritativa de Ventas

> Fuente: Ing. Geovanna Antonieta Quintero Timaure (admin iDempiere Santoni).
> Este documento es la referencia de verdad para TODAS las queries de ventas
> del bot y del runner de QA. Cuando haya ambigüedad, gana lo que dice acá.

## Tablas principales

| Tabla | Descripción | Campo clave para ventas |
|-------|-------------|-------------------------|
| `c_order` | Orden de venta | `issotrx='Y'` |
| `c_orderline` | Línea de orden | — |
| `c_invoice` | Factura | `issotrx='Y'` |
| `c_invoiceline` | Línea de factura | — |
| `m_pricelist` | Lista de precios | — |
| `m_productprice` | Productos asociados a lista | — |
| `m_product_category` | Categorías de producto | `iskpi='Y'` = SKU |
| `m_product` | Producto | — |
| `c_uom` | Unidad de medida | — |
| `c_conversion_rate` | Tasa de cambio | — |
| `c_payment` | Cobros y pagos | `isreceipt='Y'` = cobro |
| `c_allocationline` | Pagos asignados a factura | — |
| `c_bpartner` | Tercero | `iscustomer='Y'`, `isvendor='Y'`, `isemployee='Y'` |
| `c_bpartner_location` | Dirección cliente | — |
| `c_project` | **Sucursales** | — |
| `c_salesregion` | Región de ventas | — |
| `dcs_salesregiongroup` | Grupo de regiones | — |
| `c_tax` | Impuestos | — |
| `ad_user` | Usuario (para vendedor) | — |

## Reglas críticas

### 1. Distinguir ventas vs. compras
```sql
WHERE issotrx = 'Y'   -- ventas
WHERE issotrx = 'N'   -- compras
```

### 2. Moneda
```sql
c_currency_id = 205     -- Bs. (Bolívares / VES)
c_currency_id <> 205    -- USD / moneda extranjera (cualquier otro ID)
```

En Santoni cada organización registró su propia entrada de USD con iso_code
distinto (DOL, DoL, Dol, USA, dol, DLA, Dla, US., USD, etc). IDs conocidos:
**100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017**.
Todos representan dólares americanos — agruparlos bajo 'USD'.

### 3. Vendedor
El vendedor está en `c_order.salesrep_id` y `c_invoice.salesrep_id`.
Para el nombre se hace JOIN con `ad_user.ad_user_id`.

### 4. SKU vs productos genéricos
```sql
WHERE m_product_category.iskpi = 'Y'  -- SKU (productos de venta oficial)
```

### 5. Cobros (vs pagos a proveedores)
```sql
WHERE c_payment.isreceipt = 'Y'   -- cobro de cliente
WHERE c_payment.isreceipt = 'N'   -- pago a proveedor
```

### 6. Cliente / Proveedor / Empleado
```sql
WHERE c_bpartner.iscustomer = 'Y'  -- cliente
WHERE c_bpartner.isvendor = 'Y'    -- proveedor
WHERE c_bpartner.isemployee = 'Y'  -- empleado
```

Un mismo bpartner puede tener múltiples flags (ej. ser cliente y proveedor
simultáneamente).

## Joins típicos

### Factura con vendedor, cliente y sucursal
```sql
SELECT i.documentno, i.grandtotal, i.c_currency_id,
       bp.name AS cliente,
       u.name AS vendedor,
       pj.name AS sucursal
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.ad_user u ON i.salesrep_id = u.ad_user_id
LEFT JOIN adempiere.c_project pj ON i.c_project_id = pj.c_project_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
```

### Cobro asignado a facturas
```sql
SELECT p.payamt, p.datetrx,
       i.documentno AS factura,
       al.amount AS monto_asignado
FROM adempiere.c_payment p
LEFT JOIN adempiere.c_allocationline al ON al.c_payment_id = p.c_payment_id
LEFT JOIN adempiere.c_invoice i ON al.c_invoice_id = i.c_invoice_id
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
```

### Venta por sucursal y región
```sql
SELECT pj.name AS sucursal,
       sr.name AS region,
       SUM(i.grandtotal) AS total
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_project pj ON i.c_project_id = pj.c_project_id
LEFT JOIN adempiere.c_bpartner_location bpl
       ON i.c_bpartner_location_id = bpl.c_bpartner_location_id
LEFT JOIN adempiere.c_salesregion sr ON bpl.c_salesregion_id = sr.c_salesregion_id
WHERE i.issotrx = 'Y'
GROUP BY pj.name, sr.name
```

## Doc types (c_doctype)

El `c_invoice` puede ser factura (ARI) o nota de crédito (ARC). Para ventas
netas, restar las ARC:

```sql
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE dt.docbasetype = 'ARI'  -- factura de cliente (venta)
   OR dt.docbasetype = 'ARC'  -- nota de crédito (descontar)
```

Para totales netos:
```sql
SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
         WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal
         ELSE 0 END) AS venta_neta
```

## Estados de documento

- `DR` = Draft (borrador)
- `IP` = In Progress (en proceso)
- `CO` = Completed (completado)
- `CL` = Closed (cerrado)
- `RE` = Reversed (reversado)
- `VO` = Voided (anulado)

Para totales de ventas: `docstatus IN ('CO', 'CL')`.

## Notas de integración

- El campo `i.ispaid` indica si una factura está pagada (flag, no calculado).
- `i.totalpaid` **NO existe** — no intentar usarlo. Calcular pagado via
  `c_allocationline` si se necesita el detalle exacto.
- El campo `i.totallines` es la suma de `c_invoiceline.linenetamt` antes de
  impuestos. `i.grandtotal` incluye impuestos.
- Los "demo orgs" (ad_org_id 0, 11-16 en el iDempiere de prueba) no
  existen necesariamente en producción. No filtrarlos por default — solo
  cuando el usuario lo pida explícitamente.
