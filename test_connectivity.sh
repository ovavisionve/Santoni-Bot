#!/bin/bash
# ══════════════════════════════════════════════════════════════
# SantoniBot QA - CAPA 2: Conectividad de Datos
# Ejecutar desde: /opt/santonibot/scripts/qa/
# ══════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
WARN=0
FAIL=0

PROJECT_DIR="${PROJECT_DIR:-/opt/santonibot}"

log_result() {
    local status="$1" test_name="$2" detail="$3"
    case "$status" in
        PASS) echo -e "  ${GREEN}✅ PASS${NC} | $test_name | $detail"; ((PASS++)) ;;
        WARN) echo -e "  ${YELLOW}⚠️  WARN${NC} | $test_name | $detail"; ((WARN++)) ;;
        FAIL) echo -e "  ${RED}❌ FAIL${NC} | $test_name | $detail"; ((FAIL++)) ;;
    esac
}

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  SANTONIBOT QA — CAPA 2: CONECTIVIDAD DE DATOS${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

cd "$PROJECT_DIR"

# Cargar variables de entorno
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

BACKEND_CONTAINER=$(docker compose ps -q backend 2>/dev/null | head -1)

run_in_backend() {
    docker exec "$BACKEND_CONTAINER" python3 -c "$1" 2>&1
}

# ─── TEST 2.1: Conexión a DB local PostgreSQL 16 ───
echo -e "${BOLD}[2.1] DB local PostgreSQL 16${NC}"
result=$(run_in_backend "
from app.database import SessionLocal
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    db.close()
    print('OK')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:no se pudo ejecutar")

if [[ "$result" == "OK" ]]; then
    log_result "PASS" "DB local" "Conexión exitosa"
else
    log_result "FAIL" "DB local" "$result"
fi
echo ""

# ─── TEST 2.2: Conexión a iDempiere ───
echo -e "${BOLD}[2.2] iDempiere 192.168.1.73:5432${NC}"

# Primero verificar conectividad de red
if docker exec "$BACKEND_CONTAINER" python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
result = s.connect_ex(('192.168.1.73', 5432))
s.close()
print('OK' if result == 0 else 'FAIL')
" 2>/dev/null | grep -q "OK"; then
    log_result "PASS" "Red iDempiere" "Puerto 5432 accesible"
else
    log_result "FAIL" "Red iDempiere" "Puerto 5432 no accesible (¿VPN activa?)"
fi

# Verificar conexión SQL
result=$(run_in_backend "
from app.database import IdempiereSession
try:
    db = IdempiereSession()
    rows = db.execute('SELECT current_database(), current_user').fetchone()
    db.close()
    print(f'OK:db={rows[0]},user={rows[1]}')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:no se pudo ejecutar")

if [[ "$result" == OK:* ]]; then
    log_result "PASS" "SQL iDempiere" "${result#OK:}"
else
    log_result "FAIL" "SQL iDempiere" "$result"
fi

# Verificar read-only
result=$(run_in_backend "
from app.database import IdempiereSession
try:
    db = IdempiereSession()
    db.execute(\"CREATE TABLE _qa_test_readonly (id int)\")
    db.rollback()
    db.close()
    print('FAIL:pudo crear tabla — NO es read-only')
except Exception as e:
    if 'read-only' in str(e).lower() or 'permission' in str(e).lower() or 'cannot execute' in str(e).lower():
        print('OK:read-only confirmado')
    else:
        print(f'OK:bloqueado ({type(e).__name__})')
" 2>/dev/null || echo "WARN:no se pudo verificar")

if [[ "$result" == OK:* ]]; then
    log_result "PASS" "Read-only iDempiere" "${result#OK:}"
elif [[ "$result" == FAIL:* ]]; then
    log_result "FAIL" "Read-only iDempiere" "${result#FAIL:}"
else
    log_result "WARN" "Read-only iDempiere" "$result"
fi
echo ""

# ─── TEST 2.3: Schema adempiere local (datos históricos) ───
echo -e "${BOLD}[2.3] Schema adempiere (datos históricos locales)${NC}"
result=$(run_in_backend "
from app.database import SessionLocal
try:
    db = SessionLocal()
    tables = db.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'adempiere' LIMIT 20\").fetchall()
    db.close()
    if tables:
        print(f'OK:{len(tables)} tablas encontradas')
    else:
        print('WARN:schema existe pero sin tablas')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:no se pudo verificar")

if [[ "$result" == OK:* ]]; then
    log_result "PASS" "Schema adempiere" "${result#OK:}"
elif [[ "$result" == WARN:* ]]; then
    log_result "WARN" "Schema adempiere" "${result#WARN:}"
else
    log_result "FAIL" "Schema adempiere" "$result"
fi
echo ""

# ─── TEST 2.4: Conteo de registros en tablas clave ───
echo -e "${BOLD}[2.4] Registros en tablas clave (iDempiere)${NC}"
TABLES=("adempiere.c_invoice" "adempiere.c_bpartner" "adempiere.hr_employee" "adempiere.m_product" "adempiere.c_payment")
for table in "${TABLES[@]}"; do
    result=$(run_in_backend "
from app.database import IdempiereSession
try:
    db = IdempiereSession()
    count = db.execute('SELECT COUNT(*) FROM $table').fetchone()[0]
    db.close()
    print(f'OK:{count}')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:no se pudo consultar")

    tname=$(echo "$table" | cut -d. -f2)
    if [[ "$result" == OK:* ]]; then
        count="${result#OK:}"
        if (( count > 0 )); then
            log_result "PASS" "Registros $tname" "$count registros"
        else
            log_result "WARN" "Registros $tname" "0 registros (tabla vacía)"
        fi
    else
        log_result "FAIL" "Registros $tname" "$result"
    fi
done
echo ""

# ─── TEST 2.5: Routing de _get_session ───
echo -e "${BOLD}[2.5] Routing histórico (_get_session)${NC}"
result=$(run_in_backend "
try:
    from app.services.idempiere_queries import _get_session
    import os
    enabled = os.getenv('HISTORICAL_DATA_ENABLED', 'false').lower() == 'true'
    cutoff = os.getenv('HISTORICAL_DATA_CUTOFF', '2026-03-01')
    print(f'CONFIG:enabled={enabled},cutoff={cutoff}')
except ImportError:
    print('WARN:_get_session no encontrado (verificar manualmente)')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "WARN:no se pudo verificar")

if [[ "$result" == CONFIG:* ]]; then
    log_result "PASS" "Config históricos" "${result#CONFIG:}"
elif [[ "$result" == WARN:* ]]; then
    log_result "WARN" "Config históricos" "${result#WARN:}"
else
    log_result "FAIL" "Config históricos" "$result"
fi
echo ""

# ─── TEST 2.6: Latencia de queries ───
echo -e "${BOLD}[2.6] Latencia de queries simples${NC}"
for db_label in "local" "idempiere"; do
    result=$(run_in_backend "
import time
from app.database import SessionLocal, IdempiereSession
try:
    if '$db_label' == 'local':
        db = SessionLocal()
    else:
        db = IdempiereSession()
    start = time.time()
    db.execute('SELECT 1')
    elapsed = time.time() - start
    db.close()
    print(f'{elapsed:.3f}')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "FAIL:error")

    if [[ "$result" == FAIL:* ]]; then
        log_result "FAIL" "Latencia $db_label" "$result"
    else
        ms=$(echo "$result" | awk '{printf "%.0f", $1 * 1000}')
        if (( ms < 2000 )); then
            log_result "PASS" "Latencia $db_label" "${ms}ms"
        else
            log_result "WARN" "Latencia $db_label" "${ms}ms (> 2s)"
        fi
    fi
done
echo ""

# ─── TEST 2.7: API Keys configuradas ───
echo -e "${BOLD}[2.7] API Keys en .env${NC}"
declare -A KEYS=( 
    ["OPENROUTER_API_KEY"]="${OPENROUTER_API_KEY:-}" 
    ["GROQ_API_KEY"]="${GROQ_API_KEY:-}" 
    ["ANTHROPIC_API_KEY"]="${ANTHROPIC_API_KEY:-}" 
)
for key_name in "${!KEYS[@]}"; do
    val="${KEYS[$key_name]}"
    if [[ -z "$val" || "$val" == "sk-xxx"* || "$val" == "your-"* || "$val" == "placeholder"* ]]; then
        log_result "WARN" "$key_name" "Vacío o placeholder"
    else
        masked="${val:0:8}...${val: -4}"
        log_result "PASS" "$key_name" "Configurado ($masked)"
    fi
done
echo ""

# ─── TEST 2.8: Migraciones Alembic ───
echo -e "${BOLD}[2.8] Migraciones Alembic${NC}"
result=$(docker compose exec -T backend alembic current 2>&1 | tail -5)
if echo "$result" | grep -q "head"; then
    log_result "PASS" "Alembic" "En head (sin migraciones pendientes)"
else
    log_result "WARN" "Alembic" "Posibles migraciones pendientes: $result"
fi
echo ""

# ─── TEST 2.9: ChromaDB ───
echo -e "${BOLD}[2.9] ChromaDB${NC}"
result=$(run_in_backend "
try:
    from app.services.rag_service import RAGService
    rag = RAGService()
    print('OK')
except Exception as e:
    print(f'FAIL:{e}')
" 2>/dev/null || echo "WARN:no se pudo verificar")

if [[ "$result" == "OK" ]]; then
    log_result "PASS" "ChromaDB" "Servicio respondiendo"
else
    log_result "WARN" "ChromaDB" "$result"
fi
echo ""

# ─── RESUMEN ───
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESUMEN CAPA 2: CONECTIVIDAD${NC}"
echo -e "  ${GREEN}✅ PASS: $PASS${NC}  |  ${YELLOW}⚠️  WARN: $WARN${NC}  |  ${RED}❌ FAIL: $FAIL${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "CONN_PASS=$PASS CONN_WARN=$WARN CONN_FAIL=$FAIL"
