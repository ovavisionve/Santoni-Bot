#!/bin/bash
# ══════════════════════════════════════════════════════════════
# SantoniBot QA - CAPA 5: Resiliencia y Edge Cases
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
API_BASE="${API_BASE:-http://localhost:8000}"
# Credenciales: configurar via env vars o archivo .env.qa
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env.qa" ]]; then
    set -a; source "$SCRIPT_DIR/.env.qa"; set +a
fi
TEST_USER="${TEST_USER:-admin}"
TEST_PASS="${TEST_PASS:-admin123}"

log_result() {
    local status="$1" test_name="$2" detail="$3"
    case "$status" in
        PASS) echo -e "  ${GREEN}✅ PASS${NC} | $test_name | $detail"; PASS=$((PASS + 1)) ;;
        WARN) echo -e "  ${YELLOW}⚠️  WARN${NC} | $test_name | $detail"; WARN=$((WARN + 1)) ;;
        FAIL) echo -e "  ${RED}❌ FAIL${NC} | $test_name | $detail"; FAIL=$((FAIL + 1)) ;;
    esac
}

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  SANTONIBOT QA — CAPA 5: RESILIENCIA${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ─── Obtener token ───
TOKEN=$(curl -sf --max-time 10 \
    -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [[ -z "$TOKEN" ]]; then
    echo -e "  ${RED}❌ No se pudo obtener token. Abortando.${NC}"
    exit 1
fi
echo -e "  Token obtenido ✓"
echo ""

# Helper: enviar mensaje y obtener HTTP code + body
send_msg() {
    local msg="$1"
    curl -sf --max-time 30 -w "\n%{http_code}" \
        -X POST "$API_BASE/api/chat/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"message\":\"$msg\"}" 2>/dev/null || echo -e "\n000"
}

get_code() { echo "$1" | tail -1; }
get_body() { echo "$1" | sed '$d'; }

# ═══════════════════════════════════════════════════════
# TEST 5.1: Mensaje sin sentido
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.1] Mensaje sin sentido${NC}"
resp=$(send_msg "asdfghjkl zxcvbnm qwerty")
code=$(get_code "$resp")
body=$(get_body "$resp")

if [[ "$code" == "200" ]]; then
    if echo "$body" | grep -qiE "traceback|internal server error"; then
        log_result "FAIL" "Msg sin sentido" "HTTP 200 pero contiene error"
    else
        log_result "PASS" "Msg sin sentido" "Respondió sin crash (HTTP $code)"
    fi
else
    log_result "FAIL" "Msg sin sentido" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.2: Inyección SQL
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.2] Inyección SQL${NC}"
resp=$(send_msg "'; DROP TABLE users; --")
code=$(get_code "$resp")
body=$(get_body "$resp")

if [[ "$code" == "200" || "$code" == "400" || "$code" == "422" ]]; then
    if echo "$body" | grep -qiE "drop|truncat|delet"; then
        log_result "FAIL" "SQL Injection" "Posible ejecución de SQL"
    else
        log_result "PASS" "SQL Injection" "Bloqueado (HTTP $code)"
    fi
else
    log_result "WARN" "SQL Injection" "HTTP $code (verificar manualmente)"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.3: Mensaje vacío
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.3] Mensaje vacío${NC}"
resp=$(curl -sf --max-time 15 -w "\n%{http_code}" \
    -X POST "$API_BASE/api/chat/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"message":""}' 2>/dev/null || echo -e "\n000")
code=$(get_code "$resp")

if [[ "$code" == "200" || "$code" == "400" || "$code" == "422" ]]; then
    log_result "PASS" "Msg vacío" "Manejado (HTTP $code)"
else
    log_result "FAIL" "Msg vacío" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.4: Mensaje muy largo
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.4] Mensaje largo (5000+ chars)${NC}"
long_msg=$(python3 -c "print('Necesito un análisis detallado de ' + 'ventas ' * 700)")
resp=$(send_msg "$long_msg")
code=$(get_code "$resp")

if [[ "$code" == "200" || "$code" == "400" || "$code" == "413" || "$code" == "422" ]]; then
    log_result "PASS" "Msg largo" "Manejado sin crash (HTTP $code)"
elif [[ "$code" == "000" ]]; then
    log_result "WARN" "Msg largo" "Timeout (podría ser normal para 5000+ chars)"
else
    log_result "FAIL" "Msg largo" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.5: Mensaje en inglés
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.5] Mensaje en inglés${NC}"
resp=$(send_msg "What are the top 5 clients by revenue in 2025?")
code=$(get_code "$resp")
body=$(get_body "$resp")

if [[ "$code" == "200" ]]; then
    if echo "$body" | grep -qiE "traceback|error"; then
        log_result "WARN" "Msg inglés" "HTTP 200 pero posible error en body"
    else
        log_result "PASS" "Msg inglés" "Respondió (HTTP 200)"
    fi
else
    log_result "WARN" "Msg inglés" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.6: Auth - Sin token
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.6] Request sin token (debe rechazar)${NC}"
resp=$(curl -sf --max-time 10 -w "\n%{http_code}" \
    -X POST "$API_BASE/api/chat/" \
    -H "Content-Type: application/json" \
    -d '{"message":"hola"}' 2>/dev/null || echo -e "\n000")
code=$(get_code "$resp")

if [[ "$code" == "401" || "$code" == "403" ]]; then
    log_result "PASS" "Sin token" "Rechazado correctamente (HTTP $code)"
elif [[ "$code" == "200" ]]; then
    log_result "FAIL" "Sin token" "Aceptó request sin auth (HTTP 200)"
else
    log_result "WARN" "Sin token" "HTTP $code (esperaba 401/403)"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.7: Auth - Token inválido
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.7] Token inválido (debe rechazar)${NC}"
resp=$(curl -sf --max-time 10 -w "\n%{http_code}" \
    -X POST "$API_BASE/api/chat/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer invalid.token.here" \
    -d '{"message":"hola"}' 2>/dev/null || echo -e "\n000")
code=$(get_code "$resp")

if [[ "$code" == "401" || "$code" == "403" ]]; then
    log_result "PASS" "Token inválido" "Rechazado (HTTP $code)"
elif [[ "$code" == "200" ]]; then
    log_result "FAIL" "Token inválido" "Aceptó token falso (HTTP 200)"
else
    log_result "WARN" "Token inválido" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.8: Auth - Login incorrecto
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.8] Login con credenciales incorrectas${NC}"
resp=$(curl -sf --max-time 10 -w "\n%{http_code}" \
    -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"hacker","password":"password123"}' 2>/dev/null || echo -e "\n000")
code=$(get_code "$resp")

if [[ "$code" == "401" || "$code" == "403" || "$code" == "400" ]]; then
    log_result "PASS" "Login incorrecto" "Rechazado (HTTP $code)"
elif [[ "$code" == "200" ]]; then
    log_result "FAIL" "Login incorrecto" "Aceptó credenciales falsas"
else
    log_result "WARN" "Login incorrecto" "HTTP $code"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.9: Rate limiting
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.9] Rate limiting (31 requests rápidos)${NC}"
rate_limited=false
for i in $(seq 1 35); do
    code=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" \
        -X POST "$API_BASE/api/chat/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"message":"test rate limit"}' 2>/dev/null || echo "000")
    
    if [[ "$code" == "429" ]]; then
        rate_limited=true
        log_result "PASS" "Rate limiting" "Activado en request #$i (HTTP 429)"
        break
    fi
done

if [[ "$rate_limited" == "false" ]]; then
    log_result "WARN" "Rate limiting" "35 requests sin 429 (¿rate limit desactivado?)"
fi
echo ""

# ═══════════════════════════════════════════════════════
# TEST 5.10: Concurrencia
# ═══════════════════════════════════════════════════════
echo -e "${BOLD}[5.10] Concurrencia (5 requests simultáneos)${NC}"
PIDS=()
RESULTS_DIR=$(mktemp -d)

for i in $(seq 1 5); do
    (curl -sf --max-time 45 -w "\n%{http_code}" \
        -X POST "$API_BASE/api/chat/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"message\":\"¿Cuántos empleados activos hay? (test concurrencia $i)\"}" \
        > "$RESULTS_DIR/resp_$i.txt" 2>/dev/null) &
    PIDS+=($!)
done

# Esperar todos
all_ok=true
for pid in "${PIDS[@]}"; do
    wait "$pid" || true
done

success_count=0
for i in $(seq 1 5); do
    if [[ -f "$RESULTS_DIR/resp_$i.txt" ]]; then
        code=$(tail -1 "$RESULTS_DIR/resp_$i.txt")
        if [[ "$code" == "200" ]]; then
            ((success_count++))
        fi
    fi
done

rm -rf "$RESULTS_DIR"

if (( success_count == 5 )); then
    log_result "PASS" "Concurrencia" "5/5 requests exitosos"
elif (( success_count >= 3 )); then
    log_result "WARN" "Concurrencia" "$success_count/5 exitosos"
else
    log_result "FAIL" "Concurrencia" "$success_count/5 exitosos"
fi
echo ""

# ─── RESUMEN ───
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESUMEN CAPA 5: RESILIENCIA${NC}"
echo -e "  ${GREEN}✅ PASS: $PASS${NC}  |  ${YELLOW}⚠️  WARN: $WARN${NC}  |  ${RED}❌ FAIL: $FAIL${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "RESIL_PASS=$PASS RESIL_WARN=$WARN RESIL_FAIL=$FAIL"
