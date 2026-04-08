-- =====================================================================
-- Verificación del esquema de Ventas de iDempiere
-- contra la relación de tablas que compartió Santoni.
--
-- Uso (desde el servidor santonibot):
--   PGPASSWORD='ova2026*' psql -h 192.168.1.73 -U ova \
--     -d idempiere_produccion -f scripts/verificar_schema_ventas_santoni.sql
--
-- O desde docker:
--   cat scripts/verificar_schema_ventas_santoni.sql | \
--     docker compose exec -T backend psql \
--       "postgresql://ova:ova2026%2A@192.168.1.73:5432/idempiere_produccion"
-- =====================================================================

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 1) ¿Existen todas las tablas que menciona Santoni?'
\echo '═══════════════════════════════════════════════════════════════════'
WITH expected(tbl, descripcion) AS (VALUES
    ('c_order',              'Orden de venta'),
    ('c_orderline',          'Linea de orden de venta'),
    ('c_invoice',            'Factura'),
    ('c_invoiceline',        'Linea de factura'),
    ('m_pricelist',          'Lista de precios'),
    ('m_productprice',       'Productos por lista de precios'),
    ('m_product_category',   'Categorias de producto'),
    ('m_product',            'Producto'),
    ('c_uom',                'Unidad de medida'),
    ('c_conversion_rate',    'Tasa de cambio'),
    ('c_payment',            'Cobros / Pagos'),
    ('c_allocationline',     'Pagos asignados a factura'),
    ('c_bpartner',           'Tercero (cliente/proveedor/empleado)'),
    ('c_bpartner_location',  'Direccion de cliente'),
    ('c_project',            'Sucursales'),
    ('c_salesregion',        'Region de ventas'),
    ('dcs_salesregiongroup', 'Grupo de region de ventas'),
    ('c_tax',                'Impuestos'),
    ('ad_user',              'Usuarios del sistema (vendedores)'),
    ('c_currency',           'Monedas')
)
SELECT
    e.tbl AS tabla,
    e.descripcion,
    CASE WHEN t.table_name IS NOT NULL THEN 'SI' ELSE '--- NO EXISTE ---' END AS existe,
    COALESCE(
        (SELECT COUNT(*)::text FROM information_schema.columns
         WHERE table_schema='adempiere' AND table_name=e.tbl),
        '0'
    ) AS num_columnas
FROM expected e
LEFT JOIN information_schema.tables t
    ON t.table_schema='adempiere' AND t.table_name=e.tbl
ORDER BY existe DESC, tbl;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 2) Flags criticos en las tablas principales'
\echo '═══════════════════════════════════════════════════════════════════'
WITH expected(tbl, col, descripcion) AS (VALUES
    -- Flag sales/compras
    ('c_invoice',          'issotrx',      'Y = venta, N = compra'),
    ('c_order',            'issotrx',      'Y = venta, N = compra'),
    -- Moneda (205 = Bs)
    ('c_invoice',          'c_currency_id', 'FK a c_currency (205=Bs)'),
    ('c_order',            'c_currency_id', 'FK a c_currency (205=Bs)'),
    ('c_payment',          'c_currency_id', 'FK a c_currency (205=Bs)'),
    -- Vendedor
    ('c_invoice',          'salesrep_id',  'FK a ad_user (vendedor)'),
    ('c_order',            'salesrep_id',  'FK a ad_user (vendedor)'),
    -- Cobros
    ('c_payment',          'isreceipt',    'Y = cobro, N = pago'),
    -- Tipologia tercero
    ('c_bpartner',         'iscustomer',   'Y = cliente'),
    ('c_bpartner',         'isvendor',     'Y = proveedor'),
    ('c_bpartner',         'isemployee',   'Y = empleado'),
    -- SKU en categorias
    ('m_product_category', 'iskpi',        'Y = categoria SKU'),
    -- Docstatus y totales
    ('c_invoice',          'docstatus',    'CO=completada, CL=cerrada, RE=reversa'),
    ('c_invoice',          'grandtotal',   'Total con IVA'),
    ('c_invoice',          'totallines',   'Total sin IVA'),
    ('c_invoice',          'dateinvoiced', 'Fecha de factura'),
    ('c_invoice',          'ad_org_id',    'FK a ad_org (organizacion)')
)
SELECT
    e.tbl AS tabla,
    e.col AS columna,
    e.descripcion,
    CASE WHEN c.column_name IS NOT NULL THEN 'SI' ELSE '--- NO EXISTE ---' END AS existe,
    COALESCE(c.data_type, '') AS tipo
FROM expected e
LEFT JOIN information_schema.columns c
    ON c.table_schema='adempiere' AND c.table_name=e.tbl AND c.column_name=e.col
ORDER BY existe DESC, tbl, col;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 3) ¿c_currency_id = 205 es realmente Bolivares?'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT c_currency_id, iso_code, description, cursymbol
FROM adempiere.c_currency
WHERE c_currency_id = 205;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 4) Todas las monedas activas (para confirmar el universo USD)'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT c_currency_id, iso_code, description, cursymbol, isactive
FROM adempiere.c_currency
WHERE isactive = 'Y'
ORDER BY c_currency_id;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 5) Distribucion de issotrx en c_invoice (sanity check)'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT issotrx, COUNT(*) AS n_facturas
FROM adempiere.c_invoice
GROUP BY issotrx
ORDER BY issotrx;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 6) Distribucion de docstatus en c_invoice'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT docstatus, COUNT(*) AS n_facturas
FROM adempiere.c_invoice
GROUP BY docstatus
ORDER BY n_facturas DESC;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 7) Distribucion de isreceipt en c_payment'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT isreceipt, COUNT(*) AS n_pagos
FROM adempiere.c_payment
GROUP BY isreceipt
ORDER BY isreceipt;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 8) Foreign keys de c_invoice (confirmar relaciones)'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT
    kcu.column_name AS columna_local,
    ccu.table_name  AS tabla_referenciada,
    ccu.column_name AS columna_referenciada
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'adempiere'
  AND tc.table_name = 'c_invoice'
  AND kcu.column_name IN ('salesrep_id', 'c_bpartner_id', 'c_currency_id', 'ad_org_id', 'c_doctypetarget_id')
ORDER BY kcu.column_name;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 9) Organizaciones (ad_org) activas'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT ad_org_id, name, value, isactive
FROM adempiere.ad_org
WHERE isactive = 'Y'
ORDER BY name;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' 10) Muestra de 3 vendedores (ad_user con salesrep_id asignado)'
\echo '═══════════════════════════════════════════════════════════════════'
SELECT DISTINCT u.ad_user_id, u.name, u.email
FROM adempiere.ad_user u
JOIN adempiere.c_invoice i ON i.salesrep_id = u.ad_user_id
WHERE i.issotrx = 'Y'
  AND i.docstatus IN ('CO', 'CL')
  AND u.isactive = 'Y'
ORDER BY u.name
LIMIT 3;

\echo
\echo '═══════════════════════════════════════════════════════════════════'
\echo ' FIN DE LA VERIFICACION'
\echo '═══════════════════════════════════════════════════════════════════'
