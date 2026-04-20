-- =============================================================
-- VERIFICACIÓN: Órdenes de compra pendientes (DR/IP) en 2026
-- Replica build_pending_purchase_orders()
-- =============================================================

-- Query 1: Totales por estado
SELECT
    CASE o.docstatus
      WHEN 'DR' THEN 'Borrador'
      WHEN 'IP' THEN 'En Proceso'
      ELSE o.docstatus END AS estado,
    CASE WHEN o.c_currency_id = 205 THEN 'Bs.'
         WHEN o.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
         THEN 'USD' ELSE 'Otro' END AS moneda,
    COUNT(DISTINCT o.c_order_id) AS ordenes,
    COALESCE(SUM(o.grandtotal), 0) AS total
FROM adempiere.c_order o
WHERE o.issotrx = 'N'
  AND o.isactive = 'Y'
  AND o.docstatus IN ('DR', 'IP')
  AND EXTRACT(YEAR FROM o.dateordered) = 2026
GROUP BY o.docstatus, CASE WHEN o.c_currency_id = 205 THEN 'Bs.'
     WHEN o.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
     THEN 'USD' ELSE 'Otro' END
ORDER BY total DESC;

-- Query 2: Misma query pero filtrando por producto azúcar (para ver si el bot heredó el filtro)
SELECT
    CASE o.docstatus
      WHEN 'DR' THEN 'Borrador'
      WHEN 'IP' THEN 'En Proceso'
      ELSE o.docstatus END AS estado,
    COUNT(DISTINCT o.c_order_id) AS ordenes,
    COALESCE(SUM(o.grandtotal), 0) AS total
FROM adempiere.c_order o
WHERE o.issotrx = 'N'
  AND o.isactive = 'Y'
  AND o.docstatus IN ('DR', 'IP')
  AND EXTRACT(YEAR FROM o.dateordered) = 2026
  AND EXISTS (SELECT 1 FROM adempiere.c_orderline ol2
              JOIN adempiere.m_product p2 ON ol2.m_product_id = p2.m_product_id
              WHERE ol2.c_order_id = o.c_order_id
              AND (p2.name ILIKE '%azucar%' OR p2.value ILIKE '%azucar%'))
GROUP BY o.docstatus
ORDER BY total DESC;
