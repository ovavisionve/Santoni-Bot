-- ============================================================================
-- VERIFICACIÓN: Nuevas queries del agente de ventas
-- Fecha: 2026-03-26
-- Ejecutar contra: iDempiere producción (192.168.1.73:5432, DB idempiere_produccion)
-- Usuario: ova (read-only)
--
-- USO:
--   psql -h 192.168.1.73 -U ova -d idempiere_produccion -f scripts/verificar_nuevas_queries_ventas.sql
--
-- O desde el servidor SantoniBot:
--   docker compose exec db psql -h 192.168.1.73 -U ova -d idempiere_produccion \
--     -f /app/scripts/verificar_nuevas_queries_ventas.sql
-- ============================================================================

SET default_transaction_read_only = ON;

-- ============================================================================
-- 1. PRODUCTOS MÁS VENDIDOS - Año 2026 (Top 20, Bs.)
-- Función: build_sales_by_product
-- ============================================================================
\echo '============================================================'
\echo '1. TOP 20 PRODUCTOS MÁS VENDIDOS 2026 (Bs.)'
\echo '============================================================'

SELECT
    p.value AS codigo,
    p.name AS producto,
    COALESCE(pc.name, 'Sin Categoría') AS categoria,
    COALESCE(uom.name, '') AS unidad_medida,
    SUM(il.qtyinvoiced) AS cantidad,
    COALESCE(SUM(il.linenetamt), 0) AS total_neto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
LEFT JOIN adempiere.c_uom uom ON p.c_uom_id = uom.c_uom_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id = 205
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY p.value, p.name, pc.name, uom.name
ORDER BY total_neto DESC
LIMIT 20;

-- ============================================================================
-- 1b. PRODUCTOS MÁS VENDIDOS - Año 2026 (Top 20, USD)
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '1b. TOP 20 PRODUCTOS MÁS VENDIDOS 2026 (USD)'
\echo '============================================================'

SELECT
    p.value AS codigo,
    p.name AS producto,
    COALESCE(pc.name, 'Sin Categoría') AS categoria,
    SUM(il.qtyinvoiced) AS cantidad,
    COALESCE(SUM(il.linenetamt), 0) AS total_neto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY p.value, p.name, pc.name
ORDER BY total_neto DESC
LIMIT 20;

-- ============================================================================
-- 1c. TOTAL PRODUCTOS VENDIDOS - Resumen 2026
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '1c. RESUMEN TOTAL PRODUCTOS VENDIDOS 2026'
\echo '============================================================'

SELECT
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
         WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
         ELSE 'Otro' END AS moneda,
    COUNT(DISTINCT p.m_product_id) AS productos_distintos,
    SUM(il.qtyinvoiced) AS cantidad_total,
    COALESCE(SUM(il.linenetamt), 0) AS total_neto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
              WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
              ELSE 'Otro' END
ORDER BY total_neto DESC;

-- ============================================================================
-- 2. ÓRDENES DE VENTA PENDIENTES - 2026
-- Función: build_sales_orders
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '2. ÓRDENES DE VENTA 2026 (por estado)'
\echo '============================================================'

SELECT
    CASE o.docstatus
        WHEN 'DR' THEN 'Borrador'
        WHEN 'IP' THEN 'En Proceso'
        WHEN 'CO' THEN 'Completada'
        WHEN 'CL' THEN 'Cerrada'
        ELSE o.docstatus
    END AS estado,
    COUNT(*) AS ordenes,
    COALESCE(SUM(o.grandtotal), 0) AS total
FROM adempiere.c_order o
WHERE o.issotrx = 'Y'
  AND o.docstatus IN ('DR', 'IP', 'CO', 'CL')
  AND o.isactive = 'Y'
  AND o.dateordered >= '2026-01-01'
  AND o.dateordered <= '2026-12-31'
GROUP BY o.docstatus
ORDER BY total DESC;

-- ============================================================================
-- 2b. ÓRDENES PENDIENTES (solo DR + IP)
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '2b. ÓRDENES DE VENTA PENDIENTES 2026 (DR + IP)'
\echo '============================================================'

SELECT
    CASE o.docstatus
        WHEN 'DR' THEN 'Borrador'
        WHEN 'IP' THEN 'En Proceso'
        ELSE o.docstatus
    END AS estado,
    COUNT(*) AS ordenes,
    COALESCE(SUM(o.grandtotal), 0) AS total
FROM adempiere.c_order o
WHERE o.issotrx = 'Y'
  AND o.docstatus IN ('DR', 'IP')
  AND o.isactive = 'Y'
  AND o.dateordered >= '2026-01-01'
  AND o.dateordered <= '2026-12-31'
GROUP BY o.docstatus
ORDER BY total DESC;

-- ============================================================================
-- 2c. ÓRDENES POR ORGANIZACIÓN
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '2c. ÓRDENES DE VENTA 2026 POR ORGANIZACIÓN'
\echo '============================================================'

SELECT
    org.name AS organizacion,
    CASE o.docstatus
        WHEN 'DR' THEN 'Borrador'
        WHEN 'IP' THEN 'En Proceso'
        WHEN 'CO' THEN 'Completada'
        WHEN 'CL' THEN 'Cerrada'
        ELSE o.docstatus
    END AS estado,
    COUNT(*) AS ordenes,
    COALESCE(SUM(o.grandtotal), 0) AS total
FROM adempiere.c_order o
JOIN adempiere.ad_org org ON o.ad_org_id = org.ad_org_id
WHERE o.issotrx = 'Y'
  AND o.docstatus IN ('DR', 'IP', 'CO', 'CL')
  AND o.isactive = 'Y'
  AND o.dateordered >= '2026-01-01'
  AND o.dateordered <= '2026-12-31'
GROUP BY org.name, o.docstatus
ORDER BY org.name, total DESC;

-- ============================================================================
-- 3. VENTAS POR SUCURSAL (c_project) - 2026
-- Función: build_sales_by_branch
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '3. VENTAS POR SUCURSAL 2026 (Bs., Top 20)'
\echo '============================================================'

SELECT
    COALESCE(pj.name, 'Sin Sucursal') AS sucursal,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                      WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal
                      ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_project pj ON i.c_project_id = pj.c_project_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.c_currency_id = 205
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY pj.name
ORDER BY venta_neta DESC
LIMIT 20;

-- ============================================================================
-- 3b. VENTAS POR SUCURSAL (USD)
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '3b. VENTAS POR SUCURSAL 2026 (USD, Top 20)'
\echo '============================================================'

SELECT
    COALESCE(pj.name, 'Sin Sucursal') AS sucursal,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                      WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal
                      ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_project pj ON i.c_project_id = pj.c_project_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY pj.name
ORDER BY venta_neta DESC
LIMIT 20;

-- ============================================================================
-- 4. IMPUESTOS / IVA - 2026
-- Función: build_sales_tax_summary
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '4. RESUMEN DE IMPUESTOS (IVA) 2026 - Bs.'
\echo '============================================================'

SELECT
    COALESCE(t.name, 'Sin Impuesto') AS impuesto,
    COALESCE(t.rate, 0) AS tasa_porcentaje,
    COUNT(DISTINCT i.c_invoice_id) AS facturas,
    COALESCE(SUM(il.linenetamt), 0) AS base_imponible,
    COALESCE(SUM(il.linenetamt * t.rate / 100), 0) AS monto_impuesto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
LEFT JOIN adempiere.c_tax t ON il.c_tax_id = t.c_tax_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id = 205
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY t.name, t.rate
ORDER BY monto_impuesto DESC;

-- ============================================================================
-- 4b. IMPUESTOS / IVA - 2026 USD
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '4b. RESUMEN DE IMPUESTOS (IVA) 2026 - USD'
\echo '============================================================'

SELECT
    COALESCE(t.name, 'Sin Impuesto') AS impuesto,
    COALESCE(t.rate, 0) AS tasa_porcentaje,
    COUNT(DISTINCT i.c_invoice_id) AS facturas,
    COALESCE(SUM(il.linenetamt), 0) AS base_imponible,
    COALESCE(SUM(il.linenetamt * t.rate / 100), 0) AS monto_impuesto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
LEFT JOIN adempiere.c_tax t ON il.c_tax_id = t.c_tax_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
GROUP BY t.name, t.rate
ORDER BY monto_impuesto DESC;

-- ============================================================================
-- 4c. RETENCIONES (withholdingamt) - 2026
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '4c. RETENCIONES 2026 (withholdingamt en c_invoice)'
\echo '============================================================'

SELECT
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
         WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
         ELSE 'Otro' END AS moneda,
    COUNT(*) AS facturas_con_retencion,
    COALESCE(SUM(i.withholdingamt), 0) AS total_retenciones
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-12-31'
  AND COALESCE(i.withholdingamt, 0) != 0
GROUP BY CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
              WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
              ELSE 'Otro' END;

-- ============================================================================
-- 5. TASAS DE CAMBIO - Últimas 20
-- Función: build_exchange_rates
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '5. ÚLTIMAS 20 TASAS DE CAMBIO'
\echo '============================================================'

SELECT
    cf.iso_code AS moneda_origen,
    ct.iso_code AS moneda_destino,
    cr.multiplyrate AS tasa_multiplicar,
    cr.dividerate AS tasa_dividir,
    cr.validfrom AS vigente_desde,
    cr.validto AS vigente_hasta
FROM adempiere.c_conversion_rate cr
JOIN adempiere.c_currency cf ON cr.c_currency_id = cf.c_currency_id
JOIN adempiere.c_currency ct ON cr.c_currency_id_to = ct.c_currency_id
WHERE cr.isactive = 'Y'
ORDER BY cr.validfrom DESC
LIMIT 20;

-- ============================================================================
-- 5b. ¿EXISTE c_conversion_rate con datos recientes?
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '5b. CONTEO TASAS DE CAMBIO POR AÑO'
\echo '============================================================'

SELECT
    EXTRACT(YEAR FROM cr.validfrom) AS anio,
    COUNT(*) AS registros
FROM adempiere.c_conversion_rate cr
WHERE cr.isactive = 'Y'
GROUP BY EXTRACT(YEAR FROM cr.validfrom)
ORDER BY anio DESC
LIMIT 10;

-- ============================================================================
-- 5c. TASAS DE CAMBIO 2026
-- ============================================================================
\echo ''
\echo '============================================================'
\echo '5c. TASAS DE CAMBIO 2026 (todas)'
\echo '============================================================'

SELECT
    cf.iso_code AS moneda_origen,
    ct.iso_code AS moneda_destino,
    cr.multiplyrate AS tasa_multiplicar,
    cr.dividerate AS tasa_dividir,
    cr.validfrom AS vigente_desde,
    cr.validto AS vigente_hasta
FROM adempiere.c_conversion_rate cr
JOIN adempiere.c_currency cf ON cr.c_currency_id = cf.c_currency_id
JOIN adempiere.c_currency ct ON cr.c_currency_id_to = ct.c_currency_id
WHERE cr.isactive = 'Y'
  AND cr.validfrom >= '2026-01-01'
ORDER BY cr.validfrom DESC;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================
\echo ''
\echo '============================================================'
\echo 'VERIFICACIÓN COMPLETADA'
\echo 'Copiar estos resultados al documento:'
\echo '  docs/DATOS_VERIFICACION_IDEMPIERE.md'
\echo '============================================================'
