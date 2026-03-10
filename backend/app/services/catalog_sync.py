"""
Catalog Sync - Job de sincronización automática del catálogo de datos.

Ejecuta la sincronización del catálogo de iDempiere cada 5 minutos
usando asyncio nativo (sin dependencias externas).

Se inicia automáticamente con el lifespan de FastAPI en main.py.
"""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("santonibot.catalog_sync")

# Intervalo de sincronización en segundos (5 minutos)
SYNC_INTERVAL_SECONDS = 5 * 60

# Tarea asyncio global
_sync_task: asyncio.Task | None = None


async def _run_sync() -> dict:
    """Ejecuta la sincronización en un thread executor (es I/O bloqueante)."""
    from app.services.data_catalog import get_catalog_service

    catalog = get_catalog_service()

    # Ejecutar sync en thread separado para no bloquear el event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, catalog.sync)
    return result


async def _sync_loop():
    """Loop infinito que ejecuta la sincronización cada SYNC_INTERVAL_SECONDS."""
    logger.info(
        "Catalog sync iniciado. Intervalo: %d segundos (%d minutos)",
        SYNC_INTERVAL_SECONDS,
        SYNC_INTERVAL_SECONDS // 60,
    )

    # Primera sincronización inmediata al iniciar
    try:
        logger.info("Ejecutando sincronización inicial del catálogo...")
        result = await _run_sync()
        if result.get("ok"):
            logger.info(
                "Sincronización inicial completada: %d tablas, %d documentos en %.1fs",
                result.get("tables_discovered", 0),
                result.get("documents_indexed", 0),
                result.get("duration_seconds", 0),
            )
        else:
            logger.warning(
                "Sincronización inicial con errores: %s",
                result.get("error", "desconocido"),
            )
    except Exception as e:
        logger.error("Error en sincronización inicial: %s", e, exc_info=True)

    # Loop de sincronización periódica
    while True:
        try:
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)

            logger.info("Ejecutando sincronización periódica del catálogo...")
            result = await _run_sync()

            if result.get("ok"):
                logger.info(
                    "Sincronización periódica completada: %d tablas en %.1fs",
                    result.get("tables_discovered", 0),
                    result.get("duration_seconds", 0),
                )
            else:
                logger.warning(
                    "Sincronización periódica con errores: %s",
                    result.get("error", "desconocido"),
                )

        except asyncio.CancelledError:
            logger.info("Catalog sync detenido.")
            break
        except Exception as e:
            logger.error(
                "Error en sincronización periódica: %s. Reintentando en %d segundos.",
                e, SYNC_INTERVAL_SECONDS,
            )


def start_sync():
    """Inicia el job de sincronización como tarea asyncio en background."""
    global _sync_task

    if _sync_task is not None and not _sync_task.done():
        logger.warning("Catalog sync ya está en ejecución.")
        return

    _sync_task = asyncio.create_task(_sync_loop())
    logger.info("Catalog sync task creada.")


def stop_sync():
    """Detiene el job de sincronización."""
    global _sync_task

    if _sync_task is not None and not _sync_task.done():
        _sync_task.cancel()
        logger.info("Catalog sync task cancelada.")

    _sync_task = None


async def trigger_manual_sync() -> dict:
    """Dispara una sincronización manual fuera del ciclo periódico."""
    logger.info("Sincronización manual solicitada...")
    try:
        result = await _run_sync()
        return result
    except Exception as e:
        logger.error("Error en sincronización manual: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}
