-- ============================================================
-- VERIFICACIÓN COMPLETA DE VENTAS - AÑO 2024 y 2025
-- Ejecutar contra iDempiere: psql -h 192.168.1.73 -U ova -d idempiere_produccion
-- ============================================================
-- Replica EXACTA de las queries del bot (build_sales_summary,
-- build_top_clients, build_collection_summary, build_overdue_receivables)
-- ============================================================

-- =============================================
-- PARTE A: VENTAS / FACTURACIÓN (c_invoice)
-- =============================================

-- A1. TOTALES DE FACTURACIÓN 2024 (solo facturas ARI, sin notas de crédito)
SELECT '--- AÑO 2024 ---' AS periodo;
SELECT
    COUNT(*) AS total_facturas,
    COALESCE(SUM(i.grandtotal), 0) AS total_facturado,
    COALESCE(SUM(i.totallines), 0) AS total_neto,
    COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.dateinvoiced >= '2024-01-01'
  AND i.dateinvoiced <= '2024-12-31';

-- A2. NOTAS DE CRÉDITO 2024 (ARC)
SELECT
    COUNT(*) AS total_notas_credito,
    COALESCE(SUM(i.grandtotal), 0) AS monto_notas_credito
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARC'
  AND i.dateinvoiced >= '2024-01-01'
  AND i.dateinvoiced <= '2024-12-31';

-- A3. TOTALES DE FACTURACIÓN 2025
SELECT '--- AÑO 2025 ---' AS periodo;
SELECT
    COUNT(*) AS total_facturas,
    COALESCE(SUM(i.grandtotal), 0) AS total_facturado,
    COALESCE(SUM(i.totallines), 0) AS total_neto,
    COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31';

-- A4. NOTAS DE CRÉDITO 2025
SELECT
    COUNT(*) AS total_notas_credito,
    COALESCE(SUM(i.grandtotal), 0) AS monto_notas_credito
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARC'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31';

-- A5. DESGLOSE POR MES 2024 (venta neta = facturas - NC)
SELECT '--- VENTAS POR MES 2024 ---' AS seccion;
SELECT
    EXTRACT(YEAR FROM i.dateinvoiced)::int AS anio,
    EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2024-01-01'
  AND i.dateinvoiced <= '2024-12-31'
GROUP BY EXTRACT(YEAR FROM i.dateinvoiced), EXTRACT(MONTH FROM i.dateinvoiced)
ORDER BY anio, mes;

-- A6. DESGLOSE POR MES 2025 (venta neta)
SELECT '--- VENTAS POR MES 2025 ---' AS seccion;
SELECT
    EXTRACT(YEAR FROM i.dateinvoiced)::int AS anio,
    EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY EXTRACT(YEAR FROM i.dateinvoiced), EXTRACT(MONTH FROM i.dateinvoiced)
ORDER BY anio, mes;

-- A7. POR MONEDA 2025 (usa el mismo CASE que el bot para agrupar USD)
SELECT '--- VENTAS POR MONEDA 2025 ---' AS seccion;
SELECT
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END AS moneda,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY CASE
    WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
    WHEN i.c_currency_id = 205 THEN 'Bs.'
    ELSE 'Otro'
END
ORDER BY venta_neta DESC;

-- A8. POR MONEDA 2024
SELECT '--- VENTAS POR MONEDA 2024 ---' AS seccion;
SELECT
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END AS moneda,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2024-01-01'
  AND i.dateinvoiced <= '2024-12-31'
GROUP BY CASE
    WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
    WHEN i.c_currency_id = 205 THEN 'Bs.'
    ELSE 'Otro'
END
ORDER BY venta_neta DESC;

-- A9. POR ZONA (c_salesregion) 2025 - Top 20
SELECT '--- VENTAS POR ZONA 2025 ---' AS seccion;
WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT
    COALESCE(cz.zona_name, 'Sin Zona') AS zona,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_bruto,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
LEFT JOIN client_zone cz ON i.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY cz.zona_name
ORDER BY venta_neta DESC
LIMIT 20;

-- A10. POR ORGANIZACIÓN 2025
SELECT '--- VENTAS POR ORGANIZACIÓN 2025 ---' AS seccion;
SELECT
    org.name AS organizacion,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.ad_org org ON i.ad_org_id = org.ad_org_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY org.name
ORDER BY venta_neta DESC;

-- A11. POR DISTRIBUIDOR 2025 - Top 20
SELECT '--- VENTAS POR DISTRIBUIDOR 2025 ---' AS seccion;
SELECT
    COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY sr.name
ORDER BY venta_neta DESC
LIMIT 20;

-- =============================================
-- PARTE B: TOP CLIENTES (build_top_clients)
-- =============================================

-- B1. TOP 20 CLIENTES 2025 (venta neta = facturas - NC)
SELECT '--- TOP 20 CLIENTES 2025 ---' AS seccion;
WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT
    bp.value AS codigo,
    bp.name AS nombre,
    COALESCE(cz.zona_name, 'Sin Zona') AS zona,
    COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor,
    COALESCE(bpg.name, 'Sin Tipología') AS tipologia,
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END AS moneda,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total_facturado
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
LEFT JOIN adempiere.c_bp_group bpg ON bp.c_bp_group_id = bpg.c_bp_group_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY bp.value, bp.name, cz.zona_name, sr.name, bpg.name,
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END
ORDER BY total_facturado DESC
LIMIT 20;

-- B2. TOP 20 CLIENTES 2024
SELECT '--- TOP 20 CLIENTES 2024 ---' AS seccion;
WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT
    bp.value AS codigo,
    bp.name AS nombre,
    COALESCE(cz.zona_name, 'Sin Zona') AS zona,
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END AS moneda,
    SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
    COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
        WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total_facturado
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2024-01-01'
  AND i.dateinvoiced <= '2024-12-31'
GROUP BY bp.value, bp.name, cz.zona_name,
    CASE
        WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
        WHEN i.c_currency_id = 205 THEN 'Bs.'
        ELSE 'Otro'
    END
ORDER BY total_facturado DESC
LIMIT 20;

-- =============================================
-- PARTE C: COBRANZA (c_payment)
-- =============================================

-- C1. TOTALES COBRANZA 2025
SELECT '--- COBRANZA 2025 ---' AS seccion;
SELECT
    COUNT(*) AS total_recibos,
    COALESCE(SUM(p.payamt), 0) AS total_cobrado
FROM adempiere.c_payment p
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
  AND p.isactive = 'Y'
  AND p.datetrx >= '2025-01-01'
  AND p.datetrx <= '2025-12-31';

-- C2. TOTALES COBRANZA 2024
SELECT '--- COBRANZA 2024 ---' AS seccion;
SELECT
    COUNT(*) AS total_recibos,
    COALESCE(SUM(p.payamt), 0) AS total_cobrado
FROM adempiere.c_payment p
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
  AND p.isactive = 'Y'
  AND p.datetrx >= '2024-01-01'
  AND p.datetrx <= '2024-12-31';

-- C3. COBRANZA POR MÉTODO DE PAGO 2025
SELECT '--- COBRANZA POR MÉTODO 2025 ---' AS seccion;
SELECT
    CASE p.tendertype
        WHEN 'X' THEN 'Transferencia'
        WHEN 'C' THEN 'Cheque'
        WHEN 'K' THEN 'Efectivo'
        WHEN 'D' THEN 'Depósito'
        WHEN 'T' THEN 'Tarjeta'
        ELSE p.tendertype
    END AS metodo_pago,
    COUNT(*) AS recibos,
    COALESCE(SUM(p.payamt), 0) AS total
FROM adempiere.c_payment p
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
  AND p.isactive = 'Y'
  AND p.datetrx >= '2025-01-01'
  AND p.datetrx <= '2025-12-31'
GROUP BY p.tendertype
ORDER BY total DESC;

-- C4. TOP 20 CLIENTES POR COBRANZA 2025
SELECT '--- TOP 20 COBRANZA POR CLIENTE 2025 ---' AS seccion;
SELECT
    bp.name AS cliente,
    COUNT(*) AS recibos,
    COALESCE(SUM(p.payamt), 0) AS total
FROM adempiere.c_payment p
JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
  AND p.isactive = 'Y'
  AND p.datetrx >= '2025-01-01'
  AND p.datetrx <= '2025-12-31'
GROUP BY bp.name
ORDER BY total DESC
LIMIT 20;

-- C5. COBRANZA POR MES 2025
SELECT '--- COBRANZA POR MES 2025 ---' AS seccion;
SELECT
    EXTRACT(YEAR FROM p.datetrx)::int AS anio,
    EXTRACT(MONTH FROM p.datetrx)::int AS mes,
    COUNT(*) AS recibos,
    COALESCE(SUM(p.payamt), 0) AS total_cobrado
FROM adempiere.c_payment p
WHERE p.isreceipt = 'Y'
  AND p.docstatus IN ('CO', 'CL')
  AND p.isactive = 'Y'
  AND p.datetrx >= '2025-01-01'
  AND p.datetrx <= '2025-12-31'
GROUP BY EXTRACT(YEAR FROM p.datetrx), EXTRACT(MONTH FROM p.datetrx)
ORDER BY anio, mes;

-- =============================================
-- PARTE D: CUENTAS POR COBRAR VENCIDAS
-- =============================================

-- D1. TOP 30 FACTURAS VENCIDAS (ispaid='N', últimos 3 años, monto > 100)
SELECT '--- CUENTAS POR COBRAR VENCIDAS ---' AS seccion;
WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT
    i.documentno AS numero_factura,
    bp.name AS cliente,
    COALESCE(cz.zona_name, '') AS zona,
    i.grandtotal AS monto_total,
    i.dateinvoiced AS fecha,
    (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END)::date AS fecha_vencimiento,
    CURRENT_DATE - (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) AS dias_vencido
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.ispaid = 'N'
  AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years')
  AND i.grandtotal > 100
  AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE
ORDER BY dias_vencido DESC
LIMIT 30;

-- =============================================
-- PARTE E: VERIFICACIÓN DE DOCSTATUS
-- =============================================

-- E1. ¿Hay facturas de venta con otros docstatus?
SELECT '--- DOCSTATUS DE FACTURAS 2025 ---' AS seccion;
SELECT
    i.docstatus,
    COUNT(*) AS cantidad
FROM adempiere.c_invoice i
WHERE i.issotrx = 'Y'
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY i.docstatus
ORDER BY cantidad DESC;

-- E2. ¿Hay pagos con otros docstatus?
SELECT '--- DOCSTATUS DE PAGOS 2025 ---' AS seccion;
SELECT
    p.docstatus,
    COUNT(*) AS cantidad
FROM adempiere.c_payment p
WHERE p.isreceipt = 'Y'
  AND p.isactive = 'Y'
  AND p.datetrx >= '2025-01-01'
  AND p.datetrx <= '2025-12-31'
GROUP BY p.docstatus
ORDER BY cantidad DESC;

-- E3. Tipos de documento (docbasetype) presentes en facturas de venta
SELECT '--- TIPOS DE DOCUMENTO EN FACTURAS 2025 ---' AS seccion;
SELECT
    dt.docbasetype,
    dt.name AS tipo_documento,
    COUNT(*) AS cantidad
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY dt.docbasetype, dt.name
ORDER BY cantidad DESC;

-- E4. Monedas usadas en facturas de venta 2025 (verificar IDs de USD)
SELECT '--- MONEDAS EN FACTURAS 2025 ---' AS seccion;
SELECT
    c.iso_code,
    c.c_currency_id,
    c.cursymbol,
    COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2025-01-01'
  AND i.dateinvoiced <= '2025-12-31'
GROUP BY c.iso_code, c.c_currency_id, c.cursymbol
ORDER BY facturas DESC;

-- E5. Zonas de venta registradas (c_salesregion)
SELECT '--- ZONAS DE VENTA EN IDEMPIERE ---' AS seccion;
SELECT
    sreg.name AS zona,
    sreg.c_salesregion_id,
    COUNT(DISTINCT bpl.c_bpartner_id) AS clientes_asignados
FROM adempiere.c_salesregion sreg
LEFT JOIN adempiere.c_bpartner_location bpl ON sreg.c_salesregion_id = bpl.c_salesregion_id AND bpl.isactive = 'Y'
WHERE sreg.isactive = 'Y'
GROUP BY sreg.name, sreg.c_salesregion_id
ORDER BY clientes_asignados DESC;

-- E6. Tipologías de clientes (c_bp_group)
SELECT '--- TIPOLOGÍAS DE CLIENTES ---' AS seccion;
SELECT
    bpg.name AS tipologia,
    COUNT(DISTINCT bp.c_bpartner_id) AS clientes
FROM adempiere.c_bp_group bpg
LEFT JOIN adempiere.c_bpartner bp ON bpg.c_bp_group_id = bp.c_bp_group_id AND bp.isactive = 'Y'
WHERE bpg.isactive = 'Y'
GROUP BY bpg.name
ORDER BY clientes DESC;
