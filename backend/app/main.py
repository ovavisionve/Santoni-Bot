import time
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.api.routes import auth, chat, users, admin, export, knowledge, documents, dashboard, catalog
from app.middleware.auth import get_current_user
from app.utils.migrate import run_startup_migrations
from app.utils.seed import create_admin_user
from app.utils.seed_demo import seed_demo_data
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = setup_logging()

# ─── App version (used for Sentry releases and health checks) ──
APP_VERSION = "1.1.0"

# ─── Sentry (optional, only if DSN is configured) ──────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        environment=settings.app_env,
        release=f"santonibot@{APP_VERSION}",
        send_default_pii=False,
        enable_tracing=True,
    )
    logger.info("Sentry initialized (env=%s, release=santonibot@%s)", settings.app_env, APP_VERSION)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # print() garantiza que aparezca en docker logs (no depende de logging config)
    _env_msg = (
        f"═══ APP_ENV={settings.app_env} ═══ "
        f"Queries irán a: {'iDempiere (producción)' if settings.app_env == 'production' else 'DEMO tables (desarrollo)'}"
    )
    print(f"[SantoniBot] {_env_msg}", flush=True)
    logger.info("SantoniBot starting up...")
    logger.info(_env_msg)

    # Warn about historical data configuration
    if settings.historical_data_enabled:
        _hist_msg = (
            f"═══ HISTORICAL_DATA_ENABLED=true, CUTOFF={settings.historical_data_cutoff} ═══ "
            f"Queries con fechas antes del cutoff irán a la DB LOCAL (schema adempiere). "
            f"Si la DB local está vacía, se hará fallback a iDempiere automáticamente."
        )
        print(f"[SantoniBot] {_hist_msg}", flush=True)
        logger.info(_hist_msg)
    else:
        logger.info("Historical data routing DISABLED — all queries go to iDempiere.")

    run_startup_migrations()
    Base.metadata.create_all(bind=engine)
    create_admin_user()
    seed_demo_data()

    # Iniciar sincronización automática del catálogo de datos (cada 5 min)
    from app.services.catalog_sync import start_sync, stop_sync
    start_sync()

    logger.info("SantoniBot ready.")
    yield

    # Detener sincronización del catálogo
    stop_sync()
    logger.info("SantoniBot shutting down.")


app = FastAPI(
    title="SantoniBot API",
    description="Sistema Inteligente de Análisis de Datos Empresariales - Alimentos Santoni",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# CORS - explicit methods and headers
_cors_origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://localhost:80",
    "https://localhost",
]
if settings.app_env == "production":
    _cors_origins = [
        f"https://{settings.domain}",
        f"http://{settings.domain}",
    ]
    # Also allow direct port access in internal network
    if settings.domain not in ("localhost", "127.0.0.1"):
        _cors_origins.append(f"http://{settings.domain}:3000")
        _cors_origins.append(f"http://{settings.domain}:80")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def sentry_user_context(request: Request, call_next):
    """Set Sentry user context from JWT token when available."""
    if settings.sentry_dsn:
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from app.services.auth import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                if payload:
                    sentry_sdk.set_user({
                        "id": str(payload.get("sub", "")),
                        "username": payload.get("username", ""),
                        "ip_address": request.client.host if request.client else None,
                    })
                    sentry_sdk.set_tag("user.department", payload.get("department", "unknown"))
        except Exception:
            pass  # Never break requests for Sentry context
    response = await call_next(request)
    if settings.sentry_dsn:
        sentry_sdk.set_user(None)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_logger = get_logger("http")
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000)

    if not request.url.path.startswith("/api/health"):
        req_logger.info(
            "%s %s → %s (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"status_code": response.status_code, "duration_ms": duration_ms},
        )

    return response


# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
        "app_env": settings.app_env,
    }


@app.get("/api/health/detailed")
def health_check_detailed(current_user=Depends(get_current_user)):
    """Detailed health check - requires authentication."""
    checks = {}

    # PostgreSQL (internal)
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = {"status": "ok"}
    except Exception:
        checks["database"] = {"status": "error"}

    # AI Provider
    checks["ai_provider"] = {
        "active": settings.ai_provider,
        "groq": "ok" if settings.groq_api_key else "not_configured",
        "openrouter": "ok" if settings.openrouter_api_key else "not_configured",
        "anthropic": "ok" if settings.anthropic_api_key else "not_configured",
    }

    # iDempiere
    checks["idempiere"] = {
        "status": "configured" if settings.idempiere_db_password else "not_configured",
    }

    overall = "ok" if checks["database"]["status"] == "ok" else "degraded"

    return {
        "status": overall,
        "app": settings.app_name,
        "version": APP_VERSION,
        "checks": checks,
    }
