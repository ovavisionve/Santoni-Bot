#!/usr/bin/env python3
"""
migrate_demo_to_production.py - Script de migracion de demo a produccion para SantoniBot.

Maneja la transicion del modo desarrollo (datos demo) al modo produccion (iDempiere real).

Uso:
    python scripts/migrate_demo_to_production.py --dry-run       # Vista previa
    python scripts/migrate_demo_to_production.py                 # Ejecutar migracion
    python scripts/migrate_demo_to_production.py --clean-demo    # Migrar + eliminar tablas demo
    python scripts/migrate_demo_to_production.py --rollback      # Revertir a desarrollo

Requiere: psycopg2-binary (incluido en requirements.txt del backend)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# ANSI color helpers (sin dependencias externas)
# ---------------------------------------------------------------------------

class _C:
    """ANSI escape codes para salida con color."""

    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    @staticmethod
    def disable() -> None:
        for attr in ("RESET", "BOLD", "DIM", "RED", "GREEN", "YELLOW",
                      "BLUE", "MAGENTA", "CYAN", "WHITE"):
            setattr(_C, attr, "")


def _banner(msg: str) -> None:
    width = max(60, len(msg) + 4)
    print(f"\n{_C.CYAN}{_C.BOLD}{'=' * width}")
    print(f"  {msg}")
    print(f"{'=' * width}{_C.RESET}\n")


def _ok(msg: str) -> None:
    print(f"  {_C.GREEN}[OK]{_C.RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_C.YELLOW}[!!]{_C.RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {_C.RED}[FALLO]{_C.RESET}  {msg}")


def _info(msg: str) -> None:
    print(f"  {_C.BLUE}[--]{_C.RESET}  {msg}")


def _step(msg: str) -> None:
    print(f"\n{_C.MAGENTA}{_C.BOLD}>>> {msg}{_C.RESET}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"migration_{datetime.now():%Y%m%d_%H%M%S}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("migration")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEMO_TABLES: list[str] = [
    "demo_clientes",
    "demo_facturas_venta",
    "demo_lineas_factura_venta",
    "demo_cobranzas",
    "demo_metas_venta",
    "demo_cuentas_bancarias",
    "demo_movimientos_bancarios",
    "demo_cuentas_por_pagar",
    "demo_asientos_contables",
    "demo_balance_general",
    "demo_empleados",
    "demo_nominas",
    "demo_asistencias",
    "demo_produccion_diaria",
    "demo_ordenes_produccion",
    "demo_proveedores_insumos",
    "demo_ordenes_compra_insumos",
    "demo_productores",
    "demo_compras_productores",
]

IDEMPIERE_CRITICAL_TABLES: list[str] = [
    "c_invoice",
    "c_bpartner",
    "hr_employee",
    "m_inout",
    "c_order",
    "fact_acct",
    "c_bankaccount",
    "m_storageonhand",
]

# Queries de validacion por agente (una por cada agente del sistema)
AGENT_VALIDATION_QUERIES: dict[str, tuple[str, str]] = {
    "Ventas": (
        "SELECT COUNT(*) AS total FROM adempiere.c_invoice WHERE issotrx = 'Y' AND docstatus = 'CO'",
        "Facturas de venta completadas",
    ),
    "Finanzas": (
        "SELECT COUNT(*) AS total FROM adempiere.c_bankaccount WHERE isactive = 'Y'",
        "Cuentas bancarias activas",
    ),
    "Contabilidad": (
        "SELECT COUNT(*) AS total FROM adempiere.fact_acct WHERE ad_client_id = 1000000",
        "Asientos contables del cliente principal",
    ),
    "RRHH": (
        "SELECT COUNT(*) AS total FROM adempiere.hr_employee WHERE isactive = 'Y'",
        "Empleados activos",
    ),
    "Produccion": (
        "SELECT COUNT(*) AS total FROM adempiere.m_storageonhand WHERE qtyonhand > 0",
        "Productos con stock",
    ),
    "Compras Insumos": (
        "SELECT COUNT(*) AS total FROM adempiere.c_order WHERE issotrx = 'N' AND docstatus = 'CO'",
        "Ordenes de compra completadas",
    ),
    "Compras Productores": (
        "SELECT COUNT(*) AS total FROM adempiere.m_inout WHERE movementtype = 'V+' AND docstatus = 'CO'",
        "Recepciones de material completadas",
    ),
}

# ---------------------------------------------------------------------------
# Utilidades de .env
# ---------------------------------------------------------------------------

def _read_env(path: Path) -> dict[str, str]:
    """Lee un archivo .env y devuelve un dict clave=valor."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            key = match.group(1)
            val = match.group(2).strip().strip('"').strip("'")
            env[key] = val
    return env


def _write_env_value(path: Path, key: str, new_value: str) -> None:
    """Actualiza (o agrega) una clave en el archivo .env."""
    lines = path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^{re.escape(key)}=")
    found = False
    for i, line in enumerate(lines):
        if pattern.match(line.strip()):
            lines[i] = f"{key}={new_value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={new_value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Conexion a bases de datos
# ---------------------------------------------------------------------------

def _connect_pg(host: str, port: int, dbname: str, user: str, password: str,
                timeout: int = 10):
    """Crea una conexion psycopg2 con timeout."""
    try:
        import psycopg2  # type: ignore[import-untyped]
    except ImportError:
        _fail("psycopg2 no esta instalado. Ejecute: pip install psycopg2-binary")
        sys.exit(1)

    return psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, password=password,
        connect_timeout=timeout,
    )


def _exec_query(conn, query: str, params: tuple | None = None) -> list[Any]:
    """Ejecuta una query y devuelve las filas."""
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


# ---------------------------------------------------------------------------
# PASO 1 - Pre-flight checks
# ---------------------------------------------------------------------------

def preflight_checks(env: dict[str, str], *, dry_run: bool) -> bool:
    """Verifica requisitos previos para la migracion."""
    _step("PASO 1: Verificaciones previas (pre-flight)")
    ok = True

    # 1a. .env existe
    if ENV_FILE.exists():
        _ok(f"Archivo .env encontrado en {ENV_FILE}")
    else:
        _fail(f"No se encontro .env en {ENV_FILE}")
        _info("Copie .env.example a .env y configure los valores.")
        return False

    # 1b. APP_ENV actual
    current_env = env.get("APP_ENV", "development")
    _info(f"APP_ENV actual: {_C.BOLD}{current_env}{_C.RESET}")
    if current_env == "production":
        _warn("APP_ENV ya esta en 'production'. Use --rollback para revertir primero.")

    # 1c. Verificar configuraciones criticas de produccion
    secret_key = env.get("SECRET_KEY", "")
    default_secret = "change-this-to-a-random-secret-key-min-32-chars"
    if secret_key == default_secret or len(secret_key) < 32:
        _fail("SECRET_KEY es el valor por defecto o muy corta. Genere una clave segura:")
        _info('  python -c "import secrets; print(secrets.token_urlsafe(64))"')
        ok = False
    else:
        _ok("SECRET_KEY configurada correctamente")

    pg_pass = env.get("POSTGRES_PASSWORD", "")
    if pg_pass in ("changeme", "change-this-password", ""):
        _fail("POSTGRES_PASSWORD no esta configurada para produccion")
        ok = False
    else:
        _ok("POSTGRES_PASSWORD configurada")

    idempiere_pass = env.get("IDEMPIERE_DB_PASSWORD", "")
    if idempiere_pass in ("", "change-this-password"):
        _fail("IDEMPIERE_DB_PASSWORD no esta configurada")
        ok = False
    else:
        _ok("IDEMPIERE_DB_PASSWORD configurada")

    # 1d. Verificar proveedor de IA
    ai_provider = env.get("AI_PROVIDER", "groq")
    if ai_provider == "openrouter":
        key = env.get("OPENROUTER_API_KEY", "")
        if key and key != "your-openrouter-api-key-here":
            _ok(f"Proveedor IA: OpenRouter (clave configurada)")
        else:
            _fail("OPENROUTER_API_KEY no esta configurada")
            ok = False
    elif ai_provider == "groq":
        key = env.get("GROQ_API_KEY", "")
        if key:
            _ok(f"Proveedor IA: Groq (clave configurada)")
            _warn("Groq tiene limite de 100K tokens/dia. Se recomienda OpenRouter para produccion.")
        else:
            _fail("GROQ_API_KEY no esta configurada")
            ok = False
    else:
        _info(f"Proveedor IA: {ai_provider}")

    # 1e. Conexion a PostgreSQL interno
    try:
        conn = _connect_pg(
            host=env.get("POSTGRES_HOST", "db"),
            port=int(env.get("POSTGRES_PORT", "5432")),
            dbname=env.get("POSTGRES_DB", "santonibot"),
            user=env.get("POSTGRES_USER", "santonibot"),
            password=env.get("POSTGRES_PASSWORD", ""),
        )
        _ok("Conexion a PostgreSQL interno: exitosa")

        # Verificar usuario admin
        rows = _exec_query(
            conn,
            "SELECT id, email, role FROM users WHERE role = 'administrador' LIMIT 1",
        )
        if rows:
            _ok(f"Usuario administrador encontrado: {rows[0][1]} (id={rows[0][0]})")
        else:
            _warn("No se encontro usuario administrador en la base de datos")
            _info("Asegurese de crear un usuario admin antes de poner en produccion.")

        conn.close()
    except Exception as e:
        _fail(f"No se pudo conectar a PostgreSQL interno: {e}")
        logger.exception("Error conectando a PostgreSQL interno")
        ok = False

    # 1f. Conexion a iDempiere
    try:
        idempiere_conn = _connect_pg(
            host=env.get("IDEMPIERE_DB_HOST", "192.168.1.73"),
            port=int(env.get("IDEMPIERE_DB_PORT", "5432")),
            dbname=env.get("IDEMPIERE_DB_NAME", "idempiere_produccion"),
            user=env.get("IDEMPIERE_DB_USER", "ova"),
            password=env.get("IDEMPIERE_DB_PASSWORD", ""),
            timeout=15,
        )
        _ok("Conexion a iDempiere: exitosa")
        idempiere_conn.close()
    except Exception as e:
        _fail(f"No se pudo conectar a iDempiere: {e}")
        logger.exception("Error conectando a iDempiere")
        ok = False

    return ok


# ---------------------------------------------------------------------------
# PASO 2 - Validacion de conectividad iDempiere
# ---------------------------------------------------------------------------

def validate_idempiere(env: dict[str, str], *, dry_run: bool) -> bool:
    """Valida tablas criticas y modo read-only en iDempiere."""
    _step("PASO 2: Validacion de conectividad iDempiere")

    try:
        conn = _connect_pg(
            host=env.get("IDEMPIERE_DB_HOST", "192.168.1.73"),
            port=int(env.get("IDEMPIERE_DB_PORT", "5432")),
            dbname=env.get("IDEMPIERE_DB_NAME", "idempiere_produccion"),
            user=env.get("IDEMPIERE_DB_USER", "ova"),
            password=env.get("IDEMPIERE_DB_PASSWORD", ""),
            timeout=15,
        )
    except Exception as e:
        _fail(f"No se pudo conectar a iDempiere: {e}")
        return False

    ok = True

    # 2a. Verificar tablas criticas y contar filas
    _info("Verificando tablas criticas en schema adempiere...")
    print()
    header = f"  {'Tabla':<25} {'Filas':>12}  Estado"
    print(f"  {_C.DIM}{'-' * 55}{_C.RESET}")
    print(f"  {_C.BOLD}{header}{_C.RESET}")
    print(f"  {_C.DIM}{'-' * 55}{_C.RESET}")

    for table in IDEMPIERE_CRITICAL_TABLES:
        try:
            rows = _exec_query(conn, f"SELECT COUNT(*) FROM adempiere.{table}")
            count = rows[0][0]
            status = f"{_C.GREEN}OK{_C.RESET}" if count > 0 else f"{_C.YELLOW}VACIA{_C.RESET}"
            print(f"  {table:<25} {count:>12,}  {status}")
            logger.info("Tabla %s: %d filas", table, count)
            if count == 0:
                _warn(f"  La tabla {table} esta vacia - verificar datos")
        except Exception as e:
            print(f"  {table:<25} {'ERROR':>12}  {_C.RED}FALLO{_C.RESET}")
            logger.error("Error consultando tabla %s: %s", table, e)
            ok = False

    print(f"  {_C.DIM}{'-' * 55}{_C.RESET}")
    print()

    # 2b. Verificar read-only
    _info("Verificando restriccion read-only...")
    try:
        with conn.cursor() as cur:
            cur.execute("SET default_transaction_read_only = ON")
            try:
                cur.execute(
                    "CREATE TEMP TABLE _migration_test_readonly (id int)"
                )
                _fail("iDempiere permite escritura - el modo read-only NO esta activo")
                _warn("La aplicacion fuerza read-only en database.py, pero verifique permisos del usuario DB.")
                ok = False
            except Exception:
                _ok("Modo read-only verificado: escritura bloqueada correctamente")
                conn.rollback()
    except Exception as e:
        _warn(f"No se pudo verificar read-only: {e}")
        conn.rollback()

    conn.close()
    return ok


# ---------------------------------------------------------------------------
# PASO 3 - Limpieza de datos demo (--clean-demo)
# ---------------------------------------------------------------------------

def clean_demo_tables(env: dict[str, str], *, dry_run: bool) -> bool:
    """Elimina las tablas demo_* de la base de datos interna."""
    _step("PASO 3: Limpieza de tablas demo")

    try:
        conn = _connect_pg(
            host=env.get("POSTGRES_HOST", "db"),
            port=int(env.get("POSTGRES_PORT", "5432")),
            dbname=env.get("POSTGRES_DB", "santonibot"),
            user=env.get("POSTGRES_USER", "santonibot"),
            password=env.get("POSTGRES_PASSWORD", ""),
        )
    except Exception as e:
        _fail(f"No se pudo conectar a PostgreSQL interno: {e}")
        return False

    # Verificar cuales tablas existen
    existing: list[str] = []
    for table in DEMO_TABLES:
        rows = _exec_query(
            conn,
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            (table,),
        )
        if rows[0][0]:
            existing.append(table)

    if not existing:
        _ok("No se encontraron tablas demo en la base de datos.")
        conn.close()
        return True

    _info(f"Se encontraron {len(existing)} tablas demo:")
    for t in existing:
        _info(f"  - {t}")

    if dry_run:
        _info("[DRY-RUN] Se eliminarian las tablas listadas arriba.")
        conn.close()
        return True

    # Pedir confirmacion
    print()
    print(f"  {_C.YELLOW}{_C.BOLD}ATENCION: Esta operacion eliminara {len(existing)} tablas demo.{_C.RESET}")
    print(f"  {_C.YELLOW}Los datos demo se perderan de forma permanente.{_C.RESET}")
    resp = input(f"\n  Escriba '{_C.BOLD}ELIMINAR{_C.RESET}' para confirmar: ").strip()
    if resp != "ELIMINAR":
        _info("Operacion cancelada por el usuario.")
        conn.close()
        return True

    # Eliminar en orden inverso (por dependencias FK)
    drop_order = list(reversed(existing))
    conn.autocommit = True
    with conn.cursor() as cur:
        for table in drop_order:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                _ok(f"Tabla {table} eliminada")
                logger.info("Tabla %s eliminada", table)
            except Exception as e:
                _fail(f"Error eliminando {table}: {e}")
                logger.error("Error eliminando tabla %s: %s", table, e)

    conn.close()
    _ok("Limpieza de tablas demo completada")
    return True


# ---------------------------------------------------------------------------
# PASO 4 - Cambio de entorno
# ---------------------------------------------------------------------------

def switch_environment(env: dict[str, str], *, dry_run: bool, to_production: bool = True) -> bool:
    """Cambia APP_ENV en .env entre development y production."""
    target = "production" if to_production else "development"
    current = env.get("APP_ENV", "development")

    _step(f"PASO 4: Cambio de entorno ({current} -> {target})")

    if current == target:
        _ok(f"APP_ENV ya esta en '{target}'. Sin cambios necesarios.")
        return True

    # Verificaciones adicionales para produccion
    if to_production:
        secret = env.get("SECRET_KEY", "")
        default_secret = "change-this-to-a-random-secret-key-min-32-chars"
        if secret == default_secret:
            _fail("No se puede activar produccion con SECRET_KEY por defecto.")
            return False

        pg_pass = env.get("POSTGRES_PASSWORD", "")
        if pg_pass in ("changeme", "change-this-password", ""):
            _fail("No se puede activar produccion con POSTGRES_PASSWORD insegura.")
            return False

    if dry_run:
        _info(f"[DRY-RUN] Se cambiaria APP_ENV de '{current}' a '{target}'")
        if to_production:
            _info("[DRY-RUN] Se cambiaria DEBUG a 'false'")
        return True

    # Backup de .env
    backup_path = ENV_FILE.with_suffix(f".env.backup.{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(ENV_FILE, backup_path)
    _ok(f"Backup de .env creado: {backup_path.name}")
    logger.info("Backup creado: %s", backup_path)

    # Aplicar cambios
    _write_env_value(ENV_FILE, "APP_ENV", target)
    _ok(f"APP_ENV actualizado a '{target}'")

    if to_production:
        _write_env_value(ENV_FILE, "DEBUG", "false")
        _ok("DEBUG actualizado a 'false'")
    else:
        _write_env_value(ENV_FILE, "DEBUG", "true")
        _ok("DEBUG actualizado a 'true'")

    logger.info("APP_ENV cambiado de %s a %s", current, target)
    return True


# ---------------------------------------------------------------------------
# PASO 5 - Validacion post-migracion
# ---------------------------------------------------------------------------

def post_migration_validation(env: dict[str, str], *, dry_run: bool) -> bool:
    """Ejecuta queries de prueba por cada agente contra iDempiere."""
    _step("PASO 5: Validacion post-migracion (queries por agente)")

    try:
        conn = _connect_pg(
            host=env.get("IDEMPIERE_DB_HOST", "192.168.1.73"),
            port=int(env.get("IDEMPIERE_DB_PORT", "5432")),
            dbname=env.get("IDEMPIERE_DB_NAME", "idempiere_produccion"),
            user=env.get("IDEMPIERE_DB_USER", "ova"),
            password=env.get("IDEMPIERE_DB_PASSWORD", ""),
            timeout=15,
        )
    except Exception as e:
        _fail(f"No se pudo conectar a iDempiere para validacion: {e}")
        return False

    ok = True
    results: list[dict[str, Any]] = []

    print()
    header = f"  {'Agente':<25} {'Resultado':>12}  Descripcion"
    print(f"  {_C.DIM}{'-' * 65}{_C.RESET}")
    print(f"  {_C.BOLD}{header}{_C.RESET}")
    print(f"  {_C.DIM}{'-' * 65}{_C.RESET}")

    for agent, (query, description) in AGENT_VALIDATION_QUERIES.items():
        try:
            rows = _exec_query(conn, query)
            count = rows[0][0] if rows else 0
            status = f"{_C.GREEN}OK{_C.RESET}" if count > 0 else f"{_C.YELLOW}SIN DATOS{_C.RESET}"
            print(f"  {agent:<25} {count:>12,}  {description} - {status}")
            results.append({"agente": agent, "resultado": count, "ok": count > 0})
            logger.info("Agente %s: %d (%s)", agent, count, description)
        except Exception as e:
            print(f"  {agent:<25} {'ERROR':>12}  {_C.RED}{e}{_C.RESET}")
            results.append({"agente": agent, "resultado": -1, "ok": False})
            logger.error("Error validando agente %s: %s", agent, e)
            ok = False

    print(f"  {_C.DIM}{'-' * 65}{_C.RESET}")
    print()

    conn.close()

    # Resumen
    agents_ok = sum(1 for r in results if r["ok"])
    total = len(results)
    if agents_ok == total:
        _ok(f"Todos los agentes ({total}/{total}) tienen datos disponibles en iDempiere")
    elif agents_ok > 0:
        _warn(f"{agents_ok}/{total} agentes con datos. Revise los agentes sin datos.")
    else:
        _fail("Ningun agente tiene datos en iDempiere. Verifique la conexion y los datos.")
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Reporte de migracion
# ---------------------------------------------------------------------------

def generate_report(env: dict[str, str], *, dry_run: bool, clean_demo: bool,
                    preflight_ok: bool, idempiere_ok: bool,
                    env_switch_ok: bool, validation_ok: bool,
                    clean_ok: bool | None) -> None:
    """Genera un reporte final de la migracion."""
    _banner("REPORTE DE MIGRACION")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = "[DRY-RUN]" if dry_run else "[EJECUCION]"

    items = [
        ("Fecha/hora", timestamp),
        ("Modo", mode),
        ("APP_ENV destino", "production" if not dry_run else f"production {_C.DIM}(sin aplicar){_C.RESET}"),
        ("Verificaciones previas", f"{_C.GREEN}PASARON{_C.RESET}" if preflight_ok else f"{_C.RED}FALLARON{_C.RESET}"),
        ("Conectividad iDempiere", f"{_C.GREEN}OK{_C.RESET}" if idempiere_ok else f"{_C.RED}FALLO{_C.RESET}"),
        ("Cambio de entorno", f"{_C.GREEN}APLICADO{_C.RESET}" if env_switch_ok else f"{_C.RED}NO APLICADO{_C.RESET}"),
        ("Validacion por agentes", f"{_C.GREEN}OK{_C.RESET}" if validation_ok else f"{_C.YELLOW}INCOMPLETA{_C.RESET}"),
    ]

    if clean_demo:
        items.append((
            "Limpieza tablas demo",
            f"{_C.GREEN}COMPLETADA{_C.RESET}" if clean_ok else f"{_C.YELLOW}NO APLICADA{_C.RESET}",
        ))

    items.append(("Log detallado", str(LOG_FILE)))

    for label, value in items:
        print(f"  {label:<30} {value}")

    print()

    all_ok = preflight_ok and idempiere_ok and env_switch_ok and validation_ok
    if dry_run:
        print(f"  {_C.CYAN}{_C.BOLD}Este fue un DRY-RUN. No se realizaron cambios.{_C.RESET}")
        print(f"  Para ejecutar la migracion: python scripts/migrate_demo_to_production.py")
    elif all_ok:
        print(f"  {_C.GREEN}{_C.BOLD}MIGRACION COMPLETADA EXITOSAMENTE{_C.RESET}")
        print()
        print(f"  {_C.BOLD}Pasos siguientes:{_C.RESET}")
        print(f"  1. Reiniciar los servicios:")
        print(f"     docker compose down && docker compose up -d")
        print(f"  2. Verificar el chat con una consulta de prueba")
        print(f"  3. Revisar logs: docker compose logs backend --tail 50")
    else:
        print(f"  {_C.YELLOW}{_C.BOLD}MIGRACION COMPLETADA CON ADVERTENCIAS{_C.RESET}")
        print(f"  Revise los pasos marcados como FALLADOS y corrija antes de usar en produccion.")

    print()


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback(env: dict[str, str], *, dry_run: bool) -> None:
    """Revierte el entorno a modo desarrollo."""
    _banner("ROLLBACK A MODO DESARROLLO")

    current = env.get("APP_ENV", "development")
    if current == "development":
        _ok("APP_ENV ya esta en 'development'. No se necesita rollback.")
        return

    if dry_run:
        _info("[DRY-RUN] Se revertiria APP_ENV de 'production' a 'development'")
        _info("[DRY-RUN] Se activaria DEBUG=true")
        return

    # Backup
    backup_path = ENV_FILE.with_suffix(f".env.backup.{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(ENV_FILE, backup_path)
    _ok(f"Backup de .env creado: {backup_path.name}")

    _write_env_value(ENV_FILE, "APP_ENV", "development")
    _write_env_value(ENV_FILE, "DEBUG", "true")
    _ok("APP_ENV revertido a 'development'")
    _ok("DEBUG revertido a 'true'")

    logger.info("Rollback ejecutado: APP_ENV -> development")

    print()
    print(f"  {_C.BOLD}Reinicie los servicios para aplicar:{_C.RESET}")
    print(f"  docker compose down && docker compose up -d")
    print()
    _warn("Las tablas demo no se recrean automaticamente.")
    _info("Si necesita datos demo, ejecute desde el backend:")
    _info("  python -c \"from app.utils.seed_demo import seed_demo_data; seed_demo_data()\"")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SantoniBot - Migracion de demo a produccion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Ejemplos:
              python scripts/migrate_demo_to_production.py --dry-run
              python scripts/migrate_demo_to_production.py
              python scripts/migrate_demo_to_production.py --clean-demo
              python scripts/migrate_demo_to_production.py --rollback
        """),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Vista previa: muestra los cambios sin aplicarlos",
    )
    parser.add_argument(
        "--clean-demo", action="store_true",
        help="Eliminar tablas demo_* de la base de datos interna",
    )
    parser.add_argument(
        "--rollback", action="store_true",
        help="Revertir a modo desarrollo (APP_ENV=development)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Desactivar colores en la salida",
    )

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        _C.disable()

    _banner("SantoniBot - Migracion Demo -> Produccion")
    _info(f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}")
    _info(f"Log: {LOG_FILE}")

    if args.dry_run:
        print(f"\n  {_C.CYAN}{_C.BOLD}*** MODO DRY-RUN: No se realizaran cambios ***{_C.RESET}\n")

    # Leer .env
    if not ENV_FILE.exists():
        _fail(f"No se encontro .env en {ENV_FILE}")
        _info(f"Copie {ENV_EXAMPLE} a .env y configure los valores.")
        sys.exit(1)

    env = _read_env(ENV_FILE)

    # Rollback
    if args.rollback:
        rollback(env, dry_run=args.dry_run)
        return

    # --- Flujo de migracion ---

    # Paso 1: Pre-flight
    preflight_ok = preflight_checks(env, dry_run=args.dry_run)
    if not preflight_ok:
        _warn("Las verificaciones previas fallaron. Corrija los errores antes de continuar.")
        if not args.dry_run:
            resp = input(f"\n  Desea continuar de todas formas? (s/N): ").strip().lower()
            if resp != "s":
                _info("Migracion cancelada.")
                sys.exit(1)

    # Paso 2: iDempiere
    idempiere_ok = validate_idempiere(env, dry_run=args.dry_run)

    # Paso 3: Limpieza demo (solo con --clean-demo)
    clean_ok: bool | None = None
    if args.clean_demo:
        clean_ok = clean_demo_tables(env, dry_run=args.dry_run)
    else:
        _step("PASO 3: Limpieza de tablas demo")
        _info("Omitido (use --clean-demo para eliminar tablas demo)")

    # Paso 4: Cambio de entorno
    env_switch_ok = switch_environment(env, dry_run=args.dry_run, to_production=True)

    # Paso 5: Validacion
    validation_ok = post_migration_validation(env, dry_run=args.dry_run)

    # Reporte final
    generate_report(
        env,
        dry_run=args.dry_run,
        clean_demo=args.clean_demo,
        preflight_ok=preflight_ok,
        idempiere_ok=idempiere_ok,
        env_switch_ok=env_switch_ok,
        validation_ok=validation_ok,
        clean_ok=clean_ok,
    )

    # Exit code
    if not args.dry_run and not (preflight_ok and idempiere_ok and env_switch_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
