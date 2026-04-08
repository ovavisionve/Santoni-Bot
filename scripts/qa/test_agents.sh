#!/bin/bash
# ══════════════════════════════════════════════════════════════
# SantoniBot QA - CAPA 3: Agentes IA
# El test más importante — valida el core del sistema
# Ejecutar desde: /opt/santonibot/scripts/qa/
# ══════════════════════════════════════════════════════════════

set -uo pipefail

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
# URL base del backend (ajustar si cambia el puerto o host)
API_BASE="${API_BASE:-http://localhost:8000}"

# ─── Credenciales de test ───
# Configurar via env vars o archivo .env.qa en scripts/qa/
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env.qa" ]]; then
    set -a; source "$SCRIPT_DIR/.env.qa"; set +a
fi
TEST_USER="${TEST_USER:-admin}"
TEST_PASS="${TEST_PASS:-admin123}"

# Archivo de reporte detallado
REPORT_FILE="/tmp/qa_agents_$(date +%Y%m%d_%H%M%S).log"

log_result() {
    local status="$1" test_name="$2" detail="$3"
    case "$status" in
        PASS) echo -e "  ${GREEN}✅ PASS${NC} | $test_name | $detail"; PASS=$((PASS + 1)) ;;
        WARN) echo -e "  ${YELLOW}⚠️  WARN${NC} | $test_name | $detail"; WARN=$((WARN + 1)) ;;
        FAIL) echo -e "  ${RED}❌ FAIL${NC} | $test_name | $detail"; FAIL=$((FAIL + 1)) ;;
    esac
    echo "$status | $test_name | $detail" >> "$REPORT_FILE"
}

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  SANTONIBOT QA — CAPA 3: AGENTES IA${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  API: $API_BASE"
echo -e "  Reporte: $REPORT_FILE"
echo ""

# ─── Obtener token JWT ───
echo -e "${BOLD}[3.0] Autenticación${NC}"
TOKEN=$(curl -sf --max-time 10 \
    -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [[ -z "$TOKEN" ]]; then
    echo -e "  ${RED}❌ No se pudo obtener token JWT. Abortando tests de agentes.${NC}"
    echo -e "  Verifica: usuario=$TEST_USER, endpoint=$API_BASE/api/auth/login"
    echo ""
    echo "AGENT_PASS=0 AGENT_WARN=0 AGENT_FAIL=1"
    exit 1
fi
log_result "PASS" "Auth JWT" "Token obtenido (${TOKEN:0:20}...)"
echo ""

# ─── Función para enviar mensaje al chat y evaluar respuesta ───
send_chat_message() {
    local message="$1"
    local test_label="$2"
    local expect_data="${3:-true}"        # ¿Se esperan datos numéricos?
    local conversation_id="${4:-}"        # Para follow-ups

    local start_time end_time elapsed_ms response body http_code

    # Construir payload
    local payload="{\"message\":\"$message\""
    if [[ -n "$conversation_id" ]]; then
        payload+=",\"conversation_id\":\"$conversation_id\""
    fi
    payload+="}"

    start_time=$(date +%s%N)

    # Enviar request — ajustar endpoint según tu API
    # Intentar primero /api/chat, luego /api/messages
    response=$(curl -sf --max-time 60 -w "\n%{http_code}" \
        -X POST "$API_BASE/api/chat/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "$payload" 2>/dev/null || \
    curl -sf --max-time 60 -w "\n%{http_code}" \
        -X POST "$API_BASE/api/messages" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "$payload" 2>/dev/null || echo -e "\n000")

    end_time=$(date +%s%N)
    elapsed_ms=$(( (end_time - start_time) / 1000000 ))

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    # Guardar respuesta completa en log
    echo "---" >> "$REPORT_FILE"
    echo "TEST: $test_label" >> "$REPORT_FILE"
    echo "MSG: $message" >> "$REPORT_FILE"
    echo "HTTP: $http_code" >> "$REPORT_FILE"
    echo "TIME: ${elapsed_ms}ms" >> "$REPORT_FILE"
    echo "BODY: $body" >> "$REPORT_FILE"

    # Evaluar HTTP
    if [[ "$http_code" != "200" ]]; then
        log_result "FAIL" "$test_label" "HTTP $http_code (${elapsed_ms}ms)"
        echo ""
        return 1
    fi

    # Extraer texto de respuesta (ajustar campo según tu API: .response, .message, .content)
    local text
    text=$(echo "$body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Intentar varios campos comunes
    for field in ['response', 'message', 'content', 'answer', 'text']:
        if field in data and data[field]:
            print(data[field])
            break
    else:
        print(json.dumps(data)[:500])
except:
    print(sys.stdin.read()[:500])
" 2>/dev/null || echo "$body")

    # Extraer conversation_id si existe (para follow-ups)
    local conv_id
    conv_id=$(echo "$body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for field in ['conversation_id', 'conv_id', 'session_id']:
        if field in data:
            print(data[field])
            break
except:
    pass
" 2>/dev/null || echo "")

    # ── Verificaciones ──

    # 1. Latencia
    if (( elapsed_ms > 30000 )); then
        log_result "FAIL" "$test_label [latencia]" "${elapsed_ms}ms (> 30s)"
    elif (( elapsed_ms > 10000 )); then
        log_result "WARN" "$test_label [latencia]" "${elapsed_ms}ms (> 10s)"
    else
        log_result "PASS" "$test_label [latencia]" "${elapsed_ms}ms"
    fi

    # 2. "no tengo acceso" (falso positivo conocido)
    if echo "$text" | grep -qi "no tengo acceso"; then
        log_result "FAIL" "$test_label [no-acceso]" "Contiene 'no tengo acceso'"
    else
        log_result "PASS" "$test_label [no-acceso]" "Limpio"
    fi

    # 3. Errores en respuesta
    if echo "$text" | grep -qiE "traceback|internal server error|error inesperado"; then
        log_result "FAIL" "$test_label [error]" "Contiene error/traceback"
    else
        log_result "PASS" "$test_label [error]" "Sin errores"
    fi

    # 4. Respuesta vacía
    if [[ -z "$text" || "$text" == "null" || ${#text} -lt 10 ]]; then
        log_result "FAIL" "$test_label [vacío]" "Respuesta vacía o muy corta"
    else
        log_result "PASS" "$test_label [contenido]" "${#text} chars"
    fi

    # 5. Datos numéricos (si se esperan)
    if [[ "$expect_data" == "true" ]]; then
        if echo "$text" | grep -qE "[0-9]+[.,][0-9]+|[0-9]{2,}"; then
            log_result "PASS" "$test_label [datos]" "Contiene datos numéricos"
        else
            log_result "WARN" "$test_label [datos]" "Sin datos numéricos visibles"
        fi
    fi

    # Retornar conversation_id para follow-ups
    if [[ -n "$conv_id" ]]; then
        echo "CONV_ID:$conv_id"
    fi
}

# ═══════════════════════════════════════════════════════
# TESTS POR AGENTE
# ═══════════════════════════════════════════════════════

echo -e "${BOLD}[3.1] Agente de VENTAS${NC}"
conv_result=$(send_chat_message \
    "¿Cuáles son los top 10 clientes por facturación en 2025?" \
    "Ventas:top_clientes" \
    "true")
conv_id=$(echo "$conv_result" | grep "CONV_ID:" | cut -d: -f2 || echo "")
echo ""

echo -e "${BOLD}[3.2] Ventas FOLLOW-UP (herencia temporal + moneda)${NC}"
send_chat_message \
    "¿Y en dólares?" \
    "Ventas:followup_usd" \
    "true" \
    "$conv_id"
echo ""

echo -e "${BOLD}[3.3] Agente de FINANZAS${NC}"
send_chat_message \
    "¿Cuáles son los saldos bancarios actuales?" \
    "Finanzas:saldos" \
    "true"
echo ""

echo -e "${BOLD}[3.4] Agente de CONTABILIDAD${NC}"
send_chat_message \
    "Muéstrame el balance general de diciembre 2025" \
    "Contabilidad:balance" \
    "true"
echo ""

echo -e "${BOLD}[3.5] Agente de RRHH${NC}"
send_chat_message \
    "¿Cuántos empleados activos hay?" \
    "RRHH:empleados" \
    "true"
echo ""

echo -e "${BOLD}[3.6] Agente de PRODUCCIÓN${NC}"
send_chat_message \
    "¿Cuáles son las órdenes de producción de enero 2026?" \
    "Produccion:ordenes" \
    "true"
echo ""

echo -e "${BOLD}[3.7] Agente de COMPRAS INSUMOS${NC}"
send_chat_message \
    "¿Cuánto se ha comprado de empaque en 2025?" \
    "ComprasInsumos:empaque" \
    "true"
echo ""

echo -e "${BOLD}[3.8] Compras Insumos + ORGANIZACIÓN${NC}"
send_chat_message \
    "¿Cuánto se ha comprado de empaque en INPROA SANTONI en 2025?" \
    "ComprasInsumos:org_filter" \
    "true"
echo ""

echo -e "${BOLD}[3.9] Agente de COMPRAS PRODUCTORES${NC}"
send_chat_message \
    "¿Cuáles son los productores registrados?" \
    "ComprasProductores:productores" \
    "false"
echo ""

# ═══════════════════════════════════════════════════════
# TESTS DE REGRESIÓN (bugs conocidos)
# ═══════════════════════════════════════════════════════

echo -e "${BOLD}${YELLOW}[3.R] Tests de REGRESIÓN${NC}"

echo -e "${BOLD}[3.R1] docstatus CO/CL (facturas pagadas)${NC}"
send_chat_message \
    "¿Cuáles son las compras pagadas en 2025?" \
    "Regresion:docstatus_CL" \
    "true"
echo ""

echo -e "${BOLD}[3.R2] Fallback período vacío${NC}"
send_chat_message \
    "¿Cuáles fueron las ventas de marzo 2020?" \
    "Regresion:fallback_vacio" \
    "false"
echo ""

# ─── RESUMEN ───
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESUMEN CAPA 3: AGENTES IA${NC}"
echo -e "  ${GREEN}✅ PASS: $PASS${NC}  |  ${YELLOW}⚠️  WARN: $WARN${NC}  |  ${RED}❌ FAIL: $FAIL${NC}"
echo -e "  Reporte detallado: $REPORT_FILE"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "AGENT_PASS=$PASS AGENT_WARN=$WARN AGENT_FAIL=$FAIL"
