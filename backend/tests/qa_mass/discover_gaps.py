#!/usr/bin/env python3
"""
Descubrimiento de gaps: ¿Qué tiene iDempiere que el bot NO consulta?

Cruza:
  A. Tablas de iDempiere con >100 filas (datos reales, no config)
  B. Tablas que el bot consulta (extraídas de idempiere_queries.py)

Resultado: lista de tablas con datos que el bot IGNORA, ordenadas
por número de filas (impacto potencial).

Esto permite identificar proactivamente qué preguntas de usuarios
van a fallar porque el bot no sabe que los datos existen.

Uso:
    docker compose exec backend python tests/qa_mass/discover_gaps.py
"""

import re
from pathlib import Path

from sqlalchemy import text
from app.database import IdempiereSession


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def get_idempiere_tables_with_data(db, min_rows: int = 100) -> dict[str, int]:
    """Lista todas las tablas de adempiere con más de N filas."""
    sql = text("""
        SELECT schemaname || '.' || relname AS table_name,
               n_live_tup AS row_count
        FROM pg_stat_user_tables
        WHERE schemaname = 'adempiere'
          AND n_live_tup > :min_rows
        ORDER BY n_live_tup DESC
    """)
    rows = db.execute(sql, {"min_rows": min_rows}).fetchall()
    return {r[0].replace("adempiere.", ""): int(r[1]) for r in rows}


def get_bot_known_tables() -> set[str]:
    """Extrae las tablas que el bot consulta de idempiere_queries.py."""
    queries_path = Path(__file__).parent.parent.parent / "app" / "services" / "idempiere_queries.py"
    if not queries_path.exists():
        return set()

    content = queries_path.read_text()
    # Match patterns like: adempiere.c_invoice, adempiere.hr_employee, etc.
    tables = set()
    for match in re.finditer(r'adempiere\.(\w+)', content):
        table = match.group(1).lower()
        tables.add(table)
    return tables


# Tablas de configuración/sistema que no son datos de negocio
_SYSTEM_TABLES = {
    "ad_ref_list", "ad_ref_table", "ad_reference", "ad_tab", "ad_table",
    "ad_window", "ad_field", "ad_column", "ad_element", "ad_form",
    "ad_menu", "ad_message", "ad_process", "ad_process_para",
    "ad_role", "ad_sequence", "ad_treenodemm", "ad_treenode",
    "ad_val_rule", "ad_workflow", "ad_wf_node", "ad_wf_nodenext",
    "ad_preference", "ad_pinstance", "ad_pinstance_log",
    "ad_pinstance_para", "ad_session", "ad_changelog", "ad_issue",
    "ad_note", "ad_recent_item", "ad_archive", "ad_attachment",
    "ad_attachmentnote", "t_selection", "t_report",
    "ad_trl", "ad_element_trl", "ad_field_trl", "ad_menu_trl",
    "ad_message_trl", "ad_process_trl", "ad_ref_list_trl",
    "ad_tab_trl", "ad_window_trl", "ad_form_trl", "ad_wf_node_trl",
}

# Categorización de tablas por dominio
_DOMAIN_HINTS = {
    "c_invoice": "ventas/compras",
    "c_invoiceline": "ventas/compras",
    "c_order": "ventas/compras",
    "c_orderline": "ventas/compras",
    "c_payment": "finanzas",
    "c_bankstatement": "finanzas",
    "c_bankaccount": "finanzas",
    "c_bpartner": "maestros",
    "m_product": "maestros",
    "m_inout": "logística",
    "m_inoutline": "logística",
    "m_inventory": "inventario",
    "m_movement": "inventario",
    "m_production": "producción",
    "m_storageonhand": "inventario",
    "hr_employee": "rrhh",
    "hr_movement": "rrhh",
    "hr_process": "rrhh",
    "hr_concept": "rrhh",
    "fact_acct": "contabilidad",
    "gl_journal": "contabilidad",
    "gl_journalline": "contabilidad",
    "c_allocationhdr": "finanzas",
    "c_allocationline": "finanzas",
    "c_project": "proyectos",
    "c_activity": "actividades",
    "pa_goal": "metas/KPI",
    "gl_budget": "presupuesto",
    "c_tax": "impuestos",
}


def guess_domain(table_name: str) -> str:
    """Intenta adivinar el dominio de una tabla por su nombre."""
    t = table_name.lower()
    if t in _DOMAIN_HINTS:
        return _DOMAIN_HINTS[t]
    if t.startswith("hr_") or t.startswith("lve_"):
        return "rrhh"
    if t.startswith("m_"):
        return "inventario/producto"
    if t.startswith("c_"):
        return "comercial"
    if t.startswith("gl_") or t.startswith("fact_"):
        return "contabilidad"
    if t.startswith("pa_"):
        return "performance/KPI"
    if t.startswith("btd_"):
        return "biométrico/asistencia"
    if t.startswith("dcs_"):
        return "custom santoni"
    if t.startswith("ad_"):
        return "sistema"
    return "otro"


def main():
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  GAPS: Tablas con datos que el bot NO consulta")
    print(f"{'=' * 70}{Colors.RESET}\n")

    db = IdempiereSession()
    try:
        # A. What iDempiere has
        all_tables = get_idempiere_tables_with_data(db, min_rows=100)
        print(f"  Tablas en iDempiere con >100 filas: {len(all_tables)}")

        # B. What the bot knows
        bot_tables = get_bot_known_tables()
        print(f"  Tablas que el bot consulta: {len(bot_tables)}")

        # C. Gap = A - B - system tables
        gap_tables = {}
        for table, rows in all_tables.items():
            t_lower = table.lower()
            if t_lower in bot_tables:
                continue
            if t_lower in _SYSTEM_TABLES:
                continue
            if t_lower.endswith("_trl"):
                continue
            gap_tables[table] = rows

        print(f"  {Colors.RED}Tablas con datos que el bot IGNORA: {len(gap_tables)}{Colors.RESET}")

        # D. Group by domain
        by_domain: dict[str, list[tuple[str, int]]] = {}
        for table, rows in sorted(gap_tables.items(), key=lambda x: -x[1]):
            domain = guess_domain(table)
            if domain == "sistema":
                continue
            by_domain.setdefault(domain, []).append((table, rows))

        print(f"\n{Colors.BOLD}  Por dominio (ordenado por impacto):{Colors.RESET}\n")
        for domain in sorted(by_domain.keys(), key=lambda d: -sum(r for _, r in by_domain[d])):
            tables = by_domain[domain]
            total_rows = sum(r for _, r in tables)
            print(f"  {Colors.CYAN}{domain}{Colors.RESET} ({len(tables)} tablas, {total_rows:,} filas total)")
            for table, rows in tables[:5]:
                print(f"    {Colors.YELLOW}{table:40s}{Colors.RESET} {rows:>12,} filas")
            if len(tables) > 5:
                print(f"    ... y {len(tables) - 5} tablas más")
            print()

        # E. High-impact recommendations
        print(f"\n{Colors.BOLD}  🎯 TABLAS DE ALTO IMPACTO (>10,000 filas, dominio de negocio):{Colors.RESET}\n")
        high_impact = [
            (t, r, guess_domain(t))
            for t, r in gap_tables.items()
            if r > 10000 and guess_domain(t) not in ("sistema", "otro")
        ]
        high_impact.sort(key=lambda x: -x[1])
        for table, rows, domain in high_impact[:15]:
            print(f"    {Colors.RED}{table:40s}{Colors.RESET} {rows:>12,} filas  [{domain}]")

        if not high_impact:
            print(f"    {Colors.GREEN}No hay tablas de alto impacto sin cubrir.{Colors.RESET}")

        # F. Bot coverage summary
        covered = len(bot_tables & set(t.lower() for t in all_tables))
        total_biz = len([t for t in all_tables if guess_domain(t) not in ("sistema", "otro")])
        print(f"\n{Colors.BOLD}  Cobertura del bot:{Colors.RESET}")
        print(f"    Tablas de negocio en iDempiere: {total_biz}")
        print(f"    Tablas que el bot consulta:     {covered}")
        print(f"    Cobertura:                      {100*covered//max(total_biz,1)}%")

    finally:
        db.close()

    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")


if __name__ == "__main__":
    main()
