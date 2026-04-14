#!/usr/bin/env python3
"""
Batch tester para SantoniBot.

Envía un archivo de preguntas al bot via API y captura todas las
respuestas. Después corre analyze_sql_audit.py sobre las queries
nuevas para darte el reporte automático.

Formato del archivo de preguntas:

    # Líneas que empiezan con # son comentarios, se ignoran.
    # Líneas vacías separan preguntas de la misma conversación
    # (pero comparten historial entre sí).
    # Una línea con '---' termina la conversación actual y empieza
    # una nueva (cada conversación se guarda en su propia entidad).

    # === Conversación 1 — cumpleaños RRHH ===
    Cumpleañeros de mayo en INPROA SANTONI
    Ahora dame del mes de agosto
    Quien cumple en la última semana de mayo?

    ---

    # === Conversación 2 — nómina ===
    Dame el resumen de procesos de nómina de INPROA SANTONI del 01/03/2026 al 31/03/2026

    ---

    # === Conversación 3 — cliente busca datos ===
    Cuántos trabajadores activos tiene INPROA SANTONI

Uso:

    # Básico (usa credenciales por defecto admin)
    docker compose exec backend python scripts/qa/batch_test.py \\
        scripts/qa/preguntas_esalas.txt

    # Con delay entre preguntas (útil para no saturar el LLM)
    docker compose exec backend python scripts/qa/batch_test.py \\
        scripts/qa/preguntas_esalas.txt --delay 2

    # Guardar respuestas del bot en archivo
    docker compose exec backend python scripts/qa/batch_test.py \\
        scripts/qa/preguntas_esalas.txt --output /tmp/respuestas.md

    # NO ejecutar analyze al final (skip reporte)
    docker compose exec backend python scripts/qa/batch_test.py \\
        scripts/qa/preguntas_esalas.txt --no-analyze
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

# Configuración del bot
BOT_URL = os.environ.get("BOT_URL", "http://localhost:8000")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "admin")
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "SantoniAdmin2026!")


def login(client: httpx.Client) -> str:
    """Login y retorna el access token JWT."""
    resp = client.post(
        f"{BOT_URL}/api/auth/login",
        json={"username": BOT_USERNAME, "password": BOT_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def stream_query(
    client: httpx.Client,
    token: str,
    message: str,
    conversation_id: int | None = None,
    timeout: int = 120,
) -> tuple[int, str, dict]:
    """Envía una query al bot via /api/chat/stream (SSE).

    Returns: (conversation_id, full_response_text, metadata).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    response_chunks: list[str] = []
    conv_id = conversation_id or 0
    metadata: dict = {}

    with client.stream(
        "POST",
        f"{BOT_URL}/api/chat/stream",
        json=payload,
        headers=headers,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]  # skip "data: "
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if event_type == "meta":
                conv_id = event.get("conversation_id") or conv_id
                metadata["agent"] = event.get("agent")
                metadata["routing_score"] = event.get("routing_score")
                metadata["timestamp"] = event.get("timestamp")
            elif event_type == "token":
                response_chunks.append(event.get("content", ""))
            elif event_type == "done":
                metadata["agent_used"] = event.get("agent_used", metadata.get("agent"))
                metadata["confidence_score"] = event.get("confidence_score")

    return conv_id, "".join(response_chunks), metadata


def parse_questions_file(path: Path) -> list[list[str]]:
    """Parsea el archivo de preguntas.

    Retorna lista de conversaciones, cada conversación es lista de preguntas.
    Separador de conversaciones: línea '---'
    Líneas que empiezan con '#' son comentarios.
    """
    conversations: list[list[str]] = [[]]
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "---":
                if conversations[-1]:
                    conversations.append([])
                continue
            conversations[-1].append(line)
    # Remover conversaciones vacías
    return [c for c in conversations if c]


def get_current_max_audit_id() -> int | None:
    """Obtiene el ID máximo actual de sql_audit antes del batch."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from sqlalchemy import text
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            r = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM sql_audit")).scalar()
            return int(r) if r is not None else 0
        finally:
            db.close()
    except Exception as exc:
        print(f"[WARN] No pude leer MAX(id) del audit: {exc}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", type=Path, help="Archivo .txt con preguntas")
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Delay en segundos entre queries (default 1)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Guardar respuestas del bot en archivo markdown",
    )
    parser.add_argument(
        "--no-analyze", action="store_true",
        help="NO ejecutar analyze_sql_audit al terminar",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Timeout por query en segundos (default 120)",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"❌ Archivo no encontrado: {args.file}", file=sys.stderr)
        sys.exit(1)

    conversations = parse_questions_file(args.file)
    total_questions = sum(len(c) for c in conversations)
    print(f"📝 Archivo: {args.file}")
    print(f"   {len(conversations)} conversaciones, {total_questions} preguntas totales")
    print()

    # Capturar ID inicial del audit log para después filtrar
    since_id = get_current_max_audit_id()
    since_id_next = (since_id or 0) + 1
    print(f"📊 Audit ID inicial: {since_id} (nuevas queries tendrán id >= {since_id_next})")
    print()

    # Login
    client = httpx.Client()
    print(f"🔐 Login como {BOT_USERNAME}...")
    try:
        token = login(client)
    except Exception as exc:
        print(f"❌ Login falló: {exc}", file=sys.stderr)
        sys.exit(2)
    print("   ✅ Login OK")
    print()

    # Preparar output file
    out_fp = args.output.open("w", encoding="utf-8") if args.output else None
    if out_fp:
        out_fp.write(f"# Respuestas de batch test — {args.file}\n\n")
        out_fp.write(f"Total conversaciones: {len(conversations)}\n")
        out_fp.write(f"Total preguntas: {total_questions}\n\n")
        out_fp.write("---\n\n")

    # Loop por conversaciones
    stats = {"ok": 0, "error": 0, "total_time": 0.0}
    q_num = 0
    for conv_idx, questions in enumerate(conversations, 1):
        print(f"─── Conversación {conv_idx}/{len(conversations)} ({len(questions)} preguntas) ───")
        if out_fp:
            out_fp.write(f"\n## Conversación {conv_idx}\n\n")

        conv_id: int | None = None
        for q in questions:
            q_num += 1
            short = q[:80] + "..." if len(q) > 80 else q
            print(f"  [{q_num:>3}/{total_questions}] {short}", flush=True)
            t0 = time.time()
            try:
                conv_id, response, meta = stream_query(
                    client, token, q, conversation_id=conv_id, timeout=args.timeout,
                )
                elapsed = time.time() - t0
                stats["ok"] += 1
                stats["total_time"] += elapsed
                agent = meta.get("agent_used") or meta.get("agent", "?")
                # Resumen corto de la respuesta (primera línea no vacía)
                preview = next(
                    (ln.strip() for ln in response.split("\n") if ln.strip()),
                    "(vacía)",
                )
                preview_short = preview[:100] + "..." if len(preview) > 100 else preview
                print(f"        ✅ {elapsed:.1f}s — agent={agent} — {preview_short}")
                if out_fp:
                    out_fp.write(f"### Q{q_num}: {q}\n\n")
                    out_fp.write(f"*Agent: `{agent}` · Tiempo: {elapsed:.1f}s*\n\n")
                    out_fp.write(f"{response}\n\n")
                    out_fp.write("---\n\n")
            except httpx.HTTPStatusError as exc:
                stats["error"] += 1
                print(f"        ❌ HTTP {exc.response.status_code}: {exc.response.text[:150]}")
                if out_fp:
                    out_fp.write(f"### Q{q_num}: {q}\n\n❌ HTTP {exc.response.status_code}\n\n---\n\n")
            except Exception as exc:
                stats["error"] += 1
                print(f"        ❌ {type(exc).__name__}: {exc}")
                if out_fp:
                    out_fp.write(f"### Q{q_num}: {q}\n\n❌ {type(exc).__name__}: {exc}\n\n---\n\n")

            if args.delay and q_num < total_questions:
                time.sleep(args.delay)
        print()

    # Resumen
    avg = stats["total_time"] / stats["ok"] if stats["ok"] else 0
    print("=" * 70)
    print(f"📊 Resumen: {stats['ok']}/{total_questions} OK, {stats['error']} errores")
    print(f"   Tiempo total: {stats['total_time']:.1f}s, promedio: {avg:.1f}s/query")
    print()

    if out_fp:
        out_fp.close()
        print(f"💾 Respuestas guardadas en: {args.output}")
        print()

    # Cerrar cliente
    client.close()

    # Análisis automático con analyze_sql_audit
    if not args.no_analyze and since_id is not None:
        print("🔍 Ejecutando análisis de audit log sobre queries nuevas...")
        print()
        script_path = Path(__file__).resolve().parent / "analyze_sql_audit.py"
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path), "--since-id", str(since_id_next)],
            capture_output=False,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
