#!/bin/bash
# ══════════════════════════════════════════════════════════════
# SantoniBot QA - MASTER SCRIPT
# Ejecuta todas las capas y genera reporte consolidado
# Ejecutar desde: /opt/santonibot/scripts/qa/
# ══════════════════════════════════════════════════════════════

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-/opt/santonibot}"
REPORT_FILE="${PROJECT_DIR}/docs/qa_report_$(date +%Y%m%d_%H%M%S).txt"

export PROJECT_DIR

echo ""
echo -e "${BOLD}${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}║                                                      ║${NC}"
echo -e "${BOLD}${MAGENTA}║       SANTONIBOT — QA COMPLETO DE CIERRE             ║${NC}"
echo -e "${BOLD}${MAGENTA}║       Desarrollado por OVA Vision Agency             ║${NC}"
echo -e "${BOLD}${MAGENTA}║                                                      ║${NC}"
echo -e "${BOLD}${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Fecha:     $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Servidor:  $(hostname) ($(uname -r))"
echo -e "  Proyecto:  $PROJECT_DIR"
echo -e "  Reporte:   $REPORT_FILE"
echo ""

# Crear directorio de reportes si no existe
mkdir -p "$(dirname "$REPORT_FILE")"

# Iniciar reporte
{
    echo "════════════════════════════════════════════════════════"
    echo " SANTONIBOT — REPORTE QA DE CIERRE"
    echo " Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
    echo " Servidor: $(hostname)"
    echo "════════════════════════════════════════════════════════"
    echo ""
} > "$REPORT_FILE"

TOTAL_PASS=0
TOTAL_WARN=0
TOTAL_FAIL=0
START_TIME=$(date +%s)

# ─── Función para ejecutar una capa ───
run_layer() {
    local layer_num="$1"
    local layer_name="$2"
    local script_name="$3"
    local script_path="$SCRIPT_DIR/$script_name"

    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  EJECUTANDO CAPA $layer_num: $layer_name${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    {
        echo ""
        echo "── CAPA $layer_num: $layer_name ──"
        echo ""
    } >> "$REPORT_FILE"

    if [[ ! -f "$script_path" ]]; then
        echo -e "  ${RED}❌ Script no encontrado: $script_path${NC}"
        echo "SCRIPT NO ENCONTRADO: $script_path" >> "$REPORT_FILE"
        ((TOTAL_FAIL++))
        return
    fi

    chmod +x "$script_path"

    # Ejecutar y capturar output
    local output
    output=$("$script_path" 2>&1) || true
    echo "$output"
    echo "$output" >> "$REPORT_FILE"

    # Extraer contadores de la última línea del output
    local last_line
    last_line=$(echo "$output" | tail -1)

    local p w f
    p=$(echo "$last_line" | grep -oP 'PASS=\K[0-9]+' || echo "0")
    w=$(echo "$last_line" | grep -oP 'WARN=\K[0-9]+' || echo "0")
    f=$(echo "$last_line" | grep -oP 'FAIL=\K[0-9]+' || echo "0")

    TOTAL_PASS=$((TOTAL_PASS + p))
    TOTAL_WARN=$((TOTAL_WARN + w))
    TOTAL_FAIL=$((TOTAL_FAIL + f))
}

# ═══════════════════════════════════════════════════════
# EJECUTAR TODAS LAS CAPAS
# ═══════════════════════════════════════════════════════

run_layer "1" "INFRAESTRUCTURA DOCKER" "test_infrastructure.sh"
run_layer "2" "CONECTIVIDAD DE DATOS" "test_connectivity.sh"
run_layer "3" "AGENTES IA" "test_agents.sh"
run_layer "5" "RESILIENCIA" "test_resilience.sh"

# ═══════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

TOTAL_TESTS=$((TOTAL_PASS + TOTAL_WARN + TOTAL_FAIL))

# Determinar estado general
if (( TOTAL_FAIL == 0 && TOTAL_WARN == 0 )); then
    OVERALL_STATUS="${GREEN}🎉 TODOS LOS TESTS PASARON — LISTO PARA CIERRE${NC}"
    OVERALL_TAG="ALL_PASS"
elif (( TOTAL_FAIL == 0 )); then
    OVERALL_STATUS="${YELLOW}⚠️  SIN FALLAS PERO HAY WARNINGS — REVISAR ANTES DE CERRAR${NC}"
    OVERALL_TAG="WARNINGS_ONLY"
elif (( TOTAL_FAIL <= 3 )); then
    OVERALL_STATUS="${RED}❌ HAY FALLAS MENORES — CORREGIR ANTES DE CERRAR${NC}"
    OVERALL_TAG="MINOR_FAILS"
else
    OVERALL_STATUS="${RED}🚨 HAY FALLAS CRÍTICAS — NO CERRAR HASTA RESOLVER${NC}"
    OVERALL_TAG="CRITICAL_FAILS"
fi

echo ""
echo ""
echo -e "${BOLD}${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}║           REPORTE FINAL QA — SANTONIBOT             ║${NC}"
echo -e "${BOLD}${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Total tests:    ${BOLD}$TOTAL_TESTS${NC}"
echo -e "  ${GREEN}✅ PASS:         $TOTAL_PASS${NC}"
echo -e "  ${YELLOW}⚠️  WARN:         $TOTAL_WARN${NC}"
echo -e "  ${RED}❌ FAIL:         $TOTAL_FAIL${NC}"
echo ""
echo -e "  Duración:       ${DURATION_MIN}m ${DURATION_SEC}s"
echo ""
echo -e "  Estado:         $OVERALL_STATUS"
echo ""
echo -e "  Reporte:        $REPORT_FILE"
echo ""

# Agregar resumen al reporte
{
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo " RESUMEN FINAL"
    echo "════════════════════════════════════════════════════════"
    echo " Total: $TOTAL_TESTS tests"
    echo " PASS:  $TOTAL_PASS"
    echo " WARN:  $TOTAL_WARN"
    echo " FAIL:  $TOTAL_FAIL"
    echo " Duración: ${DURATION_MIN}m ${DURATION_SEC}s"
    echo " Estado: $OVERALL_TAG"
    echo "════════════════════════════════════════════════════════"
} >> "$REPORT_FILE"

# ─── Siguiente paso según resultado ───
echo -e "${BOLD}Siguientes pasos:${NC}"
case "$OVERALL_TAG" in
    ALL_PASS)
        echo -e "  1. git tag v1.0-qa-passed"
        echo -e "  2. Backup de DB"
        echo -e "  3. Presentar reporte al cliente"
        ;;
    WARNINGS_ONLY)
        echo -e "  1. Revisar cada WARNING en el reporte"
        echo -e "  2. Decidir si son aceptables o requieren fix"
        echo -e "  3. Re-ejecutar capas afectadas"
        ;;
    MINOR_FAILS|CRITICAL_FAILS)
        echo -e "  1. Revisar cada FAIL en el reporte"
        echo -e "  2. Crear fix para cada falla"
        echo -e "  3. Commit con formato: fix: descripción del fix"
        echo -e "  4. Re-ejecutar: ./run_full_qa.sh"
        ;;
esac
echo ""
