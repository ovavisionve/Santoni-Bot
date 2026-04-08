"""
Golden tests runner — SantoniBot vs iDempiere.

Cada caso en cases.yaml se ejecuta dos veces:
  1. SQL directo contra iDempiere  → ground truth
  2. Pregunta al bot vía HTTP       → respuesta real

Luego compara ambas según el tipo de validación y reporta PASS/FAIL/DIFF
con el detalle de la diferencia.

Uso:
    # Desde el host, apuntando al backend en localhost:
    BOT_BASE_URL=http://localhost:8000 \\
    BOT_USERNAME=admin BOT_PASSWORD=... \\
    IDEMPIERE_PASSWORD=ova2026* \\
    python -m backend.tests.golden.runner

    # Desde dentro del contenedor backend:
    docker compose exec backend python -m tests.golden.runner

    # Solo ciertos casos:
    python -m backend.tests.golden.runner --only top_10_vendedores_inproa_usd_feb_2026

    # Verbose (muestra tablas):
    python -m backend.tests.golden.runner -v
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg2
import yaml


# ─────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────

CASES_PATH = Path(__file__).parent / "cases.yaml"

BOT_BASE_URL = os.getenv("BOT_BASE_URL", "http://localhost:8000")
BOT_USERNAME = os.getenv("BOT_USERNAME", "admin")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "")

IDEM_CONN = {
    "host": os.getenv("IDEMPIERE_HOST", "192.168.1.73"),
    "port": int(os.getenv("IDEMPIERE_PORT", "5432")),
    "database": os.getenv("IDEMPIERE_DATABASE", "idempiere_produccion"),
    "user": os.getenv("IDEMPIERE_USER", "ova"),
    "password": os.getenv("IDEMPIERE_PASSWORD", ""),
}


# ─────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class CaseResult:
    case_id: str
    agente: str
    pregunta: str
    passed: bool
    detalle: str
    bot_respuesta: str = ""
    ground_truth: Any = None
    ms_bot: float = 0.0
    ms_sql: float = 0.0


# ─────────────────────────────────────────────────────────────────────────
# Bot HTTP client
# ─────────────────────────────────────────────────────────────────────────

class BotClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token: str | None = None
        self.client = httpx.Client(timeout=120.0)

    def login(self) -> None:
        resp = self.client.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("access_token"):
            raise RuntimeError(f"Login devolvió sin token: {data}")
        self.token = data["access_token"]

    def ask(self, message: str) -> tuple[str, float]:
        """Envía una pregunta fresca (sin historial). Devuelve (respuesta_markdown, ms)."""
        if not self.token:
            self.login()
        start = time.perf_counter()
        resp = self.client.post(
            f"{self.base_url}/api/chat/",
            json={"message": message},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        return resp.json()["message"], elapsed_ms

    def close(self) -> None:
        self.client.close()


# ─────────────────────────────────────────────────────────────────────────
# iDempiere SQL runner
# ─────────────────────────────────────────────────────────────────────────

class IdempiereRunner:
    def __init__(self, conn_params: dict):
        self.conn = psycopg2.connect(**conn_params)
        self.conn.set_session(readonly=True)

    def run(self, sql: str) -> tuple[list[str], list[tuple], float]:
        start = time.perf_counter()
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []
        elapsed_ms = (time.perf_counter() - start) * 1000
        return cols, rows, elapsed_ms

    def close(self) -> None:
        self.conn.close()


# ─────────────────────────────────────────────────────────────────────────
# Markdown parsing
# ─────────────────────────────────────────────────────────────────────────

_NUM_RE = re.compile(r"-?\d[\d\.,]*")


def parse_number(s: str) -> float | None:
    """
    Parsea un número venezolano (1.234.567,89) o ISO (1,234,567.89).
    Devuelve None si no es parseable.
    """
    s = s.strip()
    if not s or s in ("-", "—", "N/A", "n/a"):
        return None
    # Quitar símbolos comunes
    s = s.replace("Bs.", "").replace("Bs", "").replace("$", "").replace("USD", "")
    s = s.replace("VES", "").replace("kg", "").replace("Kg", "").strip()
    # Si tiene punto Y coma, asumir formato venezolano (punto=miles, coma=decimal)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and s.count(",") == 1 and len(s.split(",")[1]) <= 2:
        # Única coma con <=2 dígitos después → decimal venezolano
        s = s.replace(",", ".")
    else:
        # Asumir formato con comas como miles
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def extract_all_numbers(text: str, exclude_years: bool = True) -> list[float]:
    """
    Extrae todos los números parseables del texto.
    Si exclude_years=True, filtra enteros 1900-2100 (probablemente años,
    no datos: el bot menciona "2026" en preguntas/respuestas constantemente).
    """
    nums = []
    for m in _NUM_RE.finditer(text):
        n = parse_number(m.group(0))
        if n is None:
            continue
        if exclude_years and 1900 <= n <= 2100 and n == int(n):
            continue
        nums.append(n)
    return nums


def _snippet(text: str, max_len: int = 280) -> str:
    """Snippet de una sola línea para mostrar en el reporte."""
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= max_len:
        return flat
    return flat[:max_len] + "…"


def parse_markdown_tables(md: str) -> list[list[dict[str, str]]]:
    """
    Extrae todas las tablas markdown del texto.
    Cada tabla es una lista de dicts {columna: valor} con headers normalizados.
    """
    tables = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Heurística: una línea que empieza con "|" y la siguiente es separador
        if line.startswith("|") and i + 1 < len(lines):
            sep = lines[i + 1].strip()
            if re.match(r"^\|[\s\-:|]+\|$", sep):
                headers = [h.strip() for h in line.strip("|").split("|")]
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                    if len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells)))
                    j += 1
                if rows:
                    tables.append(rows)
                i = j
                continue
        i += 1
    return tables


def normalize_label(s: str) -> str:
    """Normaliza un nombre para comparación tolerante: lower, sin acentos, sin espacios extra."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


# ─────────────────────────────────────────────────────────────────────────
# Comparators
# ─────────────────────────────────────────────────────────────────────────

def compare_scalar_exact(
    ground_truth: float, bot_response: str, tolerancia_pct: float = 0.005,
) -> tuple[bool, str]:
    # Si el ground truth ES un año, no filtrar años de la respuesta
    gt_is_year = 1900 <= ground_truth <= 2100 and ground_truth == int(ground_truth)
    nums = extract_all_numbers(bot_response, exclude_years=not gt_is_year)
    if not nums:
        return False, (
            f"Ground truth = {ground_truth:,.2f} pero la respuesta del bot no contiene "
            f"números parseables (excluyendo años). Snippet: {_snippet(bot_response)}"
        )
    # Buscar un número en la respuesta que haga match con tolerancia
    threshold = abs(ground_truth) * tolerancia_pct if ground_truth != 0 else 1e-9
    for n in nums:
        if abs(n - ground_truth) <= threshold:
            return True, f"Match: esperado {ground_truth:,.2f}, encontrado {n:,.2f} (tolerancia {tolerancia_pct*100:.2f}%)"
    # Mostrar top-3 más cercanos
    sorted_nums = sorted(set(nums), key=lambda x: abs(x - ground_truth))
    top3 = sorted_nums[:3]
    top3_str = ", ".join(f"{n:,.2f}" for n in top3)
    return False, (
        f"Esperado {ground_truth:,.2f} (tol {tolerancia_pct*100:.2f}%). "
        f"Top-3 candidatos en respuesta: [{top3_str}]. "
        f"Snippet: {_snippet(bot_response)}"
    )


def compare_count_exact(ground_truth: int, bot_response: str) -> tuple[bool, str]:
    gt_is_year = 1900 <= ground_truth <= 2100
    nums = extract_all_numbers(bot_response, exclude_years=not gt_is_year)
    int_nums = sorted({int(n) for n in nums if n == int(n) and abs(n) < 1e12})
    if ground_truth in int_nums:
        return True, f"Match exacto: {ground_truth}"
    if not int_nums:
        return False, (
            f"Esperado conteo = {ground_truth}, sin enteros en respuesta. "
            f"Snippet: {_snippet(bot_response)}"
        )
    sorted_nums = sorted(int_nums, key=lambda x: abs(x - ground_truth))
    top3 = sorted_nums[:3]
    top3_str = ", ".join(str(n) for n in top3)
    return False, (
        f"Esperado {ground_truth}. Top-3 enteros candidatos: [{top3_str}]. "
        f"Snippet: {_snippet(bot_response)}"
    )


def compare_ordered_table(
    ground_truth_rows: list[tuple],
    ground_truth_cols: list[str],
    bot_response: str,
    columna_etiqueta: str,
    columna_valor: str,
    tolerancia_pct: float = 0.01,
    posicion_estricta: bool = True,
) -> tuple[bool, str]:
    """Compara una tabla ordenada (top-N)."""
    if not ground_truth_rows:
        return False, "Ground truth vacío (SQL no devolvió filas)"

    label_idx = ground_truth_cols.index(columna_etiqueta)
    value_idx = ground_truth_cols.index(columna_valor)
    expected = [
        (normalize_label(str(r[label_idx])), float(r[value_idx]))
        for r in ground_truth_rows
    ]

    bot_tables = parse_markdown_tables(bot_response)
    if not bot_tables:
        return False, f"Ground truth tiene {len(expected)} filas pero el bot no devolvió tablas markdown"

    # Elegir la tabla más grande (suele ser la principal)
    bot_rows = max(bot_tables, key=len)

    # Buscar qué columna del bot contiene las etiquetas esperadas
    bot_headers = list(bot_rows[0].keys())
    label_col = None
    for col in bot_headers:
        norm_values = {normalize_label(row[col]) for row in bot_rows}
        overlap = sum(1 for exp_label, _ in expected if any(exp_label in nv or nv in exp_label for nv in norm_values))
        if overlap >= len(expected) * 0.5:
            label_col = col
            break
    if label_col is None:
        return False, f"No encontré columna de etiquetas en la tabla del bot. Headers: {bot_headers}"

    # Construir lista ordenada del bot según su propio orden
    bot_ordered = []
    for row in bot_rows:
        label = normalize_label(row[label_col])
        nums_in_row = []
        for col, val in row.items():
            if col == label_col:
                continue
            n = parse_number(val)
            if n is None:
                continue
            # Filtrar años (1900-2100) de las celdas, salvo que la columna parezca ser de año
            if 1900 <= n <= 2100 and n == int(n) and "año" not in col.lower() and "year" not in col.lower():
                continue
            nums_in_row.append(n)
        bot_ordered.append((label, nums_in_row))

    # Validar
    mismatches = []
    for i, (exp_label, exp_value) in enumerate(expected):
        if i >= len(bot_ordered):
            mismatches.append(f"Pos {i+1}: esperado '{exp_label}' no está en la tabla del bot")
            continue
        bot_label, bot_nums = bot_ordered[i]
        # Match tolerante por substring normalizado
        label_ok = (exp_label in bot_label) or (bot_label in exp_label)
        # Buscar el valor esperado en la fila del bot
        threshold = abs(exp_value) * tolerancia_pct if exp_value != 0 else 1e-9
        value_ok = any(abs(n - exp_value) <= threshold for n in bot_nums)
        if posicion_estricta and not label_ok:
            mismatches.append(f"Pos {i+1}: esperado '{exp_label}', bot muestra '{bot_label}'")
        if not value_ok:
            if bot_nums:
                closest = min(bot_nums, key=lambda x: abs(x - exp_value))
                mismatches.append(
                    f"Pos {i+1} ({exp_label}): valor esperado {exp_value:,.2f}, "
                    f"más cercano en fila {closest:,.2f}"
                )
            else:
                mismatches.append(f"Pos {i+1} ({exp_label}): fila del bot sin números parseables")

    if not mismatches:
        return True, f"Todas las {len(expected)} filas coinciden (etiqueta + valor + posición)"
    return False, "\n    ".join(mismatches[:10])


# ─────────────────────────────────────────────────────────────────────────
# Runner principal
# ─────────────────────────────────────────────────────────────────────────

def run_case(
    case: dict, bot: BotClient, idem: IdempiereRunner, verbose: bool = False,
) -> CaseResult:
    case_id = case["id"]
    pregunta = case["pregunta"]
    agente = case.get("agente", "?")

    # 1. Ground truth SQL
    gt_spec = case["ground_truth"]
    sql = gt_spec["sql"]
    extraer = gt_spec.get("extraer", "scalar")

    try:
        cols, rows, ms_sql = idem.run(sql)
    except Exception as exc:
        return CaseResult(
            case_id=case_id, agente=agente, pregunta=pregunta,
            passed=False, detalle=f"SQL error: {type(exc).__name__}: {exc}",
        )

    if extraer == "scalar":
        if not rows or not rows[0]:
            return CaseResult(
                case_id=case_id, agente=agente, pregunta=pregunta,
                passed=False, detalle="SQL devolvió sin filas", ms_sql=ms_sql,
            )
        ground_truth = float(rows[0][0]) if rows[0][0] is not None else 0.0
    else:
        ground_truth = (cols, rows)

    # 2. Preguntar al bot
    try:
        bot_response, ms_bot = bot.ask(pregunta)
    except Exception as exc:
        return CaseResult(
            case_id=case_id, agente=agente, pregunta=pregunta,
            passed=False, detalle=f"Bot error: {type(exc).__name__}: {exc}",
            ground_truth=ground_truth, ms_sql=ms_sql,
        )

    # 3. Comparar
    val_spec = case["validar"]
    tipo = val_spec["tipo"]

    if tipo == "valor_exacto":
        tol = val_spec.get("tolerancia_pct", 0.005)
        passed, detalle = compare_scalar_exact(ground_truth, bot_response, tol)
    elif tipo == "conteo_exacto":
        passed, detalle = compare_count_exact(int(ground_truth), bot_response)
    elif tipo == "tabla_ordenada":
        cols, rows = ground_truth
        passed, detalle = compare_ordered_table(
            rows, cols, bot_response,
            columna_etiqueta=val_spec["columna_etiqueta"],
            columna_valor=val_spec["columna_valor"],
            tolerancia_pct=val_spec.get("tolerancia_pct", 0.01),
            posicion_estricta=val_spec.get("posicion_estricta", True),
        )
    else:
        passed, detalle = False, f"Tipo de validación desconocido: {tipo}"

    result = CaseResult(
        case_id=case_id, agente=agente, pregunta=pregunta,
        passed=passed, detalle=detalle,
        bot_respuesta=bot_response if verbose else "",
        ground_truth=ground_truth if verbose else None,
        ms_bot=ms_bot, ms_sql=ms_sql,
    )
    return result


def print_report(results: list[CaseResult], verbose: bool = False) -> int:
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    width = 78

    print("\n" + "=" * width)
    print(f"  GOLDEN TESTS — SantoniBot vs iDempiere")
    print("=" * width)
    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        print(f"\n[{icon}] {r.case_id}  ({r.agente})")
        print(f"       pregunta: {r.pregunta}")
        print(f"       timing:   bot {r.ms_bot:.0f}ms, sql {r.ms_sql:.0f}ms")
        print(f"       detalle:  {r.detalle}")
        if verbose and r.bot_respuesta:
            snippet = r.bot_respuesta[:500].replace("\n", "\n         ")
            print(f"       bot ▶ {snippet}")

    print("\n" + "=" * width)
    print(f"  TOTAL: {passed}/{len(results)} PASS   {failed}/{len(results)} FAIL")
    print("=" * width + "\n")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden tests SantoniBot vs iDempiere")
    parser.add_argument("--only", help="Correr solo casos cuyo id coincida con este substring")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mostrar respuestas completas del bot")
    args = parser.parse_args()

    if not BOT_PASSWORD:
        print("ERROR: define BOT_PASSWORD en el entorno", file=sys.stderr)
        return 2
    if not IDEM_CONN["password"]:
        print("ERROR: define IDEMPIERE_PASSWORD en el entorno", file=sys.stderr)
        return 2

    with open(CASES_PATH) as f:
        cases_doc = yaml.safe_load(f)
    casos = cases_doc.get("casos", [])
    if args.only:
        casos = [c for c in casos if args.only in c["id"]]
    if not casos:
        print("No hay casos que correr")
        return 1

    print(f"Cargados {len(casos)} casos desde {CASES_PATH.name}")
    print(f"Bot:       {BOT_BASE_URL}")
    print(f"iDempiere: {IDEM_CONN['host']}/{IDEM_CONN['database']}")

    bot = BotClient(BOT_BASE_URL, BOT_USERNAME, BOT_PASSWORD)
    idem = IdempiereRunner(IDEM_CONN)
    try:
        print("Login bot...", end=" ")
        bot.login()
        print("OK")

        results = []
        for i, caso in enumerate(casos, 1):
            print(f"[{i}/{len(casos)}] {caso['id']}...", end=" ", flush=True)
            r = run_case(caso, bot, idem, verbose=args.verbose)
            results.append(r)
            print("PASS" if r.passed else "FAIL")
    finally:
        bot.close()
        idem.close()

    return print_report(results, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
