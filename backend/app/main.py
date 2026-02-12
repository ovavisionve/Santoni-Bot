import time
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.api.routes import auth, chat, users, admin, export, knowledge, documents, branding
from app.middleware.auth import get_current_user
from app.utils.seed import create_admin_user
from app.utils.seed_demo import seed_demo_data
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = setup_logging()

# ─── Sentry (optional, only if DSN is configured) ──────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        release=f"santonibot@1.0.0",
        send_default_pii=False,
    )
    logger.info("Sentry initialized (env=%s)", settings.app_env)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SantoniBot starting up...")
    Base.metadata.create_all(bind=engine)
    create_admin_user()
    seed_demo_data()
    logger.info("SantoniBot ready.")
    yield
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
    "https://localhost",
]
if settings.app_env == "production" and hasattr(settings, "domain"):
    _cors_origins = [
        f"https://{settings.domain}",
        f"http://{settings.domain}",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


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
app.include_router(branding.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
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
        "version": "1.0.0",
        "checks": checks,
    }
