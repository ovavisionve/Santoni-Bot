#!/usr/bin/env python3
"""Diagnóstico: explorar tablas de iDempiere no mapeadas.

Busca tablas y columnas relacionadas con conceptos que el bot no pudo responder:
1. Préstamos bancarios / pagarés / compromisos
2. Tipos de documento (Factura A, B, C, V)
3. Líneas de crédito / financiamiento
4. Cualquier tabla financiera no mapeada

Uso:
    docker compose exec backend python scripts/explore_idempiere_schema.py
    # o directo:
    cd backend && python scripts/explore_idempiere_schema.py
"""

import os
import sys

# Ensure the backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text


def get_idempiere_session():
    """Get a session to the iDempiere database."""
    try:
        from app.services.idempiere_queries import IdempiereSession
        return IdempiereSession()
    except Exception:
        # Fallback: connect directly using env var
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        url = os.environ.get("IDEMPIERE_DATABASE_URL")
        if not url:
            print("ERROR: Set IDEMPIERE_DATABASE_URL or run inside Docker")
            sys.exit(1)
        engine = create_engine(url)
        return Session(engine)


def section(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def run_query(db, sql: str, params: dict | None = None):
    """Run a query and return results as list of tuples."""
    result = db.execute(text(sql), params or {})
    return result.fetchall()


def main():
    db = get_idempiere_session()
    try:
        # ================================================================
        # 1. TABLAS FINANCIERAS NO MAPEADAS
        # ================================================================
        section("1. TABLAS RELACIONADAS CON PRÉSTAMOS/PAGARÉS/COMPROMISOS BANCARIOS")

        # Buscar tablas que contengan palabras clave financieras
        financial_keywords = [
            'loan', 'prestamo', 'pagare', 'commitment', 'credit_line',
            'bank_statement', 'cashflow', 'budget', 'forecast',
            'charge', 'gl_fund', 'gl_budget',
        ]
        for kw in financial_keywords:
            rows = run_query(db, f"""
                SELECT table_name,
                       (SELECT COUNT(*) FROM information_schema.columns c2
                        WHERE c2.table_schema = 'adempiere' AND c2.table_name = t.table_name) AS num_cols
                FROM information_schema.tables t
                WHERE t.table_schema = 'adempiere'
                AND t.table_name ILIKE :kw
                ORDER BY t.table_name
            """, {"kw": f"%{kw}%"})
            if rows:
                print(f"  Keyword '{kw}':")
                for r in rows:
                    print(f"    - {r[0]} ({r[1]} columnas)")

        # Buscar tablas con "bank" que no sean c_bankaccount o c_bank
        print("\n  Tablas con 'bank' en el nombre:")
        rows = run_query(db, """
            SELECT t.table_name,
                   (SELECT COUNT(*) FROM information_schema.columns c2
                    WHERE c2.table_schema = 'adempiere' AND c2.table_name = t.table_name) AS num_cols,
                   (SELECT reltuples::bigint FROM pg_class pc
                    JOIN pg_namespace ns ON pc.relnamespace = ns.oid
                    WHERE ns.nspname = 'adempiere' AND pc.relname = t.table_name) AS est_rows
            FROM information_schema.tables t
            WHERE t.table_schema = 'adempiere'
            AND t.table_name ILIKE '%bank%'
            ORDER BY t.table_name
        """)
        for r in rows:
            print(f"    - {r[0]} ({r[1]} cols, ~{r[2]} filas)")

        # ================================================================
        # 2. TIPOS DE DOCUMENTO
        # ================================================================
        section("2. TIPOS DE DOCUMENTO EN c_doctype (ventas y compras)")

        rows = run_query(db, """
            SELECT dt.name, dt.docbasetype, dt.printname,
                   COUNT(DISTINCT i.c_invoice_id) AS num_facturas
            FROM adempiere.c_doctype dt
            LEFT JOIN adempiere.c_invoice i
                ON i.c_doctypetarget_id = dt.c_doctype_id
                AND i.docstatus IN ('CO', 'CL')
                AND i.dateinvoiced >= '2025-01-01'
            WHERE dt.docbasetype IN ('ARI', 'ARC', 'API', 'APC')
            GROUP BY dt.c_doctype_id, dt.name, dt.docbasetype, dt.printname
            ORDER BY dt.docbasetype, num_facturas DESC
        """)
        print(f"  {'Nombre':<45} {'Base':<6} {'PrintName':<30} {'Facturas 2025+'}")
        print(f"  {'-'*45} {'-'*6} {'-'*30} {'-'*12}")
        for r in rows:
            print(f"  {r[0]:<45} {r[1]:<6} {r[2] or '':<30} {r[3]}")

        # ================================================================
        # 3. TABLAS c_charge Y CARGOS (puede contener conceptos financieros)
        # ================================================================
        section("3. CARGOS (c_charge) - posibles pagarés/préstamos como cargos")

        rows = run_query(db, """
            SELECT c.name, c.description, c.chargeamt,
                   CASE WHEN c.isactive = 'Y' THEN 'Activo' ELSE 'Inactivo' END
            FROM adempiere.c_charge c
            WHERE c.name ILIKE '%prest%' OR c.name ILIKE '%pagar%'
                OR c.name ILIKE '%compromis%' OR c.name ILIKE '%credit%'
                OR c.name ILIKE '%loan%' OR c.name ILIKE '%bank%'
            ORDER BY c.name
            LIMIT 20
        """)
        if rows:
            for r in rows:
                print(f"  - {r[0]} | {r[1] or ''} | Monto: {r[2]} | {r[3]}")
        else:
            print("  (Sin resultados para cargos financieros)")

        # ================================================================
        # 4. CUENTAS CONTABLES RELACIONADAS CON PRÉSTAMOS
        # ================================================================
        section("4. CUENTAS CONTABLES con 'prestamo', 'pagare', 'credito bancario'")

        rows = run_query(db, """
            SELECT ev.value AS codigo, ev.name AS cuenta,
                   CASE ev.accounttype
                       WHEN 'A' THEN 'Activo' WHEN 'L' THEN 'Pasivo'
                       WHEN 'O' THEN 'Patrimonio' WHEN 'R' THEN 'Ingreso'
                       WHEN 'E' THEN 'Gasto' ELSE ev.accounttype END AS tipo,
                   ev.issummary
            FROM adempiere.c_elementvalue ev
            WHERE ev.isactive = 'Y'
            AND (ev.name ILIKE '%prestam%' OR ev.name ILIKE '%pagar%'
                 OR ev.name ILIKE '%credito%banc%' OR ev.name ILIKE '%compromis%'
                 OR ev.name ILIKE '%financ%' OR ev.name ILIKE '%obligaci%')
            ORDER BY ev.value
        """)
        if rows:
            print(f"  {'Código':<15} {'Cuenta':<55} {'Tipo':<12} {'Summary'}")
            print(f"  {'-'*15} {'-'*55} {'-'*12} {'-'*7}")
            for r in rows:
                print(f"  {r[0]:<15} {r[1]:<55} {r[2]:<12} {r[3]}")
        else:
            print("  (Sin resultados)")

        # ================================================================
        # 5. FACT_ACCT: Movimientos en cuentas de préstamos (si existen)
        # ================================================================
        section("5. MOVIMIENTOS CONTABLES en cuentas de préstamos (últimos 2 años)")

        rows = run_query(db, """
            SELECT ev.value AS codigo, ev.name AS cuenta,
                   COUNT(*) AS movimientos,
                   SUM(fa.amtacctdr) AS total_debe,
                   SUM(fa.amtacctcr) AS total_haber,
                   MIN(fa.dateacct) AS desde,
                   MAX(fa.dateacct) AS hasta
            FROM adempiere.fact_acct fa
            JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
            WHERE ev.isactive = 'Y'
            AND (ev.name ILIKE '%prestam%' OR ev.name ILIKE '%pagar%'
                 OR ev.name ILIKE '%credito%banc%' OR ev.name ILIKE '%compromis%'
                 OR ev.name ILIKE '%obligaci%')
            AND fa.dateacct >= '2024-01-01'
            GROUP BY ev.value, ev.name
            ORDER BY movimientos DESC
            LIMIT 20
        """)
        if rows:
            print(f"  {'Código':<15} {'Cuenta':<45} {'Movs':<8} {'Debe':<20} {'Haber':<20} {'Desde':<12} {'Hasta'}")
            print(f"  {'-'*15} {'-'*45} {'-'*8} {'-'*20} {'-'*20} {'-'*12} {'-'*12}")
            for r in rows:
                print(f"  {r[0]:<15} {r[1][:45]:<45} {r[2]:<8} {r[3]:>18,.2f} {r[4]:>18,.2f} {str(r[5])[:10]:<12} {str(r[6])[:10]}")
        else:
            print("  (Sin movimientos en cuentas de préstamos)")

        # ================================================================
        # 6. c_bankstatement / c_bankstatementline
        # ================================================================
        section("6. ESTADOS DE CUENTA BANCARIOS (c_bankstatement)")

        rows = run_query(db, """
            SELECT t.table_name,
                   (SELECT reltuples::bigint FROM pg_class pc
                    JOIN pg_namespace ns ON pc.relnamespace = ns.oid
                    WHERE ns.nspname = 'adempiere' AND pc.relname = t.table_name) AS est_rows
            FROM information_schema.tables t
            WHERE t.table_schema = 'adempiere'
            AND t.table_name IN ('c_bankstatement', 'c_bankstatementline')
        """)
        for r in rows:
            print(f"  - {r[0]}: ~{r[1]} filas")

        # Detalle de columnas de bankstatement
        for tbl in ['c_bankstatement', 'c_bankstatementline']:
            rows = run_query(db, """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'adempiere' AND table_name = :tbl
                ORDER BY ordinal_position
            """, {"tbl": tbl})
            if rows:
                print(f"\n  Columnas de {tbl}:")
                for r in rows:
                    print(f"    - {r[0]} ({r[1]}, null={r[2]})")

        # Datos recientes
        rows = run_query(db, """
            SELECT bs.name, bs.statementdate, bs.docstatus,
                   ba.accountno, b.name AS banco,
                   (SELECT COUNT(*) FROM adempiere.c_bankstatementline bsl
                    WHERE bsl.c_bankstatement_id = bs.c_bankstatement_id) AS num_lineas
            FROM adempiere.c_bankstatement bs
            JOIN adempiere.c_bankaccount ba ON bs.c_bankaccount_id = ba.c_bankaccount_id
            JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id
            WHERE bs.statementdate >= '2025-01-01'
            ORDER BY bs.statementdate DESC
            LIMIT 15
        """)
        if rows:
            print(f"\n  Últimos estados de cuenta (2025+):")
            print(f"  {'Nombre':<40} {'Fecha':<12} {'Estado':<8} {'Cuenta':<22} {'Banco':<25} {'Líneas'}")
            for r in rows:
                print(f"  {str(r[0])[:40]:<40} {str(r[1])[:10]:<12} {r[2]:<8} {str(r[3])[:22]:<22} {str(r[4])[:25]:<25} {r[5]}")
        else:
            print("\n  (Sin estados de cuenta recientes)")

        # ================================================================
        # 7. TABLAS GL (General Ledger) no mapeadas
        # ================================================================
        section("7. TABLAS GL (General Ledger) no mapeadas")

        rows = run_query(db, """
            SELECT t.table_name,
                   (SELECT reltuples::bigint FROM pg_class pc
                    JOIN pg_namespace ns ON pc.relnamespace = ns.oid
                    WHERE ns.nspname = 'adempiere' AND pc.relname = t.table_name) AS est_rows
            FROM information_schema.tables t
            WHERE t.table_schema = 'adempiere'
            AND t.table_name LIKE 'gl_%'
            ORDER BY t.table_name
        """)
        for r in rows:
            print(f"  - {r[0]}: ~{r[1]} filas")

        # ================================================================
        # 8. DOCUMENTOS TIPO "COMPROMISO" O "LOAN" en c_order
        # ================================================================
        section("8. TIPOS DE DOCUMENTO EN c_doctype (TODOS los docbasetype)")

        rows = run_query(db, """
            SELECT dt.docbasetype, dt.name,
                   COUNT(DISTINCT dt.c_doctype_id) AS num_tipos
            FROM adempiere.c_doctype dt
            WHERE dt.isactive = 'Y'
            GROUP BY dt.docbasetype, dt.name
            ORDER BY dt.docbasetype, dt.name
        """)
        current_base = None
        for r in rows:
            if r[0] != current_base:
                current_base = r[0]
                print(f"\n  [{r[0]}]")
            print(f"    - {r[1]}")

        # ================================================================
        # 9. TABLAS C_* FINANCIERAS NO EXPLORADAS
        # ================================================================
        section("9. TABLAS c_* POTENCIALMENTE FINANCIERAS (con >0 filas)")

        rows = run_query(db, """
            SELECT t.table_name,
                   (SELECT reltuples::bigint FROM pg_class pc
                    JOIN pg_namespace ns ON pc.relnamespace = ns.oid
                    WHERE ns.nspname = 'adempiere' AND pc.relname = t.table_name) AS est_rows
            FROM information_schema.tables t
            WHERE t.table_schema = 'adempiere'
            AND t.table_name SIMILAR TO 'c_(cash|charge|conversion|commission|debt|deposit|dunning|fund|interest|loan|payment|revenue|tax|withholding)%'
            AND (SELECT reltuples::bigint FROM pg_class pc
                 JOIN pg_namespace ns ON pc.relnamespace = ns.oid
                 WHERE ns.nspname = 'adempiere' AND pc.relname = t.table_name) > 0
            ORDER BY t.table_name
        """)
        for r in rows:
            print(f"  - {r[0]}: ~{r[1]} filas")

        # ================================================================
        # 10. BUSCAR EN TODA LA DB: tablas con columna "loanamt" o similar
        # ================================================================
        section("10. COLUMNAS con nombres financieros en CUALQUIER tabla")

        for col_kw in ['loan', 'pagare', 'commitment', 'credit_limit', 'creditlimit',
                        'loanamt', 'interestamt', 'creditamt']:
            rows = run_query(db, """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'adempiere'
                AND column_name ILIKE :kw
                LIMIT 10
            """, {"kw": f"%{col_kw}%"})
            if rows:
                print(f"  Columnas con '{col_kw}':")
                for r in rows:
                    print(f"    - {r[0]}.{r[1]} ({r[2]})")

        # ================================================================
        # 11. SOCIOS DE NEGOCIO: campos financieros
        # ================================================================
        section("11. CAMPOS FINANCIEROS en c_bpartner (proveedores/clientes)")

        rows = run_query(db, """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'adempiere' AND table_name = 'c_bpartner'
            AND (column_name ILIKE '%credit%' OR column_name ILIKE '%loan%'
                 OR column_name ILIKE '%limit%' OR column_name ILIKE '%score%'
                 OR column_name ILIKE '%rating%' OR column_name ILIKE '%balance%')
            ORDER BY column_name
        """)
        if rows:
            for r in rows:
                print(f"  - c_bpartner.{r[0]} ({r[1]})")

        print("\n" + "=" * 80)
        print("  DIAGNÓSTICO COMPLETADO")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
