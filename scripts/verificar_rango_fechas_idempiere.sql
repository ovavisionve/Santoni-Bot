-- ============================================================================
-- VERIFICACIÓN: ¿Desde qué año hay data en iDempiere?
-- Ejecutar contra: 192.168.1.73:5432 / idempiere_produccion
-- ============================================================================

-- Facturas (ventas y compras)
SELECT 'c_invoice (facturas)' AS tabla,
       MIN(dateinvoiced)::date AS desde,
       MAX(dateinvoiced)::date AS hasta,
       COUNT(*) AS total_registros
FROM adempiere.c_invoice
WHERE docstatus = 'CO';

-- Facturas de VENTA por año
SELECT EXTRACT(YEAR FROM dateinvoiced)::int AS anio,
       COUNT(*) AS facturas_venta
FROM adempiere.c_invoice
WHERE issotrx = 'Y' AND docstatus = 'CO'
GROUP BY anio ORDER BY anio;

-- Facturas de COMPRA por año
SELECT EXTRACT(YEAR FROM dateinvoiced)::int AS anio,
       COUNT(*) AS facturas_compra
FROM adempiere.c_invoice
WHERE issotrx = 'N' AND docstatus = 'CO'
GROUP BY anio ORDER BY anio;

-- Pagos/cobros
SELECT 'c_payment (pagos)' AS tabla,
       MIN(datetrx)::date AS desde,
       MAX(datetrx)::date AS hasta,
       COUNT(*) AS total_registros
FROM adempiere.c_payment
WHERE docstatus = 'CO';

-- Movimientos de inventario (producción)
SELECT 'm_inout (movimientos)' AS tabla,
       MIN(movementdate)::date AS desde,
       MAX(movementdate)::date AS hasta,
       COUNT(*) AS total_registros
FROM adempiere.m_inout
WHERE docstatus = 'CO';

-- Movimientos de inventario por año
SELECT EXTRACT(YEAR FROM movementdate)::int AS anio,
       COUNT(*) AS movimientos
FROM adempiere.m_inout
WHERE docstatus = 'CO'
GROUP BY anio ORDER BY anio;

-- Nómina (hr_process)
SELECT 'hr_process (nómina)' AS tabla,
       MIN(dateacct)::date AS desde,
       MAX(dateacct)::date AS hasta,
       COUNT(*) AS total_registros
FROM adempiere.hr_process
WHERE docstatus = 'CO';

-- Nómina por año
SELECT EXTRACT(YEAR FROM dateacct)::int AS anio,
       COUNT(*) AS procesos_nomina
FROM adempiere.hr_process
WHERE docstatus = 'CO'
GROUP BY anio ORDER BY anio;

-- Empleados (fecha de ingreso más antigua)
SELECT 'hr_employee (empleados)' AS tabla,
       MIN(startdate)::date AS ingreso_mas_antiguo,
       MAX(startdate)::date AS ingreso_mas_reciente,
       COUNT(DISTINCT c_bpartner_id) AS empleados_unicos
FROM adempiere.hr_employee;

-- Contabilidad (fact_acct)
SELECT 'fact_acct (contabilidad)' AS tabla,
       MIN(dateacct)::date AS desde,
       MAX(dateacct)::date AS hasta,
       COUNT(*) AS total_asientos
FROM adempiere.fact_acct;

-- Órdenes de compra
SELECT 'c_order (órdenes)' AS tabla,
       MIN(dateordered)::date AS desde,
       MAX(dateordered)::date AS hasta,
       COUNT(*) AS total_registros
FROM adempiere.c_order
WHERE docstatus = 'CO';
