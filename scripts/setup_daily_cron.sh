#!/bin/bash
# Configura el cron job para sincronización diaria a las 00:00
# Ejecutar una sola vez: bash scripts/setup_daily_cron.sh

SANTONI_DIR="/opt/santonibot"
LOG_DIR="${SANTONI_DIR}/logs"
CRON_CMD="0 0 * * * cd ${SANTONI_DIR} && /usr/bin/docker compose run --rm daily-sync >> ${LOG_DIR}/daily_sync.log 2>&1"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

# Verificar si ya existe
if crontab -l 2>/dev/null | grep -q "daily-sync"; then
    echo "El cron de daily-sync ya existe:"
    crontab -l | grep daily-sync
    echo ""
    echo "Para reemplazarlo, primero elimínalo con: crontab -e"
    exit 0
fi

# Agregar al crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron instalado:"
echo "  $CRON_CMD"
echo ""
echo "Logs en: ${LOG_DIR}/daily_sync.log"
echo "Verificar: crontab -l"
echo ""
echo "Para probar manualmente:"
echo "  cd ${SANTONI_DIR} && docker compose run --rm daily-sync"
