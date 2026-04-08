-- ============================================================================
-- VERIFICACIÓN DIRECTA: 34 preguntas del test admin contra iDempiere
-- Ejecutar contra: 192.168.1.73:5432 / idempiere_produccion / schema adempiere
-- Usuario: ova (read-only)
--
-- Cada query corresponde a una pregunta del test_admin_conversation_live.py
-- Si devuelve filas → el bot SÍ tiene acceso a esa data
--
-- Alineación con idempiere_queries.py (Abr 2026):
--   * docstatus IN ('CO', 'CL')  — incluye Completed y Closed (facturas pagadas
--     pasan a CL en iDempiere)
--   * Ventas: usa i.totallines (sin IVA) en vez de i.grandtotal
--   * CxC/CxP: usa (i.grandtotal - abonos_parciales) — patrón _OPEN_EXPR
-- ============================================================================

-- ═══════════════════════════════════════════════════════════════════════
-- VENTAS (11 preguntas)
-- ═══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 1: "Top 10 clientes de este mes" (marzo 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 1: Top 10 clientes de este mes (marzo 2026) ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT bp.name AS cliente,
       COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END) AS total_neto,
       COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 3
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
GROUP BY bp.name, cz.zona_name, moneda
ORDER BY total_neto DESC
LIMIT 10;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 2: "Si, de marzo de 2026" (follow-up, misma query)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 2: Follow-up marzo 2026 (misma data que P1) ===' AS pregunta;
-- Misma query que P1, el follow-up hereda el contexto temporal.


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 3: "Bueno, de febrero de 2026" (follow-up cambiando mes)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 3: Top clientes febrero 2026 ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT bp.name AS cliente,
       COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END) AS total_neto,
       COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
GROUP BY bp.name, cz.zona_name, moneda
ORDER BY total_neto DESC
LIMIT 10;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 4: "Ranking de ventas por zona del mes de enero 2026"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 4: Ranking ventas por zona enero 2026 ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
       COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                         WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_neto
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id
LEFT JOIN client_zone cz ON i.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 1
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
GROUP BY cz.zona_name
ORDER BY total_neto DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 5: "Dime el ranking de venta por zona" (follow-up, hereda enero 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 5: Follow-up ranking por zona (hereda enero 2026) ===' AS pregunta;
-- Misma query que P4, el follow-up hereda el período.


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 6: "¿Cuánto se facturó en dólares en febrero 2026?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 6: Facturación en USD febrero 2026 ===' AS pregunta;

SELECT COUNT(*) AS total_facturas,
       COALESCE(SUM(i.totallines), 0) AS total_facturado_usd
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 7: "Top 20 clientes por ventas del 2025"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 7: Top 20 clientes año 2025 ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT bp.name AS cliente,
       COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END) AS total_neto,
       COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2025
GROUP BY bp.name, cz.zona_name, moneda
ORDER BY total_neto DESC
LIMIT 20;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 8: "Top 20 clientes de InproMaiz en febrero 2026"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 8: Top 20 clientes InproMaiz febrero 2026 ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT bp.name AS cliente,
       COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END) AS total_neto,
       COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND i.ad_org_id IN (SELECT o.ad_org_id FROM adempiere.ad_org o WHERE o.name ILIKE '%inpromaiz%')
GROUP BY bp.name, cz.zona_name
ORDER BY total_neto DESC
LIMIT 20;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 9: "Puedes hacer este análisis pero por zona?" (follow-up InproMaiz feb 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 9: Ventas InproMaiz feb 2026 por zona ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
       COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                         WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_neto
FROM adempiere.c_invoice i
LEFT JOIN client_zone cz ON i.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND i.ad_org_id IN (SELECT o.ad_org_id FROM adempiere.ad_org o WHERE o.name ILIKE '%inpromaiz%')
GROUP BY cz.zona_name
ORDER BY total_neto DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 10: "Top 10 mejores vendedores de InproMaiz"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 10: Top 10 vendedores/distribuidores InproMaiz ===' AS pregunta;

SELECT COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
       COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                         WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_neto
FROM adempiere.c_invoice i
LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND i.ad_org_id IN (SELECT o.ad_org_id FROM adempiere.ad_org o WHERE o.name ILIKE '%inpromaiz%')
GROUP BY sr.name
ORDER BY total_neto DESC
LIMIT 10;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 11: "Top 10 clientes de InproMaíz en enero 2026"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 11: Top 10 clientes InproMaiz enero 2026 ===' AS pregunta;

WITH client_zone AS (
    SELECT DISTINCT ON (bpl.c_bpartner_id)
        bpl.c_bpartner_id, sreg.name AS zona_name
    FROM adempiere.c_bpartner_location bpl
    LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id
    WHERE bpl.isactive = 'Y'
    ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
)
SELECT bp.name AS cliente,
       COALESCE(cz.zona_name, 'Sin Zona') AS zona,
       SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines
                WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END) AS total_neto,
       COUNT(*) AS facturas
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 1
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND i.ad_org_id IN (SELECT o.ad_org_id FROM adempiere.ad_org o WHERE o.name ILIKE '%inpromaiz%')
GROUP BY bp.name, cz.zona_name
ORDER BY total_neto DESC
LIMIT 10;


-- ═══════════════════════════════════════════════════════════════════════
-- RRHH (7 preguntas)
-- ═══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 12: "¿Cuántos empleados activos hay en INPROA SANTONI?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 12: Empleados activos INPROA SANTONI ===' AS pregunta;

SELECT COALESCE(o.name, 'Sin Org') AS organizacion,
       COUNT(DISTINCT e.c_bpartner_id) AS total_empleados,
       COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos,
       COUNT(DISTINCT CASE WHEN e.isactive = 'N' THEN e.c_bpartner_id END) AS inactivos
FROM adempiere.hr_employee e
LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
GROUP BY o.name
ORDER BY total_empleados DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 13: "¿Cuántos empleados hay por departamento?" (follow-up)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 13: Empleados por departamento ===' AS pregunta;

SELECT COALESCE(d.name, 'Sin Departamento') AS departamento,
       COUNT(DISTINCT e.c_bpartner_id) AS total,
       COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos
FROM adempiere.hr_employee e
LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
GROUP BY d.name
ORDER BY total DESC
LIMIT 20;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 14: "¿Cuántos obreros integrales hay?" (follow-up)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 14: Obreros integrales ===' AS pregunta;

SELECT DISTINCT ON (bp.c_bpartner_id)
       bp.name AS nombre,
       COALESCE(o.name, '') AS organizacion,
       COALESCE(d.name, '') AS departamento,
       COALESCE(j.name, '') AS cargo,
       e.startdate AS fecha_ingreso
FROM adempiere.hr_employee e
JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
WHERE e.isactive = 'Y'
  AND j.name ILIKE '%obrero%' AND j.name ILIKE '%integral%'
ORDER BY bp.c_bpartner_id, e.startdate DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 15: "¿Cuántos choferes tiene la empresa?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 15: Choferes ===' AS pregunta;

SELECT DISTINCT ON (bp.c_bpartner_id)
       bp.name AS nombre,
       COALESCE(o.name, '') AS organizacion,
       COALESCE(d.name, '') AS departamento,
       COALESCE(j.name, '') AS cargo,
       e.startdate AS fecha_ingreso
FROM adempiere.hr_employee e
JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
WHERE e.isactive = 'Y'
  AND j.name ILIKE '%chofer%'
ORDER BY bp.c_bpartner_id, e.startdate DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 16: "Indicadores de ausentismo de INPROA SANTONI de septiembre 2025"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 16: Ausentismo INPROA SANTONI septiembre 2025 ===' AS pregunta;

SELECT hc.name AS concepto,
       COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados,
       COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs,
       COUNT(*) AS registros
FROM adempiere.hr_process hp
JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
WHERE hp.docstatus IN ('CO', 'CL') AND hp.isactive = 'Y'
  AND EXTRACT(MONTH FROM hp.dateacct) = 9
  AND EXTRACT(YEAR FROM hp.dateacct) = 2025
  AND (LOWER(hc.name) LIKE '%ausent%' OR LOWER(hc.name) LIKE '%inasist%'
       OR LOWER(hc.name) LIKE '%falta%' OR LOWER(hc.name) LIKE '%permiso%'
       OR LOWER(hc.name) LIKE '%reposo%' OR LOWER(hc.name) LIKE '%incapacidad%'
       OR LOWER(hc.name) LIKE '%licencia%')
GROUP BY hc.name
ORDER BY registros DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 17: "¿Cuántos empleados ingresaron entre enero y junio 2025?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 17: Nuevos ingresos enero-junio 2025 ===' AS pregunta;

SELECT DISTINCT ON (bp.c_bpartner_id)
       bp.name AS nombre,
       COALESCE(o.name, '') AS organizacion,
       COALESCE(d.name, '') AS departamento,
       COALESCE(j.name, '') AS cargo,
       e.startdate AS fecha_ingreso
FROM adempiere.hr_employee e
JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
WHERE e.isactive = 'Y'
  AND e.startdate >= '2025-01-01'
  AND e.startdate <= '2025-06-30'
ORDER BY bp.c_bpartner_id, e.startdate DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 18: "Cumpleañeros del mes de marzo"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 18: Cumpleañeros de marzo ===' AS pregunta;

-- Primero verificar si existe columna de cumpleaños:
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'adempiere'
  AND table_name IN ('c_bpartner', 'lve_c_bpartner', 'hr_employee')
  AND data_type IN ('date', 'timestamp without time zone', 'timestamp with time zone')
  AND (column_name LIKE '%birth%' OR column_name LIKE '%nac%' OR column_name LIKE '%cumple%')
ORDER BY table_name, column_name;

-- Si existe birthday en c_bpartner:
SELECT DISTINCT ON (bp.c_bpartner_id)
       bp.name AS nombre,
       EXTRACT(DAY FROM bp.birthday)::int AS dia,
       COALESCE(d.name, '') AS departamento,
       COALESCE(j.name, '') AS cargo
FROM adempiere.hr_employee e
JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
WHERE e.isactive = 'Y'
  AND bp.birthday IS NOT NULL
  AND EXTRACT(MONTH FROM bp.birthday) = 3
ORDER BY bp.c_bpartner_id, e.startdate DESC;


-- ═══════════════════════════════════════════════════════════════════════
-- FINANZAS (5 preguntas)
-- ═══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 19: "¿Cuáles son los saldos bancarios actuales?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 19: Saldos bancarios actuales ===' AS pregunta;

SELECT b.name AS banco,
       ba.accountno AS numero_cuenta,
       CASE WHEN ba.bankaccounttype = 'C' THEN 'Corriente'
            WHEN ba.bankaccounttype = 'S' THEN 'Ahorro'
            WHEN ba.bankaccounttype = 'I' THEN 'Inversión'
            ELSE ba.bankaccounttype END AS tipo,
       COALESCE(c.iso_code, 'VES') AS moneda,
       ba.currentbalance AS saldo,
       o.name AS organizacion
FROM adempiere.c_bankaccount ba
JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id
LEFT JOIN adempiere.c_currency c ON ba.c_currency_id = c.c_currency_id
LEFT JOIN adempiere.ad_org o ON ba.ad_org_id = o.ad_org_id
WHERE ba.isactive = 'Y'
ORDER BY c.iso_code, b.name;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 20: "¿Cuál es el banco con mayor disponibilidad actualmente?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 20: Banco con mayor disponibilidad ===' AS pregunta;

SELECT b.name AS banco,
       COALESCE(c.iso_code, 'VES') AS moneda,
       SUM(ba.currentbalance) AS saldo_total
FROM adempiere.c_bankaccount ba
JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id
LEFT JOIN adempiere.c_currency c ON ba.c_currency_id = c.c_currency_id
WHERE ba.isactive = 'Y'
GROUP BY b.name, c.iso_code
ORDER BY saldo_total DESC
LIMIT 5;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 21: "¿Cuánto tenemos en cuentas por cobrar vencidas?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 21: Cuentas por cobrar vencidas ===' AS pregunta;

-- NOTA: saldo pendiente real = grandtotal - SUM(abonos parciales).
-- El bot usa el mismo patrón (ver _OPEN_EXPR en idempiere_queries.py).
SELECT CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       COUNT(*) AS facturas_vencidas,
       COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0) AS total_vencido
FROM adempiere.c_invoice i
LEFT JOIN (
    SELECT al.c_invoice_id,
           SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
    FROM adempiere.c_allocationline al
    JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
    WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
    GROUP BY al.c_invoice_id
) alloc ON alloc.c_invoice_id = i.c_invoice_id
LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.ispaid = 'N' AND i.isactive = 'Y'
  AND (i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE
GROUP BY moneda;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 22: "¿Cuánto debemos en cuentas por pagar?" (follow-up)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 22: Cuentas por pagar ===' AS pregunta;

SELECT CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       COUNT(*) AS facturas_pendientes,
       COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0) AS total_por_pagar
FROM adempiere.c_invoice i
LEFT JOIN (
    SELECT al.c_invoice_id,
           SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
    FROM adempiere.c_allocationline al
    JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
    WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
    GROUP BY al.c_invoice_id
) alloc ON alloc.c_invoice_id = i.c_invoice_id
WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.ispaid = 'N' AND i.isactive = 'Y'
GROUP BY moneda
ORDER BY total_por_pagar DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 23: "Cuotas de préstamos vencidos a la fecha"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 23: Préstamos / CxP vencidas ===' AS pregunta;

-- iDempiere no tiene módulo de préstamos estándar, pero las cuotas
-- se reflejan como facturas de compra (CxP) vencidas:
SELECT CASE WHEN i.c_currency_id = 205 THEN 'Bs.'
            WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
            ELSE 'Otro' END AS moneda,
       COUNT(*) AS facturas_vencidas,
       COALESCE(SUM(i.grandtotal - COALESCE(alloc.paid, 0)), 0) AS total_vencido
FROM adempiere.c_invoice i
LEFT JOIN (
    SELECT al.c_invoice_id,
           SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid
    FROM adempiere.c_allocationline al
    JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
    WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL')
    GROUP BY al.c_invoice_id
) alloc ON alloc.c_invoice_id = i.c_invoice_id
LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id
WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.ispaid = 'N' AND i.isactive = 'Y'
  AND (i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE
GROUP BY moneda;


-- ═══════════════════════════════════════════════════════════════════════
-- PRODUCCION (9 preguntas)
-- ═══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 24: "¿Cuánto se produjo en enero 2026?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 24: Producción enero 2026 ===' AS pregunta;

SELECT SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones_mp,
       SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos_pt,
       SUM(CASE WHEN io.movementtype IN ('M+','M-') THEN 1 ELSE 0 END) AS movimientos_internos,
       SUM(CASE WHEN io.movementtype IN ('P+','P-') THEN 1 ELSE 0 END) AS mov_produccion,
       COUNT(*) AS total_movimientos
FROM adempiere.m_inout io
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 1
  AND EXTRACT(YEAR FROM io.movementdate) = 2026;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 25: "¿Cuáles son las órdenes de producción del mes?" (marzo 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 25: Movimientos de producción marzo 2026 ===' AS pregunta;

SELECT io.documentno AS documento,
       io.movementdate::date AS fecha,
       CASE io.movementtype
         WHEN 'V+' THEN 'Recepción MP'
         WHEN 'C-' THEN 'Despacho PT'
         WHEN 'M+' THEN 'Mov. Entrada'
         WHEN 'M-' THEN 'Mov. Salida'
         WHEN 'P+' THEN 'Producción +'
         WHEN 'P-' THEN 'Producción -'
         ELSE io.movementtype END AS tipo,
       org.name AS organizacion
FROM adempiere.m_inout io
JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 3
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
ORDER BY io.movementdate DESC
LIMIT 50;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 26: "¿Cuáles son las órdenes de producción del mes de enero de 2026?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 26: Movimientos de producción enero 2026 ===' AS pregunta;

SELECT io.documentno AS documento,
       io.movementdate::date AS fecha,
       CASE io.movementtype
         WHEN 'V+' THEN 'Recepción MP'
         WHEN 'C-' THEN 'Despacho PT'
         WHEN 'M+' THEN 'Mov. Entrada'
         WHEN 'M-' THEN 'Mov. Salida'
         WHEN 'P+' THEN 'Producción +'
         WHEN 'P-' THEN 'Producción -'
         ELSE io.movementtype END AS tipo,
       org.name AS organizacion
FROM adempiere.m_inout io
JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 1
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
ORDER BY io.movementdate DESC
LIMIT 50;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 27: "Dame el Inventario de materia prima actual"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 27: Inventario materia prima actual ===' AS pregunta;

SELECT p.name AS producto,
       pc.name AS categoria,
       w.name AS almacen,
       o.name AS organizacion,
       SUM(s.qtyonhand) AS cantidad_disponible
FROM adempiere.m_storageonhand s
JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id
JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id
JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id
JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id
LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
WHERE s.isactive = 'Y' AND s.qtyonhand <> 0
GROUP BY p.name, pc.name, w.name, o.name
HAVING SUM(s.qtyonhand) > 0
ORDER BY SUM(s.qtyonhand) DESC
LIMIT 30;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 28: "Me refería al mes de enero de 2026" (follow-up inventario)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 28: Movimientos de inventario enero 2026 ===' AS pregunta;

-- Para inventario de un mes pasado, se usan los movimientos (m_inout):
SELECT p.name AS producto,
       SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido,
       SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado,
       SUM(ABS(iol.movementqty)) AS total_movido
FROM adempiere.m_inout io
JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 1
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
GROUP BY p.name
ORDER BY total_movido DESC
LIMIT 20;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 29: "Producción de arroz blanco en enero 2026"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 29: Arroz blanco enero 2026 ===' AS pregunta;

SELECT p.name AS producto,
       SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido,
       SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado,
       SUM(ABS(iol.movementqty)) AS total_movido
FROM adempiere.m_inout io
JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 1
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
  AND (LOWER(p.name) LIKE '%arroz%' AND LOWER(p.name) LIKE '%blanc%')
GROUP BY p.name
ORDER BY total_movido DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 30: "¿Cuánto desperdicio hubo en empaque este mes?" (marzo 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 30: Desperdicio empaque marzo 2026 ===' AS pregunta;

-- Los desperdicios se registran como movimientos internos (M-) o producción (P-)
SELECT p.name AS producto,
       io.movementtype AS tipo_movimiento,
       SUM(ABS(iol.movementqty)) AS cantidad
FROM adempiere.m_inout io
JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 3
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
  AND io.movementtype IN ('M-', 'P-')
  AND (LOWER(p.name) LIKE '%empaqu%' OR LOWER(p.name) LIKE '%desperdi%'
       OR LOWER(p.name) LIKE '%merma%' OR LOWER(p.name) LIKE '%scrap%')
GROUP BY p.name, io.movementtype
ORDER BY cantidad DESC;

-- Si la query anterior no arroja datos, buscar TODOS los movimientos tipo salida en empaque:
SELECT p.name AS producto,
       io.movementtype,
       SUM(ABS(iol.movementqty)) AS cantidad
FROM adempiere.m_inout io
JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND EXTRACT(MONTH FROM io.movementdate) = 3
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
  AND io.movementtype IN ('M-', 'P-')
GROUP BY p.name, io.movementtype
ORDER BY cantidad DESC
LIMIT 20;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 31: "¿Cuántas cajas de cartón recibimos en enero 2026?"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 31: Cajas de cartón recibidas enero 2026 ===' AS pregunta;

-- Recepción de materia prima (V+) de cajas de cartón
SELECT p.name AS producto,
       SUM(iol.movementqty) AS cantidad_recibida,
       io.movementtype
FROM adempiere.m_inout io
JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
  AND io.movementtype = 'V+'
  AND EXTRACT(MONTH FROM io.movementdate) = 1
  AND EXTRACT(YEAR FROM io.movementdate) = 2026
  AND (LOWER(p.name) LIKE '%caja%' AND LOWER(p.name) LIKE '%cart%')
GROUP BY p.name, io.movementtype
ORDER BY cantidad_recibida DESC;

-- Alternativa: también buscar en facturas de compra
SELECT p.name AS producto,
       bp.name AS proveedor,
       SUM(il.qtyinvoiced) AS cantidad,
       SUM(il.linenetamt) AS total
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND EXTRACT(MONTH FROM i.dateinvoiced) = 1
  AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
  AND (LOWER(p.name) LIKE '%caja%' AND LOWER(p.name) LIKE '%cart%')
GROUP BY p.name, bp.name
ORDER BY total DESC;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 32: "Inventario de producto terminado actual"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 32: Inventario producto terminado actual ===' AS pregunta;

SELECT p.name AS producto,
       pc.name AS categoria,
       w.name AS almacen,
       o.name AS organizacion,
       SUM(s.qtyonhand) AS cantidad_disponible
FROM adempiere.m_storageonhand s
JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id
JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id
JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id
JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id
LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
WHERE s.isactive = 'Y' AND s.qtyonhand <> 0
GROUP BY p.name, pc.name, w.name, o.name
HAVING SUM(s.qtyonhand) > 0
ORDER BY SUM(s.qtyonhand) DESC
LIMIT 30;


-- ═══════════════════════════════════════════════════════════════════════
-- COMPRAS INSUMOS (2 preguntas)
-- ═══════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 33: "Dame el historial de compras de azúcar del último trimestre"
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 33: Compras de azúcar último trimestre ===' AS pregunta;

-- "Último trimestre" desde la fecha actual (mar 2026) = dic 2025 a mar 2026
SELECT p.value AS codigo_producto, p.name AS producto,
       bp.name AS proveedor, i.documentno AS factura,
       i.dateinvoiced AS fecha,
       il.qtyinvoiced AS cantidad,
       il.priceactual AS precio_unitario,
       il.linenetamt AS total_linea
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 months')
  AND (LOWER(p.name) LIKE '%azucar%' OR LOWER(p.name) LIKE '%azúcar%'
       OR LOWER(p.value) LIKE '%azucar%')
ORDER BY i.dateinvoiced DESC
LIMIT 50;


-- ──────────────────────────────────────────────────────────────────────
-- PREGUNTA 34: "Disculpa el trimestre a analizar es de, enero a marzo"
-- (follow-up que corrige el período a enero-marzo 2026)
-- ──────────────────────────────────────────────────────────────────────
SELECT '=== PREGUNTA 34: Compras azúcar enero-marzo 2026 ===' AS pregunta;

SELECT p.value AS codigo_producto, p.name AS producto,
       bp.name AS proveedor, i.documentno AS factura,
       i.dateinvoiced AS fecha,
       il.qtyinvoiced AS cantidad,
       il.priceactual AS precio_unitario,
       il.linenetamt AS total_linea
FROM adempiere.c_invoice i
JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
WHERE i.issotrx = 'N' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
  AND i.dateinvoiced >= '2026-01-01'
  AND i.dateinvoiced <= '2026-03-31'
  AND (LOWER(p.name) LIKE '%azucar%' OR LOWER(p.name) LIKE '%azúcar%'
       OR LOWER(p.value) LIKE '%azucar%')
ORDER BY i.dateinvoiced DESC
LIMIT 50;


-- ═══════════════════════════════════════════════════════════════════════
-- RESUMEN: VERIFICACIÓN DE TABLAS DISPONIBLES
-- ═══════════════════════════════════════════════════════════════════════

SELECT '=== VERIFICACIÓN: Tablas principales y conteo de registros ===' AS pregunta;

-- Ventas
SELECT 'c_invoice (facturas)' AS tabla,
       COUNT(*) AS registros,
       COUNT(*) FILTER (WHERE issotrx = 'Y' AND docstatus IN ('CO', 'CL')) AS facturas_venta,
       COUNT(*) FILTER (WHERE issotrx = 'N' AND docstatus IN ('CO', 'CL')) AS facturas_compra
FROM adempiere.c_invoice;

-- Empleados
SELECT 'hr_employee' AS tabla,
       COUNT(*) AS registros,
       COUNT(DISTINCT c_bpartner_id) AS empleados_unicos,
       COUNT(DISTINCT c_bpartner_id) FILTER (WHERE isactive = 'Y') AS activos
FROM adempiere.hr_employee;

-- Bancos
SELECT 'c_bankaccount' AS tabla,
       COUNT(*) AS registros,
       COUNT(*) FILTER (WHERE isactive = 'Y') AS activas
FROM adempiere.c_bankaccount;

-- Movimientos (producción/inventario)
SELECT 'm_inout (movimientos)' AS tabla,
       COUNT(*) AS registros,
       COUNT(*) FILTER (WHERE docstatus IN ('CO', 'CL')) AS completados
FROM adempiere.m_inout;

-- Stock actual
SELECT 'm_storageonhand (inventario)' AS tabla,
       COUNT(*) AS registros,
       COUNT(*) FILTER (WHERE qtyonhand > 0) AS con_stock
FROM adempiere.m_storageonhand;

-- Nómina
SELECT 'hr_process (nómina)' AS tabla,
       COUNT(*) AS registros,
       COUNT(*) FILTER (WHERE docstatus IN ('CO', 'CL')) AS completados
FROM adempiere.hr_process;

-- Organizaciones
SELECT 'ad_org' AS tabla, ad_org_id, name
FROM adempiere.ad_org
WHERE isactive = 'Y'
ORDER BY name;
