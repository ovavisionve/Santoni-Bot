import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.api.routes import auth, chat, users, admin, export
from app.utils.seed import create_admin_user
from app.utils.seed_demo import seed_demo_data
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = setup_logging()


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
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost",
        "https://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
    }


@app.get("/api/health/detailed")
def health_check_detailed():
    """Detailed health check for monitoring."""
    checks = {}

    # PostgreSQL (internal)
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # Groq API key
    checks["groq"] = {
        "status": "ok" if settings.groq_api_key else "not_configured",
        "model": settings.groq_model,
    }

    # Anthropic (optional)
    checks["anthropic"] = {
        "status": "ok" if settings.anthropic_api_key else "not_configured",
    }

    # iDempiere DB
    checks["idempiere"] = {
        "status": "configured" if settings.idempiere_db_password else "not_configured",
        "host": settings.idempiere_db_host,
        "database": settings.idempiere_db_name,
    }

    overall = "ok" if checks["database"]["status"] == "ok" and checks["groq"]["status"] == "ok" else "degraded"

    return {
        "status": overall,
        "app": settings.app_name,
        "version": "1.0.0",
        "env": settings.app_env,
        "checks": checks,
    }
