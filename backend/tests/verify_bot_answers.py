"""
Verificación SQL directa contra iDempiere.
Compara respuestas del bot con datos reales de la base de datos.

Ejecutar en el servidor:
    python3 backend/tests/verify_bot_answers.py

Requiere acceso a iDempiere (192.168.1.73).
"""

import sys
import psycopg2
from decimal import Decimal

# ── Conexión iDempiere ──
IDEM_CONN = {
    "host": "192.168.1.73",
    "port": 5432,
    "database": "idempiere_produccion",
    "user": "ova",
    "password": "ova2026*",
}

# IDs de monedas en Santoni
VES_IDS = [205]
USD_IDS = [100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017]

# Mapeo moneda → empresa
# DOL (1000000) = INPROA SANTONI
# DoL (1000011) = InproMaiz
# Dol (1000006) = INVERSIONES AGA
# USA (1000003) = AGROINPROA
# dol (1000008) = AGROPECUARIA R.R.
# DLA = Santoni Service


def fmt(val):
    """Formato venezolano para números."""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float, Decimal)):
        # Formato con separador de miles
        return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(val)


def run_query(cur, label, sql, params=None):
    """Ejecuta query y muestra resultado."""
    print(f"\n{'─' * 70}")
    print(f"  {label}")
    print(f"{'─' * 70}")
    try:
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        if not rows:
            print("  (sin resultados)")
            return rows

        # Calcular anchos de columna
        widths = [len(c) for c in cols]
        formatted_rows = []
        for row in rows:
            frow = [fmt(v) for v in row]
            formatted_rows.append(frow)
            for i, v in enumerate(frow):
                widths[i] = max(widths[i], len(v))

        # Header
        header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        print(f"  {header}")
        print(f"  {'-+-'.join('-' * w for w in widths)}")

        # Rows (max 20)
        for frow in formatted_rows[:20]:
            line = " | ".join(frow[i].ljust(widths[i]) for i in range(len(cols)))
            print(f"  {line}")

        if len(rows) > 20:
            print(f"  ... ({len(rows)} filas total)")

        return rows
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    print("=" * 70)
    print("  VERIFICACIÓN SQL - Respuestas del Bot vs iDempiere")
    print("=" * 70)

    try:
        conn = psycopg2.connect(**IDEM_CONN)
        conn.set_session(readonly=True)
        cur = conn.cursor()
        print(f"  Conectado a {IDEM_CONN['host']}/{IDEM_CONN['database']}")
    except Exception as e:
        print(f"ERROR conexión: {e}")
        sys.exit(1)

    # ──────────────────────────────────────────────────────────────────────
    # 1. Total compras insumos febrero 2026 (VES)
    #    Bot dijo: 1.145.119.859,51 VES
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "1. Total compras insumos FEBRERO 2026 - TODAS las monedas\n"
        "   Bot dijo: 1.145.119.859,51 VES",
        """
        SELECT COUNT(DISTINCT i.c_invoice_id) AS total_facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total_monto
        FROM adempiere.c_invoice i
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
        """)

    # Desglose por moneda
    run_query(cur,
        "1b. Desglose por MONEDA - febrero 2026",
        """
        SELECT c.iso_code, c.c_currency_id,
               COUNT(DISTINCT i.c_invoice_id) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
        GROUP BY c.iso_code, c.c_currency_id
        ORDER BY total DESC
        """)

    # Solo VES
    run_query(cur,
        "1c. Solo VES (c_currency_id=205) - febrero 2026",
        """
        SELECT COUNT(DISTINCT i.c_invoice_id) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total_ves
        FROM adempiere.c_invoice i
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
          AND i.c_currency_id = 205
        """)

    # Solo USD (todos los IDs)
    run_query(cur,
        "1d. Solo DÓLARES (todos los IDs USD) - febrero 2026",
        """
        SELECT COUNT(DISTINCT i.c_invoice_id) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total_usd
        FROM adempiere.c_invoice i
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
          AND i.c_currency_id IN (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. Órdenes pendientes febrero 2026
    #    Bot dijo: 1.180 órdenes
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "2. Total facturas compra FEBRERO 2026 (todas monedas)\n"
        "   Bot dijo: 1.180 órdenes",
        """
        SELECT COUNT(DISTINCT i.c_invoice_id) AS total_facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total_monto
        FROM adempiere.c_invoice i
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 3. Inventario cajas de cartón
    #    Bot dijo: -14.255 unidades, 2 productos
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "3. Inventario 'caja' + 'carton' (m_storageonhand)\n"
        "   Bot dijo: 2 productos, -14.255 unidades",
        """
        SELECT p.value AS codigo, p.name AS producto,
               COALESCE(o.name, '-') AS organizacion,
               SUM(s.qtyonhand) AS cantidad,
               COALESCE(u.name, '-') AS unidad
        FROM adempiere.m_storageonhand s
        JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id
        JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id
        JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id
        JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id
        LEFT JOIN adempiere.c_uom u ON p.c_uom_id = u.c_uom_id
        WHERE s.isactive = 'Y' AND s.qtyonhand <> 0
          AND (p.name ILIKE '%%caja%%' AND p.name ILIKE '%%carton%%')
        GROUP BY p.value, p.name, o.name, u.name
        ORDER BY cantidad DESC
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 4. Código de caja de cartón para cereales
    #    Bot dijo: IS-CAJ-220
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "4. Producto 'caja' + 'carton' + 'cereal'\n"
        "   Bot dijo: IS-CAJ-220",
        """
        SELECT p.value AS codigo, p.name AS producto,
               COALESCE(pc.name, '-') AS categoria
        FROM adempiere.m_product p
        LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id
        WHERE p.name ILIKE '%%caja%%'
          AND p.name ILIKE '%%carton%%'
          AND p.name ILIKE '%%cereal%%'
        ORDER BY p.name
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 5. Proveedores láminas hierro negro
    #    Bot dijo: MATERIALES Y METALES ACARIGUA, 10/02/2026
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "5. Compras de 'lamina' (word-based search) - 2026\n"
        "   Bot dijo: MATERIALES Y METALES ACARIGUA, 10/02/2026",
        """
        SELECT p.value AS codigo, p.name AS producto,
               bp.name AS proveedor, i.documentno AS factura,
               i.dateinvoiced AS fecha,
               il.qtyinvoiced AS cantidad, il.linenetamt AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
        JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        WHERE i.issotrx = 'N' AND i.docstatus = 'CO' AND i.isactive = 'Y'
          AND (p.name ILIKE '%%lamina%%' OR p.value ILIKE '%%lamina%%')
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
        ORDER BY i.dateinvoiced DESC
        LIMIT 20
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 6. Historial REP-LAMI-0037
    #    Bot dijo: SUPLIDORA INDUSTRIAL..., PREF-025340, 02/02/2026
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "6. Historial REP-LAMI-0037\n"
        "   Bot dijo: SUPLIDORA INDUSTRIAL, PREF-025340, 02/02/2026",
        """
        SELECT p.value AS codigo, p.name AS producto,
               bp.name AS proveedor, i.documentno AS factura,
               i.dateinvoiced AS fecha,
               il.qtyinvoiced AS cantidad,
               il.priceactual AS precio_unit,
               il.linenetamt AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
        JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        WHERE i.issotrx = 'N' AND i.docstatus = 'CO' AND i.isactive = 'Y'
          AND (p.value ILIKE '%%REP-LAMI-0037%%')
        ORDER BY i.dateinvoiced DESC
        LIMIT 10
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 7. Último proveedor REP-TUER-0115 en INPROA
    #    Bot dijo: TORNILLERIA EL GUAMAL, 19/01/2026
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "7. Último proveedor REP-TUER-0115\n"
        "   Bot dijo: TORNILLERIA EL GUAMAL, 19/01/2026",
        """
        SELECT p.value AS codigo, p.name AS producto,
               bp.name AS proveedor, i.documentno AS factura,
               i.dateinvoiced AS fecha,
               il.qtyinvoiced AS cantidad,
               il.priceactual AS precio_unit
        FROM adempiere.c_invoice i
        JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
        JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        WHERE i.issotrx = 'N' AND i.docstatus = 'CO' AND i.isactive = 'Y'
          AND (p.value ILIKE '%%REP-TUER-0115%%')
        ORDER BY i.dateinvoiced DESC
        LIMIT 5
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 8. Gasoil en INPROA SANTONI, 01/01/26 - 23/02/26
    #    Bot dijo: FILTRO IVECO TECTOR GASOIL 2992241: 4 unidades, FILTRO GASOIL...
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "8. Productos 'gasoil' en INPROA, ene-feb 2026\n"
        "   Bot dijo: FILTRO IVECO TECTOR GASOIL: 4 uds, FILTRO GASOIL...",
        """
        SELECT p.value AS codigo, p.name AS producto,
               bp.name AS proveedor,
               i.dateinvoiced AS fecha,
               il.qtyinvoiced AS cantidad,
               il.linenetamt AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id
        JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        WHERE i.issotrx = 'N' AND i.docstatus = 'CO' AND i.isactive = 'Y'
          AND (p.name ILIKE '%%gasoil%%' OR p.value ILIKE '%%gasoil%%')
          AND i.dateinvoiced >= '2026-01-01'
          AND i.dateinvoiced <= '2026-02-23'
        ORDER BY i.dateinvoiced DESC
        """)

    # ──────────────────────────────────────────────────────────────────────
    # 9. Mapeo moneda → empresa (referencia)
    # ──────────────────────────────────────────────────────────────────────
    run_query(cur,
        "9. REFERENCIA: Monedas usadas por empresa - compras feb 2026",
        """
        SELECT o.name AS organizacion,
               c.iso_code, c.c_currency_id,
               COUNT(DISTINCT i.c_invoice_id) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
        JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
        WHERE i.issotrx = 'N'
          AND i.docstatus = 'CO'
          AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
        GROUP BY o.name, c.iso_code, c.c_currency_id
        ORDER BY o.name, total DESC
        """)

    print(f"\n{'=' * 70}")
    print("  Verificación completa")
    print(f"{'=' * 70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
