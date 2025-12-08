from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from core.logging import configure_logging

# Import centralized services
from services.database import init_db, run_migrations, close_db

# Import middleware
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_context import RequestContextMiddleware
from middleware.error_handler import ErrorHandlingMiddleware

from auth.routes import router as auth_router

# Import apps to trigger registration
import apps.ai_chat
import apps.agentic_barista
import apps.insurance_claims
import apps.agentic_lms
import apps.agentic_tutor
import apps.ml_predictor

from apps.registry import registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== LIFESPAN START ===")
    try:
        # Initialize database using centralized service
        print("Initializing database...")
        await init_db()
        print("✓ Database initialized")
        
        # Run migrations
        print("Running migrations...")
        await run_migrations()
        print("✓ Migrations completed")
        
        # Initialize apps
        print("Initializing apps...")
        await registry.initialize_apps()
        print("✓ Apps initialized")
        print("=== LIFESPAN READY ===")
    except Exception as e:
        print(f"ERROR during lifespan startup: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    yield
    
    print("=== LIFESPAN SHUTDOWN ===")
    try:
        await close_db()
        print("✓ Connections closed")
    except Exception as e:
        print(f"ERROR during shutdown: {e}")

configure_logging()

app = FastAPI(
    title="Co-Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add middleware (order matters - first added = last executed)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, requests_per_second=20)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Health check endpoint
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Register auth router
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Register app routers from registry
for router_info in registry.get_routers():
    router, prefix, tags = router_info
    app.include_router(router, prefix=prefix, tags=tags)
