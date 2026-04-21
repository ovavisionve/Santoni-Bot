"""Catálogo: REGLAS de generación SQL para Claude."""

REGLAS_SQL = """
## REGLAS para generar SQL:
1. SOLO usar SELECT (nunca INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
2. Todas las tablas deben tener prefijo 'adempiere.' (ej: adempiere.lve_empleadosactivos)
3. Limitar a 500 filas con LIMIT 500
4. Para fechas SIEMPRE usar rangos `dateXX >= 'YYYY-MM-DD' AND dateXX < 'YYYY-MM-DD'`.
   NO usar `EXTRACT(YEAR FROM ...)` ni `EXTRACT(MONTH FROM ...)` en filtros de fecha
   (excepto para cumpleaños en `birthday`) porque rompe el uso de índices y causa
   timeouts de > 120s. Ejemplo OK: `dateinvoiced >= '2026-02-01' AND dateinvoiced < '2026-03-01'`.
5. Para ventas SIEMPRE filtrar: issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
6. Para compras a proveedores: issotrx='N' en c_invoice
7. Para compras a productores: usar c_order (guías), NO c_invoice
8. VES = c_currency_id = 205. USD = c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
9. Usar totallines (sin IVA) para montos de ventas, grandtotal (con IVA) para compras
10. Si no sabes qué columna tiene una tabla, haz tu mejor intento con las columnas del catálogo
11. SIEMPRE intenta generar SQL. Solo responde NO_SQL si la pregunta no tiene nada que ver con datos (ej: "hola", "gracias", chistes). Para cualquier pregunta sobre datos empresariales, genera el SQL.
12. **FILTRO DE ORGS DEMO (blacklist, no whitelist):** iDempiere trae orgs DEMO
    de fábrica (HQ, Store Central/East/North/South/West, Stores, Furniture,
    Fertilizer) y la org system-wide (nombre '*'). No son orgs reales de Santoni
    y pueden contaminar totales. Cuando el usuario NO especifique una organización
    concreta Y estés sumando/contando datos financieros (c_invoice, c_payment,
    c_order, fact_acct), **agregá SIEMPRE este filtro para excluirlas**:
    ```
    AND {alias}.ad_org_id IN (
      SELECT ad_org_id FROM adempiere.ad_org
      WHERE isactive = 'Y'
        AND name NOT ILIKE 'HQ' AND name NOT ILIKE 'Fertilizer'
        AND name NOT ILIKE 'Furniture'
        AND name NOT ILIKE 'Store Central' AND name NOT ILIKE 'Store East'
        AND name NOT ILIKE 'Store North' AND name NOT ILIKE 'Store South'
        AND name NOT ILIKE 'Store West' AND name NOT ILIKE 'Stores'
        AND name NOT ILIKE '*'
    )
    ```
    Este filtro es BLACKLIST: incluye TODAS las orgs reales (INPROA SANTONI,
    InproMaiz, AGROINPROA, AGROPECUARIA R.R., AGA AGRICOLA, INVERSIONES AGA,
    Santoni Service, Ocean Equipment Industries LLC, Venecauchos, Agro Import,
    y cualquier filial nueva que Santoni cree a futuro) y solo excluye las demos
    conocidas de iDempiere. Esto es mejor que whitelist porque no oculta orgs
    reales durmientes si el usuario pregunta histórico.
    Esto NO aplica para `lve_empleadosactivos` (ya filtra internamente) ni para
    queries de RRHH/cumpleaños.
"""
