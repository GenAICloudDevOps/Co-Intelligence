from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from tortoise import Tortoise
from config import settings
from auth.routes import router as auth_router
from apps.ai_chat.routes import router as ai_chat_router
from apps.agentic_barista.routes import router as barista_router
from apps.insurance_claims.routes import router as insurance_router
from apps.agentic_lms.routes import router as lms_router
from apps.agentic_lms.database import init_lms_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': [
            'auth.models',
            'apps.ai_chat.models',
            'apps.agentic_barista.models',
            'apps.insurance_claims.models',
            'apps.agentic_lms.models',
            'models.app_role'
        ]}
    )
    await Tortoise.generate_schemas()
    await init_lms_db()
    yield
    await Tortoise.close_connections()

app = FastAPI(title="Co-Intelligence API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(ai_chat_router, prefix="/api/apps/ai-chat", tags=["ai-chat"])
app.include_router(barista_router, prefix="/api/apps/agentic-barista", tags=["agentic-barista"])
app.include_router(insurance_router, prefix="/api/apps/insurance-claims", tags=["insurance-claims"])
app.include_router(lms_router, prefix="/api/apps/agentic-lms", tags=["agentic-lms"])

@app.get("/")
async def root():
    return {"message": "Co-Intelligence API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
