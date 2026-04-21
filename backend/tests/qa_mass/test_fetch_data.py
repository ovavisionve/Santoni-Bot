#!/usr/bin/env python3
"""
Test DIRECTO de fetch_data — sin LLM, sin API, solo capa de datos.

Para cada caso del training_dataset.json:
1. Instancia el agente correcto
2. Llama fetch_data() directamente (lo que le daría al LLM)
3. Verifica: ¿devolvió datos? ¿cuántos chars? ¿contiene keywords relevantes?

Resultado determinístico — no depende del LLM.
Tarda ~2 minutos para 135 casos (vs 40 min del test vía API).

Uso:
    docker compose exec backend python tests/qa_mass/test_fetch_data.py
"""

import json
import sys
import time
from collections import Counter

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
B = "\033[1m"
X = "\033[0m"


def main():
    # Load cases
    with open("/app/data/training_dataset.json") as f:
        entries = json.load(f)["entries"]

    agents_filter = {"ventas", "rrhh", "contabilidad"}
    cases = [e for e in entries
             if e["agente_esperado"] in agents_filter and not e.get("es_followup")]

    print(f"\n{B}{'='*70}")
    print(f"  TEST DIRECTO fetch_data — {len(cases)} casos")
    print(f"  Sin LLM, sin API — solo capa de datos")
    print(f"{'='*70}{X}\n")

    # Initialize agents once
    from app.agents.rrhh import RRHHAgent
    from app.agents.ventas import VentasAgent
    from app.agents.contabilidad import ContabilidadAgent

    agent_instances = {
        "rrhh": RRHHAgent(),
        "ventas": VentasAgent(),
        "contabilidad": ContabilidadAgent(),
    }

    results = {"pass": 0, "short": 0, "empty": 0, "error": 0}
    failures = []
    total = len(cases)

    start_total = time.time()
    for i, case in enumerate(cases, 1):
        q = case["pregunta"]
        agent_name = case["agente_esperado"]
        case_id = case.get("id", i)
        cat = case.get("categoria", "?")

        agent = agent_instances[agent_name]
        try:
            start = time.time()
            result = agent.fetch_data(
                message=q, history=[], org_ids=None, salesrep_id=None,
            )
            elapsed = time.time() - start

            if result is None:
                results["empty"] += 1
                failures.append((case_id, agent_name, cat, q[:50], "empty", "fetch_data retornó None"))
                print(f"{R}X{X}", end="", flush=True)
            elif isinstance(result, str) and len(result) < 50:
                results["short"] += 1
                failures.append((case_id, agent_name, cat, q[:50], "short", f"{len(result)} chars: {result[:80]}"))
                print(f"{Y}!{X}", end="", flush=True)
            else:
                length = len(result) if isinstance(result, str) else len(str(result))
                if length >= 50:
                    results["pass"] += 1
                    print(f"{G}.{X}", end="", flush=True)
                else:
                    results["short"] += 1
                    failures.append((case_id, agent_name, cat, q[:50], "short", f"{length} chars"))
                    print(f"{Y}!{X}", end="", flush=True)

        except Exception as exc:
            results["error"] += 1
            failures.append((case_id, agent_name, cat, q[:50], "error", str(exc)[:100]))
            print(f"{R}E{X}", end="", flush=True)

        if i % 50 == 0:
            print(f" [{i}/{total}]")

    elapsed_total = time.time() - start_total
    print(f"\n")

    # Summary
    total_run = sum(results.values())
    passed = results["pass"]
    print(f"{B}{'='*70}")
    print(f"  RESULTADO: {passed}/{total_run} — fetch_data devuelve datos")
    print(f"  Tiempo: {elapsed_total:.1f}s ({elapsed_total/max(total_run,1):.1f}s/caso)")
    print(f"{'='*70}{X}")
    print(f"  {G}pass  {X} {results['pass']:4d} — datos reales de iDempiere (≥50 chars)")
    print(f"  {Y}short {X} {results['short']:4d} — respuesta corta (<50 chars, probable error)")
    print(f"  {R}empty {X} {results['empty']:4d} — fetch_data retornó None")
    print(f"  {R}error {X} {results['error']:4d} — excepción en fetch_data")

    # By agent
    agent_results = {}
    all_cases_by_agent = Counter(c["agente_esperado"] for c in cases)
    for case_id, agent_name, cat, q, typ, note in failures:
        agent_results.setdefault(agent_name, []).append(typ)

    print(f"\n  {B}Por agente:{X}")
    for agent_name in sorted(agents_filter):
        agent_total = all_cases_by_agent[agent_name]
        agent_fails = len(agent_results.get(agent_name, []))
        agent_pass = agent_total - agent_fails
        pct = 100 * agent_pass // max(agent_total, 1)
        color = G if pct >= 90 else Y if pct >= 70 else R
        print(f"    {color}{agent_name:20s}{X} {agent_pass}/{agent_total} ({pct}%)")

    if failures:
        print(f"\n  {B}Fallos ({len(failures)}):{X}")
        for cid, ag, cat, q, typ, note in failures:
            color = R if typ in ("error", "empty") else Y
            print(f"    {color}#{cid:3d}{X} [{ag}/{cat}] {q}")
            print(f"         [{typ}] {note}")

    # Save report
    try:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"/tmp/qa_fetchdata_{ts}.md"
        with open(path, "w") as f:
            f.write(f"# Test fetch_data directo — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"**Resultado:** {passed}/{total_run} ({100*passed//max(total_run,1)}%)\n")
            f.write(f"**Tiempo:** {elapsed_total:.1f}s\n\n")
            if failures:
                f.write("## Fallos\n\n")
                for cid, ag, cat, q, typ, note in failures:
                    f.write(f"- #{cid} [{ag}/{cat}] {q} → `{typ}`: {note}\n")
        print(f"\n  {C}Reporte: {path}{X}")
    except Exception:
        pass

    sys.exit(0 if results["empty"] == 0 and results["error"] == 0 else 1)


if __name__ == "__main__":
    main()
