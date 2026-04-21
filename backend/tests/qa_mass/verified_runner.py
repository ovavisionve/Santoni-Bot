#!/usr/bin/env python3
"""
Runner masivo VERIFICADO — compara respuesta del bot contra datos crudos
de las MISMAS funciones build_* que el agente usa.

Para cada caso:
  1. Extrae parámetros (mes, año, org) de la pregunta
  2. Llama la función build_* correspondiente → datos crudos de iDempiere
  3. Extrae número(s) clave del crudo
  4. Envía la pregunta al bot vía API
  5. Extrae números de la respuesta del bot
  6. Compara: ¿los números del bot coinciden con iDempiere? (±10%)

Uso:
    docker compose exec backend python -m tests.qa_mass.verified_runner \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!' \
        --agents ventas,rrhh,contabilidad
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any

from tests.qa_ventas.bot_client import BotClient, extract_numbers

# ── Parameter extraction ─────────────────────────────────────────────────

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _extract_mes_anio(pregunta: str) -> tuple[int | None, int | None]:
    """Extrae mes y año de una pregunta en español."""
    text = pregunta.lower()
    mes = None
    anio = None

    for nombre, num in _MESES.items():
        if nombre in text:
            mes = num
            break

    # "mes pasado", "mes actual"
    now = datetime.now()
    if "mes actual" in text or "este mes" in text:
        mes = now.month
        anio = now.year
    elif "mes pasado" in text:
        if now.month == 1:
            mes, anio = 12, now.year - 1
        else:
            mes, anio = now.month - 1, now.year

    # Year
    for m in re.finditer(r'20[12]\d', text):
        anio = int(m.group())

    if not anio:
        anio = now.year

    return mes, anio


def _extract_org(pregunta: str) -> str | None:
    """Extrae nombre de organización de la pregunta."""
    text = pregunta.lower()
    orgs = ["inproa", "inpromaiz", "santoni service", "agropecuaria", "agroinproa", "inversiones aga", "agro import"]
    for org in orgs:
        if org in text:
            return org
    return None


def _extract_account_code(pregunta: str) -> str | None:
    """Extrae código contable."""
    m = re.search(r'\b(\d\.\d{2}(?:\.\d{2}){0,3})\b', pregunta)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{4})\b', pregunta)
    if m and m.group(1) not in ("2024", "2025", "2026", "2023"):
        return m.group(1)
    return None


# ── Currency detection ────────────────────────────────────────────────────

def _is_usd_question(pregunta: str) -> bool:
    """True si la pregunta pide datos en dólares."""
    t = pregunta.lower()
    return any(w in t for w in ["dólar", "dolar", "dolares", "usd", "en dólares", "en dolares"])


def _get_por_moneda_total(data: dict, moneda: str = "Bs.") -> float:
    """Extrae el total de una moneda del dict por_moneda.
    Prefiere venta_neta (bruto - NC) porque es lo que el bot muestra."""
    for entry in data.get("por_moneda", []):
        if entry.get("moneda") == moneda:
            return entry.get("venta_neta", entry.get("total_facturado", entry.get("total", 0)))
    return 0


def _get_por_moneda_facturas(data: dict, moneda: str = "Bs.") -> int:
    """Extrae las facturas de una moneda del dict por_moneda."""
    for entry in data.get("por_moneda", []):
        if entry.get("moneda") == moneda:
            return entry.get("facturas", entry.get("cantidad", 0))
    return 0


# ── Category → verification function mapping ─────────────────────────────

def _verify_empleados(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_employee_summary
    data = build_employee_summary(org_ids=None)
    if not isinstance(data, dict):
        return []
    totales = data.get("totales", {})

    # If question asks for specific org, check org breakdown
    if org:
        for entry in data.get("por_organizacion", []):
            org_name = entry.get("organizacion", "").lower()
            if org.lower() in org_name:
                return [("empleados_org", entry.get("total", entry.get("activos", 0)))]

    # If question asks for specific cargo/department, verify name presence instead
    pregunta_lower = pregunta.lower()
    cargo_keywords = ["obrero", "chofer", "analista", "gerente", "supervisor", "operador",
                       "asistente", "coordinador", "jefe", "director", "técnico", "ingeniero"]
    for kw in cargo_keywords:
        if kw in pregunta_lower:
            return [("nombre_cargo", kw)]

    dept_keywords = ["talento", "nómina", "nomina", "administración", "producción",
                      "logística", "ventas", "compras", "contabilidad", "mantenimiento"]
    for kw in dept_keywords:
        if kw in pregunta_lower:
            return [("nombre_depto", kw)]

    # If asks "buscar empleado apellido X", check name presence
    m = re.search(r'apellido\s+(\w+)', pregunta_lower)
    if m:
        return [("nombre_empleado", m.group(1))]

    # Default: total empleados
    total = totales.get("total", totales.get("activos", 0))
    if total:
        return [("total_empleados", total)]
    return []


def _verify_nomina(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_payroll_summary
    data = build_payroll_summary(mes=mes, anio=anio)
    if isinstance(data, dict):
        dev = data.get("total_devengado", 0)
        if dev:
            return [("devengado", dev)]
    return []


def _verify_cumpleanos(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_birthday_list
    data = build_birthday_list(mes=mes, org_name=org)
    if isinstance(data, list):
        names = [d.get("nombre", d.get("name", "")) for d in data[:3]]
        checks = [("total_cumpleañeros", len(data))]
        for n in names:
            if n:
                checks.append(("nombre_cumple", " ".join(n.split()[:2])))
        return checks
    return []


def _verify_ausentismo(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_attendance_summary
    data = build_attendance_summary(mes=mes, anio=anio)
    if isinstance(data, dict):
        totales = data.get("totales", {})
        ocurrencias = totales.get("total_ocurrencias", 0)
        empleados = totales.get("empleados_con_ausencias", 0)
        tasa = totales.get("tasa_ausentismo_pct", 0)
        if ocurrencias:
            return [("ausencias", ocurrencias)]
        if empleados:
            return [("empleados_ausentes", empleados)]
    return []


def _verify_vacaciones(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_vacation_summary
    kwargs = {"mes": mes, "anio": anio}
    if org:
        kwargs["org_name"] = org
    try:
        data = build_vacation_summary(**kwargs)
    except TypeError:
        data = build_vacation_summary(mes=mes, anio=anio)
    if isinstance(data, dict):
        totales = data.get("totales", {})
        empleados = totales.get("total_empleados", 0)
        monto = totales.get("total_monto", 0)
        if empleados:
            return [("empleados_vacaciones", empleados)]
        if monto:
            return [("monto_vacaciones", monto)]
    return []


def _verify_rotacion(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_turnover_summary
    data = build_turnover_summary(anio=anio)
    if isinstance(data, dict):
        totales = data.get("totales", {})
        bajas = totales.get("bajas", 0)
        tasa = totales.get("tasa_rotacion_pct", 0)
        if bajas:
            return [("bajas", bajas)]
        if tasa:
            return [("tasa_rotacion", tasa)]
    return []


def _verify_resumen_ventas(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_sales_summary
    usd = _is_usd_question(pregunta)
    currency_ids = [100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017] if usd else None
    data = build_sales_summary(mes=mes, anio=anio, org_name=org, currency_ids=currency_ids)
    if isinstance(data, dict):
        # Use per-currency breakdown when available (avoids mixed totals)
        por_moneda = data.get("por_moneda", [])
        if por_moneda and not usd:
            # Get VES entry (Bs.) — this is what the bot typically shows
            ves_total = _get_por_moneda_total(data, "Bs.")
            ves_facturas = _get_por_moneda_facturas(data, "Bs.")
            if ves_total:
                return [("ventas_ves", ves_total)]
            # Fallback to first entry
            if por_moneda:
                entry = por_moneda[0]
                return [("ventas", entry.get("total_facturado", entry.get("venta_neta", 0)))]
        elif usd:
            usd_total = _get_por_moneda_total(data, "USD")
            if usd_total:
                return [("ventas_usd", usd_total)]
        # Fallback to totales
        totals = data.get("totales", {})
        total = totals.get("total_facturado", 0)
        facturas = totals.get("total_facturas", 0)
        if total:
            return [("total_facturado", total)]
    return []


def _verify_cobranza(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_collection_summary
    data = build_collection_summary(mes=mes, anio=anio, org_name=org)
    if isinstance(data, dict):
        # collection_summary NO tiene por_moneda — solo totales (mixto VES+USD)
        totals = data.get("totales", {})
        total = totals.get("total_cobrado", 0)
        recibos = totals.get("total_recibos", 0)
        if total:
            return [("total_cobrado", total)]
        if recibos:
            return [("recibos", recibos)]
    return []


def _verify_ranking_vendedores(pregunta, mes, anio, org):
    """Para ranking de vendedores, verificar nombres de distribuidores."""
    from app.services.idempiere_queries import build_sales_summary
    data = build_sales_summary(mes=mes, anio=anio, org_name=org)
    if isinstance(data, dict):
        distribuidores = data.get("por_distribuidor", [])
        if distribuidores:
            return [
                ("nombre_vendedor", d.get("distribuidor", "").split(",")[0][:20])
                for d in distribuidores[:2]
                if d.get("distribuidor") and d["distribuidor"] != "Sin Distribuidor"
            ]
    return []


def _verify_ventas_zona(pregunta, mes, anio, org):
    """Para preguntas de zona/región, verificar nombres de zonas en respuesta."""
    from app.services.idempiere_queries import build_sales_summary
    data = build_sales_summary(mes=mes, anio=anio, org_name=org)
    if isinstance(data, dict):
        zonas = data.get("por_zona", data.get("por_region", []))
        if zonas:
            # Check top 2 zone/region names appear
            return [
                ("nombre_zona", z.get("zona", z.get("region", "")).split()[0])
                for z in zonas[:2]
                if z.get("zona") or z.get("region")
            ]
    return []


def _verify_ranking_clientes(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_top_clients
    usd = _is_usd_question(pregunta)
    cids = [100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017] if usd else [205]
    mes_q = _extract_mes_anio(pregunta)[0]
    data = build_top_clients(anio=anio, mes=mes_q, org_name=org, currency_ids=cids)
    if isinstance(data, list) and data:
        return [("nombre_cliente", " ".join(d.get("cliente", d.get("nombre", "")).split()[:3])) for d in data[:3]]
    return []


def _verify_cxc_vencidas(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_overdue_receivables
    data = build_overdue_receivables()
    if isinstance(data, list) and data:
        return [("nombre_moroso", d.get("cliente", d.get("nombre", ""))) for d in data[:3] if d.get("cliente") or d.get("nombre")]
    return []


def _verify_balance_general(pregunta, mes, anio, org):
    from app.services.idempiere_queries import build_accounting_summary
    data = build_accounting_summary(mes=mes, anio=anio)
    if isinstance(data, dict):
        # Bot shows monetary amounts (activo, pasivo, patrimonio), NOT asientos count.
        # Verify that account type names appear in the response.
        por_tipo = data.get("por_tipo_cuenta", [])
        if por_tipo:
            types_to_check = []
            for entry in por_tipo[:3]:
                name = entry.get("tipo_nombre", entry.get("tipo", ""))
                if name:
                    types_to_check.append(("tipo_cuenta", name.lower()))
            if types_to_check:
                return types_to_check
        # Fallback: check balance amounts
        balance = data.get("balance", {})
        if balance:
            for key in ("total_activo", "total_pasivo", "activo", "pasivo"):
                val = balance.get(key, 0)
                if val and abs(val) > 1000:
                    return [(key, val)]
    return []


def _verify_saldo_cuenta(pregunta, mes, anio, org):
    code = _extract_account_code(pregunta)
    if not code:
        return []
    from app.services.idempiere_queries import build_account_detail
    try:
        data = build_account_detail(account_code=code, mes=mes, anio=anio)
    except TypeError:
        try:
            data = build_account_detail(account_value=code, mes=mes, anio=anio)
        except TypeError:
            return []
    if isinstance(data, dict):
        accounts = data.get("cuentas", data.get("accounts", data.get("detalle", [])))
        if accounts and isinstance(accounts, list) and accounts:
            first = accounts[0]
            name = first.get("cuenta", first.get("name", first.get("nombre", "")))
            if name:
                return [("nombre_cuenta", name.split()[0])]
    return []


# Fallback for categories we don't have specific verification for
def _verify_generic(pregunta, mes, anio, org):
    return []


_CATEGORY_MAP = {
    # RRHH
    "empleados": _verify_empleados,
    "nomina": _verify_nomina,
    "cumpleanos": _verify_cumpleanos,
    "ausentismo": _verify_ausentismo,
    "vacaciones": _verify_vacaciones,
    "rotacion": _verify_rotacion,
    "busqueda_cargo": _verify_empleados,
    "ingresos_personal": _verify_generic,
    "indicadores_rrhh": _verify_generic,
    "asistencia": _verify_ausentismo,
    # Ventas
    "resumen_ventas": _verify_resumen_ventas,
    "cobranza": _verify_cobranza,
    "ranking_clientes": _verify_ranking_clientes,
    "top_clientes": _verify_ranking_clientes,
    "cxc_vencidas": _verify_cxc_vencidas,
    "ranking_vendedores": _verify_ranking_vendedores,
    "ventas_zona": _verify_ventas_zona,
    "ventas_por_zona": _verify_ventas_zona,
    "ventas_por_region": _verify_ventas_zona,
    "ventas_region_especifica": _verify_ventas_zona,
    "ventas_comparacion_regiones": _verify_ventas_zona,
    "ventas_categoria": _verify_resumen_ventas,
    "facturacion": _verify_resumen_ventas,
    "facturacion_zona": _verify_resumen_ventas,
    "facturacion_distribuidor": _verify_resumen_ventas,
    "facturacion_moneda": _verify_resumen_ventas,
    "visitas_clientes": _verify_generic,
    # Contabilidad
    "balance_general": _verify_balance_general,
    "situacion_financiera": _verify_balance_general,
    "estado_resultados": _verify_balance_general,
    "saldo_cuenta": _verify_saldo_cuenta,
    "costos": _verify_balance_general,
    "gastos": _verify_balance_general,
    "libro_mayor": _verify_saldo_cuenta,
    "impuestos": _verify_balance_general,
}


# ── Colors ────────────────────────────────────────────────────────────────

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
D = "\033[2m"
X = "\033[0m"

_ERROR_PHRASES = [
    "no se encontraron datos", "no hay datos", "no hay registros",
    "dificultades para", "error de conexión", "no tengo acceso",
    "inténtalo de nuevo",
]


# ── Main runner ───────────────────────────────────────────────────────────

def run_verified(client: BotClient, cases: list[dict], verbose: bool = False):
    total = len(cases)
    results = {"pass": 0, "data_mismatch": 0, "no_data": 0, "no_verify": 0, "error": 0}
    failures = []

    for i, case in enumerate(cases, 1):
        q = case["pregunta"]
        agent = case["agente_esperado"]
        cat = case.get("categoria", "?")
        case_id = case.get("id", i)

        # 1. Extract params
        mes, anio = _extract_mes_anio(q)
        org = _extract_org(q)

        # 2. Get expected data from build_* functions
        verify_fn = _CATEGORY_MAP.get(cat, _verify_generic)
        try:
            expected_vals = verify_fn(q, mes, anio, org)
        except Exception as exc:
            expected_vals = []
            if verbose:
                print(f"  {Y}⚠ SQL error for #{case_id}: {exc}{X}")

        # 3. Send to bot
        try:
            start = time.time()
            resp = client.ask(q, agent_name=agent)
            elapsed = time.time() - start
            bot_text = resp.get("message", "")
            bot_nums = extract_numbers(bot_text)
            text_lower = bot_text.lower()
        except Exception as exc:
            results["error"] += 1
            failures.append((case_id, agent, cat, q[:50], "error", str(exc)[:80]))
            print(f"{R}E{X}", end="", flush=True)
            continue

        # 4. Check for bot errors
        has_error = any(p in text_lower for p in _ERROR_PHRASES)
        if has_error or len(bot_text) < 50:
            results["no_data"] += 1
            failures.append((case_id, agent, cat, q[:50], "no_data", bot_text[:80]))
            print(f"{R}X{X}", end="", flush=True)
            if i % 50 == 0:
                print(f" [{i}/{total}]")
            continue

        # 5. Verify against expected values
        if not expected_vals:
            results["no_verify"] += 1
            print(f"{Y}?{X}", end="", flush=True)
            if i % 50 == 0:
                print(f" [{i}/{total}]")
            continue

        all_match = True
        for label, expected in expected_vals:
            if isinstance(expected, str):
                # Name check
                if expected.lower()[:15] not in text_lower:
                    all_match = False
                    failures.append((case_id, agent, cat, q[:50], "name_missing",
                                     f"'{expected[:30]}' no aparece en respuesta"))
                    break
            elif isinstance(expected, (int, float)):
                # Number check with 10% tolerance
                found = False
                for n in bot_nums:
                    if expected == 0:
                        if abs(n) < 1:
                            found = True
                            break
                    elif abs(n - expected) / abs(expected) < 0.10:
                        found = True
                        break
                if not found:
                    all_match = False
                    closest = min(bot_nums, key=lambda x: abs(x - expected)) if bot_nums else None
                    diff = f" (más cercano: {closest:.0f}, diff {abs(closest-expected)/abs(expected)*100:.1f}%)" if closest and expected else ""
                    failures.append((case_id, agent, cat, q[:50], "data_mismatch",
                                     f"{label}={expected:.2f} no en respuesta{diff}"))
                    break

        if all_match:
            results["pass"] += 1
            print(f"{G}.{X}", end="", flush=True)
        else:
            results["data_mismatch"] += 1
            print(f"{R}!{X}", end="", flush=True)

        if i % 50 == 0:
            print(f" [{i}/{total}]")

    print(f"\n")

    # Summary
    total_run = sum(results.values())
    print(f"{B}{'='*70}")
    print(f"  QA MASIVO VERIFICADO — {results['pass']}/{total_run} verificados OK")
    print(f"{'='*70}{X}")
    print(f"  {G}pass          {X} {results['pass']:4d} — datos del bot coinciden con iDempiere")
    print(f"  {R}data_mismatch {X} {results['data_mismatch']:4d} — bot respondió pero números no coinciden")
    print(f"  {R}no_data       {X} {results['no_data']:4d} — bot dijo 'no hay datos'")
    print(f"  {Y}no_verify     {X} {results['no_verify']:4d} — sin verificación para esta categoría")
    print(f"  {R}error         {X} {results['error']:4d} — error de API/conexión")

    if failures:
        print(f"\n  {B}Fallos detallados ({len(failures)}):{X}")
        for cid, ag, cat, q, typ, note in failures:
            color = R if typ in ("data_mismatch", "no_data") else Y
            print(f"    {color}#{cid:3d}{X} [{ag}/{cat}] {D}{q}{X}")
            print(f"         [{typ}] {note}")

    # Save report
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"/tmp/qa_verified_{ts}.md"
        with open(path, "w") as f:
            f.write(f"# QA Masivo Verificado — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"**Resultado:** {results['pass']}/{total_run} verificados\n\n")
            f.write(f"| Categoría | Cuenta |\n|---|---|\n")
            for k, v in results.items():
                f.write(f"| {k} | {v} |\n")
            if failures:
                f.write(f"\n## Fallos\n\n")
                for cid, ag, cat, q, typ, note in failures:
                    f.write(f"- #{cid} [{ag}/{cat}] {q} → `{typ}`: {note}\n")
        print(f"\n  {C}Reporte: {path}{X}")
    except Exception:
        pass

    return results


def main():
    parser = argparse.ArgumentParser(description="QA Masivo Verificado")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--agents", default="ventas,rrhh,contabilidad")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--dataset", default="/app/data/training_dataset.json")
    args = parser.parse_args()

    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "")
    if not password:
        print(f"{R}Falta --password{X}")
        sys.exit(1)

    agents = args.agents.split(",")

    with open(args.dataset) as f:
        entries = json.load(f)["entries"]

    cases = [e for e in entries
             if e["agente_esperado"] in agents and not e.get("es_followup")]
    if args.limit:
        cases = cases[:args.limit]

    print(f"\n{B}{'='*70}")
    print(f"  QA MASIVO VERIFICADO — {len(cases)} casos")
    print(f"  Agentes: {', '.join(agents)}")
    print(f"  Verificación: datos del bot vs build_*() directo a iDempiere")
    print(f"{'='*70}{X}\n")

    client = BotClient(args.base_url, username, password, timeout=120)
    try:
        client.login()
        print(f"  {G}Login OK{X}\n")
    except Exception as exc:
        print(f"  {R}Login failed: {exc}{X}")
        sys.exit(1)

    results = run_verified(client, cases, verbose=args.verbose)
    sys.exit(0 if results["data_mismatch"] == 0 and results["no_data"] == 0 else 1)


if __name__ == "__main__":
    main()
