-- =============================================================================
-- DIAGNÓSTICO: Top vendedores febrero 2026 — comparar bot vs Excel de Darwin
-- =============================================================================
-- Objetivo: identificar por qué el bot muestra ~57% menos de lo que Darwin ve
-- en su Excel. Probables causas: filtro de organización, moneda, docstatus,
-- o conversión VES→USD que el bot no hace.
--
-- Correr EN iDempiere (192.168.1.73:5432, DB idempiere_produccion) como
-- usuario 'ova' o cualquiera con SELECT.
-- =============================================================================

-- Prep: ID set que el bot usa para USD
-- (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)

-- -----------------------------------------------------------------------------
-- CONSULTA 1: Top 10 vendedores USD, SOLO INPROA SANTONI — así hace el bot hoy
-- -----------------------------------------------------------------------------
SELECT '1. Bot (INPROA SANTONI, USD)' AS diagnostico;
SELECT
    COALESCE(sr.name, 'Sin Vendedor') AS vendedor,
    COUNT(*) FILTER (WHERE dt.docbasetype = 'ARI') AS facturas,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END)::numeric, 2) AS bruto_totallines,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END)::numeric, 2) AS bruto_grandtotal
FROM adempiere.c_invoice i
LEFT JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND o.name ILIKE '%inproa santoni%'
  AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
GROUP BY sr.name
ORDER BY bruto_totallines DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- CONSULTA 2: Top 10 vendedores USD, TODAS las organizaciones
-- -----------------------------------------------------------------------------
SELECT '2. Todas las orgs (USD)' AS diagnostico;
SELECT
    COALESCE(sr.name, 'Sin Vendedor') AS vendedor,
    COUNT(*) FILTER (WHERE dt.docbasetype = 'ARI') AS facturas,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END)::numeric, 2) AS bruto_totallines,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END)::numeric, 2) AS bruto_grandtotal
FROM adempiere.c_invoice i
LEFT JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
GROUP BY sr.name
ORDER BY bruto_totallines DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- CONSULTA 3: Desglose por organización — ver en cuáles hay ventas
-- -----------------------------------------------------------------------------
SELECT '3. Facturas USD por organización feb-2026' AS diagnostico;
SELECT
    o.name AS organizacion,
    COUNT(*) FILTER (WHERE dt.docbasetype = 'ARI') AS facturas,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END)::numeric, 2) AS total_usd
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
GROUP BY o.name
ORDER BY total_usd DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 4: ANTONINO RUSSO específicamente — ver cada factura
-- -----------------------------------------------------------------------------
SELECT '4. ANTONINO RUSSO - facturas individuales feb-2026 USD' AS diagnostico;
SELECT
    i.documentno,
    o.name AS org,
    i.dateinvoiced::date AS fecha,
    dt.docbasetype,
    i.docstatus,
    c.iso_code AS moneda,
    i.c_currency_id,
    ROUND(i.totallines::numeric, 2) AS totallines,
    ROUND(i.grandtotal::numeric, 2) AS grandtotal
FROM adempiere.c_invoice i
JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
LEFT JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
WHERE i.issotrx = 'Y'
  AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND sr.name ILIKE '%antonino%russo%'
  AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
ORDER BY i.dateinvoiced, i.documentno;

-- -----------------------------------------------------------------------------
-- CONSULTA 5: ANTONINO RUSSO — incluye TODAS las monedas para detectar VES
-- -----------------------------------------------------------------------------
SELECT '5. ANTONINO RUSSO - feb-2026 TODAS las monedas' AS diagnostico;
SELECT
    c.iso_code AS moneda,
    i.c_currency_id,
    COUNT(*) FILTER (WHERE dt.docbasetype = 'ARI') AS facturas,
    ROUND(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END)::numeric, 2) AS total
FROM adempiere.c_invoice i
JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
LEFT JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND sr.name ILIKE '%antonino%russo%'
GROUP BY c.iso_code, i.c_currency_id
ORDER BY total DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 6: docstatus de las facturas — ver si hay estados distintos a CO/CL
-- -----------------------------------------------------------------------------
SELECT '6. docstatus de facturas de venta feb-2026' AS diagnostico;
SELECT
    i.docstatus,
    COUNT(*) AS facturas,
    ROUND(SUM(i.totallines)::numeric, 2) AS total_totallines,
    ROUND(SUM(i.grandtotal)::numeric, 2) AS total_grandtotal
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
GROUP BY i.docstatus
ORDER BY facturas DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 7: Usuario admin del bot — qué org_ids tiene configurado
-- -----------------------------------------------------------------------------
-- CORRER EN LA DB LOCAL DE SANTONIBOT (santonibot_db), NO EN iDempiere:
-- SELECT username, email, allowed_org_ids FROM users WHERE username = 'admin';
