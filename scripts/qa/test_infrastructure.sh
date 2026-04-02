#!/bin/bash
# ══════════════════════════════════════════════════════════════
# SantoniBot QA - CAPA 1: Infraestructura Docker
# Ejecutar desde: /opt/santonibot/scripts/qa/
# ══════════════════════════════════════════════════════════════

set -uo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
WARN=0
FAIL=0
RESULTS=""

PROJECT_DIR="${PROJECT_DIR:-/opt/santonibot}"

log_result() {
    local status="$1" test_name="$2" detail="$3"
    case "$status" in
        PASS) echo -e "  ${GREEN}✅ PASS${NC} | $test_name | $detail"; PASS=$((PASS + 1)) ;;
        WARN) echo -e "  ${YELLOW}⚠️  WARN${NC} | $test_name | $detail"; WARN=$((WARN + 1)) ;;
        FAIL) echo -e "  ${RED}❌ FAIL${NC} | $test_name | $detail"; FAIL=$((FAIL + 1)) ;;
    esac
    RESULTS+="$status | $test_name | $detail\n"
}

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  SANTONIBOT QA — CAPA 1: INFRAESTRUCTURA DOCKER${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Servidor: $(hostname)"
echo ""

cd "$PROJECT_DIR"

# ─── TEST 1.1: Servicios Docker corriendo ───
echo -e "${BOLD}[1.1] Servicios Docker${NC}"
EXPECTED_SERVICES=("backend" "frontend" "postgres" "chromadb" "nginx")
for svc in "${EXPECTED_SERVICES[@]}"; do
    status=$(docker compose ps --format "{{.Service}}:{{.State}}" 2>/dev/null | grep "^${svc}:" | cut -d: -f2 || echo "NOT_FOUND")
    if [[ "$status" == "running" ]]; then
        log_result "PASS" "Servicio $svc" "Estado: running"
    elif [[ "$status" == "NOT_FOUND" ]]; then
        log_result "FAIL" "Servicio $svc" "No encontrado en docker compose"
    else
        log_result "FAIL" "Servicio $svc" "Estado: $status"
    fi
done
echo ""

# ─── TEST 1.2: Consumo de RAM ───
echo -e "${BOLD}[1.2] Consumo de RAM por contenedor${NC}"
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    mem_raw=$(echo "$line" | awk '{print $2}')
    # Extraer valor numérico en MiB
    if [[ "$mem_raw" == *GiB* ]]; then
        mem_mb=$(echo "$mem_raw" | sed 's/GiB//' | awk '{printf "%.0f", $1 * 1024}')
    elif [[ "$mem_raw" == *MiB* ]]; then
        mem_mb=$(echo "$mem_raw" | sed 's/MiB//' | awk '{printf "%.0f", $1}')
    else
        mem_mb=0
    fi

    if [[ "$name" == *backend* ]] && (( mem_mb > 2048 )); then
        log_result "FAIL" "RAM $name" "${mem_raw} (> 2GB límite backend)"
    elif (( mem_mb > 3072 )); then
        log_result "WARN" "RAM $name" "${mem_raw} (alto)"
    else
        log_result "PASS" "RAM $name" "${mem_raw}"
    fi
done < <(docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" 2>/dev/null | sed 's|/.*||' | head -10)
echo ""

# ─── TEST 1.3: CPU del servidor ───
echo -e "${BOLD}[1.3] CPU del servidor${NC}"
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}' | cut -d. -f1 2>/dev/null || echo "0")
if (( cpu_usage > 80 )); then
    log_result "FAIL" "CPU servidor" "${cpu_usage}% (> 80%)"
elif (( cpu_usage > 60 )); then
    log_result "WARN" "CPU servidor" "${cpu_usage}% (moderado)"
else
    log_result "PASS" "CPU servidor" "${cpu_usage}%"
fi
echo ""

# ─── TEST 1.4: Disco libre ───
echo -e "${BOLD}[1.4] Espacio en disco${NC}"
disk_avail=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
if (( disk_avail < 5 )); then
    log_result "FAIL" "Disco libre" "${disk_avail}GB (< 5GB)"
elif (( disk_avail < 10 )); then
    log_result "WARN" "Disco libre" "${disk_avail}GB (bajo)"
else
    log_result "PASS" "Disco libre" "${disk_avail}GB"
fi
echo ""

# ─── TEST 1.5: Errores en logs (últimos 30 min) ───
echo -e "${BOLD}[1.5] Errores en logs (últimos 30 min)${NC}"
for svc in backend frontend; do
    error_count=$(docker compose logs "$svc" --since 30m 2>/dev/null | grep -ciE "ERROR|CRITICAL|Traceback" || echo "0")
    if (( error_count == 0 )); then
        log_result "PASS" "Logs $svc" "0 errores"
    elif (( error_count < 5 )); then
        log_result "WARN" "Logs $svc" "$error_count errores (revisar)"
    else
        log_result "FAIL" "Logs $svc" "$error_count errores"
    fi
done
echo ""

# ─── TEST 1.6: Puertos accesibles ───
echo -e "${BOLD}[1.6] Puertos accesibles${NC}"
declare -A PORTS=( ["Backend:8000"]=8000 ["Frontend:3000"]=3000 ["Nginx:80"]=80 )
for label in "${!PORTS[@]}"; do
    port="${PORTS[$label]}"
    if curl -sf --max-time 5 "http://localhost:${port}" > /dev/null 2>&1 || \
       curl -sf --max-time 5 -o /dev/null -w "%{http_code}" "http://localhost:${port}" 2>/dev/null | grep -qE "^[2-4]"; then
        log_result "PASS" "Puerto $label" "Accesible"
    else
        # Intentar con netcat como fallback
        if nc -z localhost "$port" 2>/dev/null; then
            log_result "PASS" "Puerto $label" "Accesible (nc)"
        else
            log_result "FAIL" "Puerto $label" "No accesible"
        fi
    fi
done

# PostgreSQL por separado (no HTTP)
if nc -z localhost 5432 2>/dev/null; then
    log_result "PASS" "Puerto PostgreSQL:5432" "Accesible"
else
    log_result "FAIL" "Puerto PostgreSQL:5432" "No accesible"
fi
echo ""

# ─── TEST 1.7: Reinicios recientes ───
echo -e "${BOLD}[1.7] Reinicios recientes (últimas 2h)${NC}"
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    status_full=$(echo "$line" | awk '{$1=""; print $0}' | xargs)
    # Buscar contenedores que se reiniciaron recientemente
    restart_count=$(docker inspect --format='{{.RestartCount}}' "$name" 2>/dev/null || echo "0")
    if (( restart_count > 0 )); then
        log_result "WARN" "Reinicios $name" "$restart_count reinicios registrados"
    else
        log_result "PASS" "Reinicios $name" "Sin reinicios"
    fi
done < <(docker compose ps --format "{{.Name}} {{.Status}}" 2>/dev/null)
echo ""

# ─── TEST 1.8: Red Docker interna ───
echo -e "${BOLD}[1.8] Red Docker interna${NC}"
network_name=$(docker compose config --format json 2>/dev/null | python3 -c "
import sys, json
try:
    config = json.load(sys.stdin)
    nets = list(config.get('networks', {}).keys())
    print(nets[0] if nets else 'default')
except:
    print('default')
" 2>/dev/null || echo "default")

backend_container=$(docker compose ps -q backend 2>/dev/null | head -1)
if [[ -n "$backend_container" ]]; then
    # Verificar que backend puede resolver otros servicios
    for target in postgres chromadb; do
        if docker exec "$backend_container" python3 -c "
import socket
try:
    socket.getaddrinfo('$target', None)
    print('OK')
except:
    print('FAIL')
" 2>/dev/null | grep -q "OK"; then
            log_result "PASS" "Red backend→$target" "Resolución DNS OK"
        else
            log_result "FAIL" "Red backend→$target" "No puede resolver"
        fi
    done
else
    log_result "FAIL" "Red Docker" "No se encontró contenedor backend"
fi
echo ""

# ─── RESUMEN ───
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RESUMEN CAPA 1: INFRAESTRUCTURA${NC}"
echo -e "  ${GREEN}✅ PASS: $PASS${NC}  |  ${YELLOW}⚠️  WARN: $WARN${NC}  |  ${RED}❌ FAIL: $FAIL${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""

# Exportar resultado para run_full_qa.sh
echo "INFRA_PASS=$PASS INFRA_WARN=$WARN INFRA_FAIL=$FAIL"
