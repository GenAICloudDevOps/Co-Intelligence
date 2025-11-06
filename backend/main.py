from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from tortoise import Tortoise
from config import settings
from auth.routes import router as auth_router
from apps.ai_chat.routes import router as ai_chat_router
from apps.agentic_barista.routes import router as barista_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Remove SSL parameters from URL if present
    db_url = settings.DATABASE_URL.split('?')[0]
    
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['auth.models', 'apps.ai_chat.models', 'apps.agentic_barista.models']}
    )
    await Tortoise.generate_schemas()
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

@app.get("/")
async def root():
    return {"message": "Co-Intelligence API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
