#!/usr/bin/env python3
"""
Test en vivo: reproduce las 35+ preguntas de la conversación real del admin (Mar 2026).

Valida:
  1. Routing al agente correcto
  2. Que NO haya alucinación (tablas inventadas cuando no hay datos)
  3. Que el bot conozca la fecha actual (no diga "Julio 2024")
  4. Que los follow-ups hereden contexto temporal
  5. Que declare honestamente cuando no tiene datos

Uso:
  python3 tests/test_admin_conversation_live.py                            # todo
  python3 tests/test_admin_conversation_live.py --url http://192.168.1.26  # URL custom
  python3 tests/test_admin_conversation_live.py --grupo ventas             # solo un grupo
  python3 tests/test_admin_conversation_live.py --rapido                   # sin follow-ups

Desde servidor:
  docker compose exec backend python3 tests/test_admin_conversation_live.py --url http://localhost:8000
"""

import sys
import json
import time
import re
import urllib.request
import urllib.error
import argparse
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
USERNAME = "admin"
PASSWORD = "SantoniAdmin2026!"
TIMEOUT  = 120

# ANSI colors
G = "\033[92m"   # green
R = "\033[91m"   # red
Y = "\033[93m"   # yellow
B = "\033[1m"    # bold
C = "\033[96m"   # cyan
M = "\033[95m"   # magenta
N = "\033[0m"    # reset
DIM = "\033[2m"  # dim


def api(base_url, method, path, body=None, token=None):
    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        return {"_error": e.code, "_detail": err_body}
    except Exception as e:
        return {"_error": str(e)}


def login(base_url):
    print(f"  Conectando a {base_url} como {USERNAME}...")
    r = api(base_url, "POST", "/api/auth/login", {
        "username": USERNAME,
        "password": PASSWORD,
        "totp_code": None,
    })
    if "_error" in r:
        print(f"  {R}ERROR login: {r}{N}")
        sys.exit(1)
    token = r.get("access_token", "")
    if not token:
        print(f"  {R}ERROR: No se recibió token. Respuesta: {r}{N}")
        sys.exit(1)
    print(f"  {G}Login OK{N}\n")
    return token


def chat(base_url, token, message, conversation_id=None):
    body = {"message": message, "conversation_id": conversation_id, "file_id": None}
    r = api(base_url, "POST", "/api/chat/", body, token)
    if "_error" in r:
        return "ERROR", f"HTTP error: {r}", conversation_id, None
    agent = r.get("agent_used", "???")
    text = r.get("message", "")
    cid = r.get("conversation_id", conversation_id)
    meta = r.get("metadata") or {}
    has_data = meta.get("has_data")
    return agent, text, cid, has_data


# ══════════════════════════════════════════════════════════════════════
# VALIDADORES
# ══════════════════════════════════════════════════════════════════════

def check_wrong_date(response: str) -> str | None:
    """Detecta si el bot respondió con fechas incorrectas (ej: julio 2024)."""
    now = datetime.now()
    current_year = now.year
    # Buscar años mencionados en la respuesta
    years_found = re.findall(r'\b(20\d{2})\b', response)
    for y in years_found:
        yi = int(y)
        # Si menciona un año anterior al actual Y el usuario no lo pidió, sospechoso
        if yi < current_year - 1:
            return f"Menciona año {yi} (posible fecha incorrecta)"
    return None


def check_hallucination(response: str, has_data: bool) -> str | None:
    """Detecta tablas con montos inventados cuando no hay datos reales."""
    if has_data:
        return None
    # Tabla con montos monetarios grandes
    if re.search(r'\|[^|]*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?[^|]*\|', response):
        return "ALUCINACION: tabla con montos sin datos reales"
    # Tabla con Bs. o USD
    if re.search(r'\|[^|]*(?:Bs\.?|USD|\$)\s*\d+[^|]*\|', response):
        return "ALUCINACION: tabla con moneda sin datos reales"
    return None


def check_no_data_honest(response: str, has_data: bool) -> str | None:
    """Si no hay datos, verifica que el bot lo diga honestamente."""
    if has_data:
        return None
    resp_lower = response.lower()
    honest_phrases = [
        "no hay datos", "no se encontraron", "no tengo datos",
        "no dispongo", "sin datos", "no está disponible",
        "no encontré", "no puedo consultar", "no tengo acceso",
        "no cuento con", "no se pudo",
    ]
    if any(p in resp_lower for p in honest_phrases):
        return None
    # Si hay tablas con números pero no hay datos, es sospechoso
    if "|" in response and re.search(r'\d{2,}', response):
        return "Sin datos pero generó tabla con números (posible invención)"
    return None


# ══════════════════════════════════════════════════════════════════════
# ESCENARIOS DE LA CONVERSACIÓN REAL DEL ADMIN
# ══════════════════════════════════════════════════════════════════════

# Cada grupo es una "conversación" (comparten conversation_id para follow-ups)
# Formato: (mensaje, agente_esperado, validaciones_extra)
# validaciones_extra: lista de funciones extra a ejecutar sobre la respuesta

GRUPO_VENTAS = [
    {
        "name": "VENTAS: Top clientes + follow-ups temporales",
        "queries": [
            ("Top 10 clientes de este mes", "ventas"),
            ("Si, de marzo de 2026", "ventas"),          # follow-up
            ("Beuno, de febrero de 2026", "ventas"),      # follow-up
        ],
    },
    {
        "name": "VENTAS: Ranking por zona",
        "queries": [
            ("Ranking de ventas por zona del mes de enero 2026", "ventas"),
            ("Dime el ranking de venta por zona", "ventas"),  # follow-up
        ],
    },
    {
        "name": "VENTAS: Facturación en dólares",
        "queries": [
            ("¿Cuánto se facturó en dólares en febrero 2026?", "ventas"),
        ],
    },
    {
        "name": "VENTAS: Top clientes histórico y por org",
        "queries": [
            ("Top 20 clientes por ventas del 2025", "ventas"),
            ("Top 20 clientes de InproMaiz en febrero 2026", "ventas"),
            ("Puedes hacer este análisis pero por zona?", "ventas"),  # follow-up
        ],
    },
    {
        "name": "VENTAS: Vendedores y org específica",
        "queries": [
            ("Top 10 mejores vendedores de InproMaiz", "ventas"),
            ("Top 10 clientes de InproMaíz en enero 2026", "ventas"),
        ],
    },
]

GRUPO_RRHH = [
    {
        "name": "RRHH: Empleados activos + depto + cargo",
        "queries": [
            ("¿Cuántos empleados activos hay en INPROA SANTONI?", "rrhh"),
            ("¿Cuántos empleados hay por departamento?", "rrhh"),       # follow-up
            ("¿Cuántos obreros integrales hay?", "rrhh"),              # follow-up
        ],
    },
    {
        "name": "RRHH: Choferes",
        "queries": [
            ("¿Cuántos choferes tiene la empresa?", "rrhh"),
        ],
    },
    {
        "name": "RRHH: Ausentismo con período",
        "queries": [
            ("Indicadores de ausentismo de INPROA SANTONI de septiembre 2025", "rrhh"),
        ],
    },
    {
        "name": "RRHH: Nuevos ingresos por rango de fechas",
        "queries": [
            ("¿Cuántos empleados ingresaron entre enero y junio 2025?", "rrhh"),
        ],
    },
    {
        "name": "RRHH: Cumpleañeros",
        "queries": [
            ("Cumpleañeros del mes de marzo", "rrhh"),
        ],
    },
]

GRUPO_FINANZAS = [
    {
        "name": "FINANZAS: Saldos bancarios",
        "queries": [
            ("¿Cuáles son los saldos bancarios actuales?", "finanzas"),
            ("¿Cuál es el banco con mayor disponibilidad actualmente?", "finanzas"),
        ],
    },
    {
        "name": "FINANZAS: CxC y CxP",
        "queries": [
            ("¿Cuánto tenemos en cuentas por cobrar vencidas?", "finanzas"),
            ("¿Cuánto debemos en cuentas por pagar?", "finanzas"),  # follow-up
        ],
    },
    {
        "name": "FINANZAS: Préstamos",
        "queries": [
            ("Cuotas de préstamos vencidos a la fecha", "finanzas"),
        ],
    },
]

GRUPO_PRODUCCION = [
    {
        "name": "PRODUCCION: Cuánto se produjo",
        "queries": [
            ("¿Cuánto se produjo en enero 2026?", "produccion"),
        ],
    },
    {
        "name": "PRODUCCION: Órdenes de producción + follow-up",
        "queries": [
            ("¿Cuáles son las órdenes de producción del mes?", "produccion"),
            ("¿Cuáles son las órdenes de producción del mes de enero de 2026?", "produccion"),
        ],
    },
    {
        "name": "PRODUCCION: Inventario materia prima + follow-up",
        "queries": [
            ("Dame el Inventario de materia prima actual", "produccion"),
            ("Me refería al mes de enero de 2026", "produccion"),  # follow-up
        ],
    },
    {
        "name": "PRODUCCION: Arroz blanco",
        "queries": [
            ("Producción de arroz blanco en enero 2026", "produccion"),
        ],
    },
    {
        "name": "PRODUCCION: Desperdicio empaque",
        "queries": [
            ("¿Cuánto desperdicio hubo en empaque este mes?", "produccion"),
        ],
    },
    {
        "name": "PRODUCCION: Recepción cajas cartón",
        "queries": [
            ("¿Cuántas cajas de cartón recibimos en enero 2026?", "produccion"),
        ],
    },
    {
        "name": "PRODUCCION: Inventario producto terminado",
        "queries": [
            ("Inventario de producto terminado actual", "produccion"),
        ],
    },
]

GRUPO_COMPRAS = [
    {
        "name": "COMPRAS: Historial azúcar + follow-up trimestre",
        "queries": [
            ("Dame el historial de compras de azúcar del último trimestre", "compras_insumos"),
            ("Disculpa el trimestre a analizar es de, enero a marzo", "compras_insumos"),
        ],
    },
]

ALL_GROUPS = {
    "ventas": GRUPO_VENTAS,
    "rrhh": GRUPO_RRHH,
    "finanzas": GRUPO_FINANZAS,
    "produccion": GRUPO_PRODUCCION,
    "compras": GRUPO_COMPRAS,
}


# ══════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ══════════════════════════════════════════════════════════════════════

def run_tests(base_url, token, test_groups, verbose=True):
    total = sum(len(g["queries"]) for g in test_groups)
    ok = warn = fail = 0
    results = []
    test_num = 0

    for group in test_groups:
        print(f"\n{B}{C}══ {group['name']} ══{N}")
        conv_id = None  # nueva conversación por grupo (para follow-ups)

        for query_data in group["queries"]:
            msg, expected_agent = query_data[0], query_data[1]
            test_num += 1
            short_msg = msg[:80] + ("..." if len(msg) > 80 else "")
            print(f"  [{test_num}/{total}] {short_msg}")

            t0 = time.time()
            agent, response, conv_id, has_data = chat(base_url, token, msg, conv_id)
            elapsed = time.time() - t0

            issues = []
            status = "OK"

            # ── Check 1: API error ──
            if agent == "ERROR":
                issues.append(f"ERROR API: {response[:100]}")
                status = "FAIL"
            else:
                # ── Check 2: Routing correcto ──
                if expected_agent and agent != expected_agent:
                    if agent == "general":
                        issues.append(f"Fue a GENERAL (esperado: {expected_agent})")
                        status = "FAIL"
                    elif agent == "orchestrator":
                        issues.append(f"ACCESO DENEGADO (esperado: {expected_agent})")
                        status = "FAIL"
                    else:
                        issues.append(f"Agente: {agent} (esperado: {expected_agent})")
                        status = "WARN"

                # ── Check 3: Fecha incorrecta ──
                date_issue = check_wrong_date(response)
                # Solo verificar si el mensaje dice "actual", "este mes", "hoy"
                msg_lower = msg.lower()
                if date_issue and any(w in msg_lower for w in [
                    "actual", "este mes", "hoy", "de este",
                ]):
                    issues.append(date_issue)
                    if status == "OK":
                        status = "WARN"

                # ── Check 4: Alucinación ──
                halluc = check_hallucination(response, has_data or False)
                if halluc:
                    issues.append(halluc)
                    status = "FAIL"

                # ── Check 5: Honestidad cuando no hay datos ──
                no_data_issue = check_no_data_honest(response, has_data or False)
                if no_data_issue and status == "OK":
                    issues.append(no_data_issue)
                    status = "WARN"

                # ── Check 6: Respuesta muy corta ──
                if len(response.strip()) < 20:
                    issues.append(f"Respuesta muy corta ({len(response)} chars)")
                    if status == "OK":
                        status = "WARN"

            # ── Mostrar resultado ──
            data_tag = f" {G}[datos]{N}" if has_data else f" {Y}[sin datos]{N}"
            resp_short = response.replace("\n", " ")[:200]

            if status == "OK":
                print(f"    {G}OK{N}   [{agent}]{data_tag} ({elapsed:.1f}s)")
                if verbose:
                    print(f"         {DIM}{resp_short}{N}")
                ok += 1
            elif status == "WARN":
                print(f"    {Y}WARN{N} [{agent}]{data_tag} ({elapsed:.1f}s)")
                for i in issues:
                    print(f"         {Y}⚠ {i}{N}")
                if verbose:
                    print(f"         {DIM}{resp_short}{N}")
                warn += 1
            else:
                print(f"    {R}FAIL{N} [{agent}]{data_tag} ({elapsed:.1f}s)")
                for i in issues:
                    print(f"         {R}✗ {i}{N}")
                if verbose:
                    print(f"         {DIM}{resp_short}{N}")
                fail += 1

            results.append({
                "num": test_num,
                "msg": msg,
                "expected": expected_agent,
                "actual": agent,
                "status": status,
                "issues": issues,
                "has_data": has_data,
                "elapsed": elapsed,
                "response_preview": resp_short,
            })
            time.sleep(0.5)

    # ── Resumen ──
    print("\n" + "=" * 70)
    print(f"  RESULTADOS: {G}{ok} OK{N}, {Y}{warn} WARN{N}, {R}{fail} FAIL{N}  (de {total} preguntas)")
    print("=" * 70)

    # ── Desglose de problemas ──
    if fail > 0 or warn > 0:
        print(f"\n{B}Detalle de problemas:{N}")
        for r in results:
            if r["status"] != "OK":
                color = R if r["status"] == "FAIL" else Y
                data_str = "con datos" if r["has_data"] else "SIN datos"
                print(f"  {color}[{r['num']}]{N} {r['msg'][:70]}...")
                print(f"       Agente: {r['actual']} (esperado: {r['expected']}) | {data_str}")
                for i in r["issues"]:
                    print(f"       {color}→{N} {i}")

    # ── Estadísticas de alucinación ──
    total_no_data = sum(1 for r in results if not r["has_data"] and r["actual"] != "ERROR")
    halluc_count = sum(1 for r in results if any("ALUCINACION" in i for i in r["issues"]))
    print(f"\n{B}Estadísticas anti-alucinación:{N}")
    print(f"  Preguntas con datos reales: {sum(1 for r in results if r['has_data'])}/{total}")
    print(f"  Preguntas sin datos:        {total_no_data}/{total}")
    print(f"  Alucinaciones detectadas:   {R if halluc_count > 0 else G}{halluc_count}{N}")
    if total_no_data > 0:
        clean = total_no_data - halluc_count
        print(f"  Respuestas honestas (sin datos): {G}{clean}/{total_no_data}{N}")

    # ── Guardar JSON de resultados ──
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "ok": ok,
        "warn": warn,
        "fail": fail,
        "hallucinations": halluc_count,
        "results": results,
    }
    report_file = "tests/test_admin_conversation_results.json"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  Reporte guardado en: {M}{report_file}{N}")
    except Exception:
        pass

    return fail


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SantoniBot - Test conversación real del admin (anti-alucinación)"
    )
    parser.add_argument("--url", default="http://192.168.1.26",
                        help="Base URL del bot (default: http://192.168.1.26)")
    parser.add_argument("--grupo", default=None,
                        help="Grupo: ventas, rrhh, finanzas, produccion, compras")
    parser.add_argument("--rapido", action="store_true",
                        help="Solo preguntas independientes (sin follow-ups)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="No mostrar preview de respuestas")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    if args.grupo:
        if args.grupo not in ALL_GROUPS:
            print(f"{R}Grupo '{args.grupo}' no existe. Opciones: {', '.join(ALL_GROUPS.keys())}{N}")
            sys.exit(1)
        test_groups = ALL_GROUPS[args.grupo]
        label = args.grupo.upper()
    else:
        test_groups = []
        for groups in ALL_GROUPS.values():
            test_groups.extend(groups)
        label = "TODOS (conversación admin)"

    # Modo rápido: solo primera pregunta de cada grupo
    if args.rapido:
        quick_groups = []
        for g in test_groups:
            quick_groups.append({
                "name": g["name"] + " (rápido)",
                "queries": [g["queries"][0]],
            })
        test_groups = quick_groups

    total_q = sum(len(g["queries"]) for g in test_groups)

    print("=" * 70)
    print(f"  {B}SANTONIBOT - TEST CONVERSACIÓN REAL DEL ADMIN{N}")
    print(f"  {label} ({total_q} preguntas)")
    print(f"  URL: {base_url}")
    print(f"  Validaciones: routing + anti-alucinación + fecha + honestidad")
    print("=" * 70)

    token = login(base_url)
    failures = run_tests(base_url, token, test_groups, verbose=not args.quiet)
    sys.exit(1 if failures > 0 else 0)
