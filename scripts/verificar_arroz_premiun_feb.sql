-- Verificar ventas de ARROZ SANTONI PREMIUN en febrero 2026
-- Ejecutar: psql -h 192.168.1.73 -U ova -d idempiere_produccion -f scripts/verificar_arroz_premiun_feb.sql

\echo '=== ARROZ SANTONI PREMIUN - Febrero 2026 (solo facturas ARI, sin NC) ==='
SELECT
    p.value AS codigo,
    p.name AS producto,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.' ELSE 'USD' END AS moneda,
    COUNT(DISTINCT i.c_invoice_id) AS facturas,
    SUM(il.qtyinvoiced) AS bultos,
    SUM(il.linenetamt) AS total_neto
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND p.value = '-010180I'
  AND i.dateinvoiced >= '2026-02-01'
  AND i.dateinvoiced < '2026-03-01'
GROUP BY p.value, p.name, CASE WHEN i.c_currency_id = 205 THEN 'Bs.' ELSE 'USD' END
ORDER BY moneda;

\echo ''
\echo '=== NOTAS DE CREDITO (ARC) para ARROZ PREMIUN - Febrero 2026 ==='
SELECT
    p.value AS codigo,
    p.name AS producto,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.' ELSE 'USD' END AS moneda,
    COUNT(DISTINCT i.c_invoice_id) AS notas_credito,
    SUM(il.qtyinvoiced) AS bultos_nc,
    SUM(il.linenetamt) AS monto_nc
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARC'
  AND p.value = '-010180I'
  AND i.dateinvoiced >= '2026-02-01'
  AND i.dateinvoiced < '2026-03-01'
GROUP BY p.value, p.name, CASE WHEN i.c_currency_id = 205 THEN 'Bs.' ELSE 'USD' END
ORDER BY moneda;

\echo ''
\echo '=== NOTAS DE CREDITO (ARC) para ARROZ PREMIUN - Despues del 04/03/2026 ==='
SELECT
    i.documentno,
    i.dateinvoiced,
    CASE WHEN i.c_currency_id = 205 THEN 'Bs.' ELSE 'USD' END AS moneda,
    il.qtyinvoiced AS bultos,
    il.linenetamt AS monto,
    bp.name AS cliente
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARC'
  AND p.value = '-010180I'
  AND i.dateinvoiced >= '2026-03-04'
ORDER BY i.dateinvoiced;

\echo ''
\echo '=== VENDEDORES USD Febrero 2026 (con y sin NC) ==='
SELECT
    COALESCE(sr.name, 'Sin Vendedor') AS vendedor,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END), 0) AS total_bruto,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.totallines ELSE 0 END), 0) AS total_nc,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                      WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_neto
FROM adempiere.c_invoice i
LEFT JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.c_currency_id != 205
  AND i.dateinvoiced >= '2026-02-01'
  AND i.dateinvoiced < '2026-03-01'
GROUP BY sr.name
ORDER BY total_neto DESC
LIMIT 10;
