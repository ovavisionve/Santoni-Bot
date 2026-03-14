-- ============================================================
-- VERIFICACIÓN DE PRODUCCIÓN AÑO 2025
-- Ejecutar contra iDempiere: psql -h 192.168.1.73 -U ova -d idempiere_produccion
-- ============================================================

-- 1. TOTALES GENERALES 2025
SELECT
    COUNT(DISTINCT pr.m_production_id) AS total_producciones,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0
        THEN prl.movementqty ELSE 0 END), 0) AS kg_producto_terminado,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0
        THEN ABS(prl.movementqty) ELSE 0 END), 0) AS kg_insumos_consumidos
FROM adempiere.m_production pr
JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
WHERE pr.isactive = 'Y'
  AND pr.docstatus IN ('CO', 'CL')
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31';

-- 2. DESGLOSE POR MES (para comparar con la tabla del bot)
SELECT
    EXTRACT(YEAR FROM pr.movementdate)::int AS anio,
    EXTRACT(MONTH FROM pr.movementdate)::int AS mes,
    COUNT(DISTINCT pr.m_production_id) AS producciones,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0
        THEN prl.movementqty ELSE 0 END), 0) AS kg_terminado,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0
        THEN ABS(prl.movementqty) ELSE 0 END), 0) AS kg_consumido
FROM adempiere.m_production pr
JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
WHERE pr.isactive = 'Y'
  AND pr.docstatus IN ('CO', 'CL')
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31'
GROUP BY EXTRACT(YEAR FROM pr.movementdate), EXTRACT(MONTH FROM pr.movementdate)
ORDER BY anio, mes;

-- 3. POR ORGANIZACIÓN
SELECT
    org.name AS organizacion,
    COUNT(DISTINCT pr.m_production_id) AS producciones,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0
        THEN prl.movementqty ELSE 0 END), 0) AS kg_terminado,
    COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0
        THEN ABS(prl.movementqty) ELSE 0 END), 0) AS kg_consumido
FROM adempiere.m_production pr
JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
JOIN adempiere.ad_org org ON pr.ad_org_id = org.ad_org_id
WHERE pr.isactive = 'Y'
  AND pr.docstatus IN ('CO', 'CL')
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31'
GROUP BY org.name
ORDER BY producciones DESC;

-- 4. TOP 20 PRODUCTOS TERMINADOS
SELECT
    p.name AS producto,
    COUNT(DISTINCT pr.m_production_id) AS producciones,
    COALESCE(SUM(prl.movementqty), 0) AS kg_producidos
FROM adempiere.m_production pr
JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id
WHERE pr.isactive = 'Y'
  AND pr.docstatus IN ('CO', 'CL')
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31'
  AND prl.isendproduct = 'Y'
  AND prl.movementqty > 0
GROUP BY p.name
ORDER BY kg_producidos DESC
LIMIT 20;

-- 5. TOP 20 INSUMOS CONSUMIDOS
SELECT
    p.name AS insumo,
    COALESCE(SUM(ABS(prl.movementqty)), 0) AS kg_consumidos
FROM adempiere.m_production pr
JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id
WHERE pr.isactive = 'Y'
  AND pr.docstatus IN ('CO', 'CL')
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31'
  AND (prl.isendproduct = 'N' OR prl.movementqty < 0)
GROUP BY p.name
ORDER BY kg_consumidos DESC
LIMIT 20;

-- 6. VERIFICACIÓN: ¿Hay producciones con otros docstatus excluidas?
SELECT
    pr.docstatus,
    COUNT(*) AS cantidad
FROM adempiere.m_production pr
WHERE pr.isactive = 'Y'
  AND pr.movementdate >= '2025-01-01'
  AND pr.movementdate <= '2025-12-31'
GROUP BY pr.docstatus
ORDER BY cantidad DESC;
