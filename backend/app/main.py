from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.api.routes import auth, chat, users, admin
from app.utils.seed import create_admin_user
from app.utils.seed_demo import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, seed admin, seed demo data
    Base.metadata.create_all(bind=engine)
    create_admin_user()
    seed_demo_data()
    yield
    # Shutdown


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

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
    }
