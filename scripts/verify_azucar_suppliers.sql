-- =============================================================
-- VERIFICACIÓN: Proveedores que venden azúcar en iDempiere
-- Replica exacta de build_supplier_price_comparison() con
-- product_search='azucar'
-- =============================================================

-- Query 1: Comparación de precios por proveedor (lo que el bot ejecuta)
SELECT
    bp.name AS proveedor,
    p.name AS producto,
    p.value AS codigo_producto,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
         WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
         THEN 'USD' ELSE 'Otro' END AS moneda,
    COUNT(*) AS compras,
    MIN(il.priceactual) AS precio_minimo,
    AVG(il.priceactual) AS precio_promedio,
    MAX(il.priceactual) AS precio_maximo,
    MAX(i.dateinvoiced) AS ultima_compra,
    SUM(il.qtyinvoiced) AS cantidad_total,
    SUM(il.linenetamt) AS monto_total
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'N'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND (p.name ILIKE '%azucar%' OR p.value ILIKE '%azucar%')
GROUP BY bp.name, p.name, p.value,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
         WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
         THEN 'USD' ELSE 'Otro' END
ORDER BY moneda, precio_promedio ASC;

-- Query 2: Detalle de TODAS las facturas de azúcar (para ver cada compra individual)
SELECT
    bp.name AS proveedor,
    p.name AS producto,
    p.value AS codigo_producto,
    i.documentno AS factura,
    i.dateinvoiced AS fecha,
    il.qtyinvoiced AS cantidad,
    il.priceactual AS precio_unitario,
    il.linenetamt AS total_linea,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
         WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
         THEN 'USD' ELSE 'Otro' END AS moneda,
    o.name AS organizacion
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
WHERE i.issotrx = 'N'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND (p.name ILIKE '%azucar%' OR p.value ILIKE '%azucar%')
ORDER BY i.dateinvoiced DESC
LIMIT 50;

-- Query 3: Todos los productos que contienen "azucar" en el catálogo
SELECT
    p.value AS codigo,
    p.name AS producto,
    pc.name AS categoria,
    p.isactive
FROM adempiere.m_product p
LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
WHERE p.name ILIKE '%azucar%' OR p.value ILIKE '%azucar%'
ORDER BY p.name;
