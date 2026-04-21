"""Catálogo: ejemplos de queries comunes para que Claude aprenda patrones."""

EJEMPLOS_SQL = """
## EJEMPLOS de queries comunes:

-- Sueldo promedio por organización (usar `sueldo` base, NO `total`):
-- NOTA DE PERFORMANCE: `v.sueldo` es columna directa y AVG es rápido.
-- `v.total` es calculado per-row (sueldo + bonos) y AVG(v.total) puede
-- tirar timeout >30s. Solo usá `total` si el usuario pide "devengado".
-- IMPORTANTE: usar siempre alias `v.` para lve_empleadosactivos cuando hay
-- JOIN con ad_org (ambas tablas tienen columna `name` → ambigua sin alias).
SELECT AVG(v.sueldo) AS sueldo_promedio_base, COUNT(*) AS empleados
FROM adempiere.lve_empleadosactivos v
JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id
WHERE o.name ILIKE '%InproMaiz%'
LIMIT 500

-- Facturas de venta por moneda y período (CON filtro blacklist de orgs demo):
SELECT COUNT(DISTINCT i.c_invoice_id) AS facturas,
       COALESCE(SUM(i.totallines), 0) AS total
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL') AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'
  AND i.ad_org_id IN (
    SELECT ad_org_id FROM adempiere.ad_org
    WHERE isactive = 'Y'
      AND name NOT ILIKE 'HQ' AND name NOT ILIKE 'Fertilizer'
      AND name NOT ILIKE 'Furniture'
      AND name NOT ILIKE 'Store Central' AND name NOT ILIKE 'Store East'
      AND name NOT ILIKE 'Store North' AND name NOT ILIKE 'Store South'
      AND name NOT ILIKE 'Store West' AND name NOT ILIKE 'Stores'
      AND name NOT ILIKE '*'
  )
LIMIT 500

-- Cumpleañeros de un mes en una org:
SELECT name, cargo, departamento, birthday
FROM adempiere.lve_empleadosactivos
WHERE EXTRACT(MONTH FROM birthday) = 5
  AND ad_org_id IN (SELECT ad_org_id FROM adempiere.ad_org WHERE name ILIKE '%INPROA SANTONI%')
ORDER BY EXTRACT(DAY FROM birthday)
LIMIT 500

-- Top vendedores por venta neta:
SELECT au.name AS vendedor,
  COALESCE(SUM(CASE WHEN dt.docbasetype='ARI' THEN i.totallines WHEN dt.docbasetype='ARC' THEN -i.totallines ELSE 0 END),0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_user au ON i.salesrep_id = au.ad_user_id
WHERE i.issotrx='Y' AND i.docstatus IN ('CO','CL') AND i.isactive='Y'
  AND i.c_currency_id = 205
  AND i.dateinvoiced >= '2026-02-01' AND i.dateinvoiced < '2026-03-01'
GROUP BY au.name ORDER BY venta_neta DESC
LIMIT 10

-- Resumen de procesos de nómina por tipo (desglose COMPLETO + TOTAL en una query):
-- OJO: NO calcules el total sumando en tu cabeza al formatear — el SQL incluye
-- la fila TOTAL GENERAL vía UNION ALL para que el número sea exacto.
-- IMPORTANTE: hr_process usa `dateacct`, NO `hrdate`. Filtramos por m.validfrom
-- (en hr_movement) que es más directo.
WITH desglose AS (
    SELECT pr.name AS tipo_nomina,
           COUNT(DISTINCT p.hr_process_id) AS procesos,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados,
           COALESCE(SUM(m.amount), 0) AS total_bs
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_process p ON m.hr_process_id = p.hr_process_id
    JOIN adempiere.hr_payroll pr ON p.hr_payroll_id = pr.hr_payroll_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%INPROA SANTONI%'
    GROUP BY pr.name
)
-- Usamos una columna 'sort_order' auxiliar para ordenar el resultado.
-- PostgreSQL NO acepta expresiones calculadas como ORDER BY tras UNION ALL,
-- pero SÍ acepta columnas del SELECT. Por eso agregamos sort_order (0/1).
SELECT tipo_nomina, procesos, empleados, total_bs, 0 AS sort_order FROM desglose
UNION ALL
SELECT 'TOTAL GENERAL',
       (SELECT SUM(procesos) FROM desglose),
       (SELECT SUM(empleados) FROM desglose),
       (SELECT SUM(total_bs) FROM desglose),
       1 AS sort_order
ORDER BY sort_order, total_bs DESC
LIMIT 500

-- Ausentismo por concepto en un período (AGROINPROA marzo 2026):
-- USAR FILTROS GENÉRICOS: %Permiso% captura "Dias de Asignacion de Permiso",
-- "Horas de Permiso No Remunerado", "Monto por Permiso Remunerado", etc.
-- Si usás sólo "%Permiso No Remunerado%" perdés las asignaciones de permiso.
-- Incluye TOTAL GENERAL vía UNION ALL para evitar que Claude sume mal.
WITH desglose AS (
    SELECT c.name AS concepto,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados_afectados,
           COUNT(*) AS ocurrencias,
           COALESCE(SUM(m.amount), 0) AS monto_bs,
           COALESCE(SUM(m.qty), 0) AS cantidad
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%AGROINPROA%'
      AND (c.name ILIKE '%Falta%' OR c.name ILIKE '%Permiso%'
           OR c.name ILIKE '%Inasistencia%' OR c.name ILIKE '%Reposo%'
           OR c.name ILIKE '%Ausencia%' OR c.name ILIKE '%Atraso%')
    GROUP BY c.name
)
SELECT concepto, empleados_afectados, ocurrencias, monto_bs, cantidad, 0 AS sort_order FROM desglose
UNION ALL
SELECT 'TOTAL GENERAL',
       NULL,
       (SELECT SUM(ocurrencias) FROM desglose),
       (SELECT SUM(monto_bs) FROM desglose),
       (SELECT SUM(cantidad) FROM desglose),
       1 AS sort_order
ORDER BY sort_order, monto_bs DESC
LIMIT 500

-- Nombres de trabajadores con un concepto específico (ej: Faltas y Atrasos):
-- El nombre real del empleado viene de c_bpartner, NO de hr_employee.
SELECT DISTINCT bp.name AS empleado,
       bp.taxid AS cedula,
       j.name AS cargo,
       COUNT(*) AS ocurrencias,
       COALESCE(SUM(m.amount), 0) AS monto_bs,
       COALESCE(SUM(m.qty), 0) AS qty
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_employee e ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
WHERE c.name ILIKE '%Faltas y Atrasos%'
  AND m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
  AND o.name ILIKE '%AGROINPROA%'
GROUP BY bp.name, bp.taxid, j.name
ORDER BY monto_bs DESC
LIMIT 500

-- Conceptos pagados/deducidos a UN empleado específico en un período:
SELECT c.name AS concepto,
       COUNT(*) AS ocurrencias,
       COALESCE(SUM(m.amount), 0) AS monto_bs,
       COALESCE(SUM(m.qty), 0) AS qty
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
WHERE bp.name ILIKE '%Geovanna%'
  AND m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
GROUP BY c.name
ORDER BY monto_bs DESC
LIMIT 500

-- Control vacacional (vacaciones pagadas/disfrutadas en un período).
-- NO intentar calcular "días acumulados LOTT" con joins complejos contra
-- múltiples tablas y funciones fecha — eso da timeout (>30s). En su lugar
-- listar los movimientos de nómina con concepto ILIKE '%vacacion%':
SELECT bp.name AS empleado,
       bp.taxid AS cedula,
       j.name AS cargo,
       c.name AS concepto,
       m.validfrom::date AS periodo_desde,
       m.validto::date AS periodo_hasta,
       m.qty AS dias,
       m.amount AS monto_bs
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_employee e ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
WHERE c.name ILIKE '%vacacion%'
  AND m.validfrom >= '2026-04-01' AND m.validfrom < '2026-06-01'
  AND o.name ILIKE '%INPROA SANTONI%'
ORDER BY bp.name, m.validfrom
LIMIT 500

-- Ventas USD separando ProFormas de Facturas Legales (REGLA #8):
-- El usuario pregunta "ventas en dólares marzo 2026". Santoni distingue
-- ProFormas (USD real pre-factura) de Facturas Legales (cierre Bs/USD).
-- Devolvemos AMBAS métricas así el usuario entiende la diferencia.
WITH clasificacion AS (
    SELECT i.c_invoice_id, i.totallines, dt.name AS tipo_doc,
           dt.docbasetype,
           CASE
               WHEN dt.name ILIKE '%Proforma%' OR dt.name ILIKE '%ProDolares%'
                    OR dt.name ILIKE '%Pro-Forma%' THEN 'ProForma'
               ELSE 'FacturaLegal'
           END AS categoria
    FROM adempiere.c_invoice i
    JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
    WHERE i.issotrx='Y' AND i.docstatus IN ('CO','CL') AND i.isactive='Y'
      AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
      AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'
)
SELECT categoria,
       docbasetype,
       COUNT(*) FILTER (WHERE docbasetype='ARI') AS facturas,
       COUNT(*) FILTER (WHERE docbasetype='ARC') AS notas_credito,
       COALESCE(SUM(CASE WHEN docbasetype='ARI' THEN totallines
                         WHEN docbasetype='ARC' THEN -totallines ELSE 0 END), 0) AS neto_usd
FROM clasificacion
GROUP BY categoria, docbasetype
ORDER BY categoria, docbasetype
LIMIT 500

-- Empleados con antigüedad >= N años (usar EXTRACT sobre startdate, NO
-- tservicio que es texto). CRÍTICO: prefijar TODAS las columnas con `v.`
-- porque lve_empleadosactivos y ad_org ambas tienen columna `name`.
-- Sin alias → `column reference "name" is ambiguous` y la query falla.
SELECT v.name, v.cargo, v.departamento, v.startdate::date AS ingreso,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, v.startdate))::int AS anos_servicio
FROM adempiere.lve_empleadosactivos v
JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id
WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, v.startdate)) >= 5
  AND o.name ILIKE '%INPROA SANTONI%'
ORDER BY anos_servicio DESC
LIMIT 500

-- Análisis de antigüedad de saldos / facturas vencidas (CxC aging):
-- PATRÓN RECOMENDADO para queries específicas de org/período: SUBQUERY
-- CORRELACIONADA ESCALAR. Es simple, rápida, y permite referenciar `i`
-- desde adentro porque el scope DE UN SCALAR SUBQUERY SÍ ve el outer.
-- Este es el patrón NATURAL para aging — usalo por default.
SELECT bp.name AS cliente,
       i.documentno AS factura,
       i.dateinvoiced::date AS fecha_emision,
       (i.dateinvoiced + COALESCE(pt.netdays, 30))::date AS fecha_vencimiento,
       i.grandtotal AS monto_factura,
       COALESCE((
           SELECT SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0))
           FROM adempiere.c_allocationline al
           JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
           WHERE al.c_invoice_id = i.c_invoice_id  -- correlación OK en scalar subquery
             AND ah.isactive = 'Y' AND ah.docstatus IN ('CO','CL')
       ), 0) AS monto_pagado,
       (i.grandtotal - COALESCE((
           SELECT SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0))
           FROM adempiere.c_allocationline al
           JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id
           WHERE al.c_invoice_id = i.c_invoice_id
             AND ah.isactive = 'Y' AND ah.docstatus IN ('CO','CL')
       ), 0)) AS saldo_abierto,
       (CURRENT_DATE - (i.dateinvoiced + COALESCE(pt.netdays, 30))) AS dias_vencido
FROM adempiere.c_invoice i
JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL') AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND o.name ILIKE '%InproMaiz%'  -- filtro org aquí, simple y efectivo
  AND (CURRENT_DATE - (i.dateinvoiced + COALESCE(pt.netdays, 30))) > 60
ORDER BY dias_vencido DESC
LIMIT 500

-- Ausentismo MULTI-MES (Enero, Febrero, Marzo) — patrón correcto para ORDER BY
-- tras UNION ALL con columna cronológica.
-- CLAVE: las columnas del ORDER BY DEBEN estar en TODAS las ramas del UNION,
-- aunque sean NULL en la fila TOTAL. PostgreSQL solo acepta columnas del
-- SELECT como ORDER BY tras UNION ALL, NUNCA expresiones CASE ni cálculos.
WITH desglose AS (
    SELECT EXTRACT(MONTH FROM m.validfrom)::int AS mes_num,
           TO_CHAR(m.validfrom, 'TMMonth') AS mes,
           c.name AS concepto,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados,
           COUNT(*) AS ocurrencias,
           COALESCE(SUM(m.amount), 0) AS monto_bs
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-01-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%AGROINPROA%'
      AND (c.name ILIKE '%Falta%' OR c.name ILIKE '%Permiso%'
           OR c.name ILIKE '%Inasistencia%' OR c.name ILIKE '%Reposo%')
    GROUP BY EXTRACT(MONTH FROM m.validfrom), TO_CHAR(m.validfrom, 'TMMonth'), c.name
)
-- FIJARSE: mes_num, mes, concepto, empleados, ocurrencias, monto_bs, sort_order
-- Las 7 columnas están en AMBAS ramas del UNION, con NULL donde no aplique.
SELECT mes_num, mes, concepto, empleados, ocurrencias, monto_bs, 0 AS sort_order
FROM desglose
UNION ALL
SELECT NULL AS mes_num, 'TOTAL GENERAL' AS mes, NULL AS concepto,
       NULL AS empleados,
       (SELECT SUM(ocurrencias) FROM desglose) AS ocurrencias,
       (SELECT SUM(monto_bs) FROM desglose) AS monto_bs,
       1 AS sort_order
ORDER BY sort_order, mes_num, monto_bs DESC  -- mes_num funciona porque
                                              -- está en AMBAS ramas (NULL en TOTAL)
LIMIT 500
"""
