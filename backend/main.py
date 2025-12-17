from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from config import settings
from core.logging import configure_logging
from core.logging import REQUEST_ID_HEADER
from middleware.request_context import get_request_id

# Import centralized services
from services.database import init_db, run_migrations, close_db
from services.ai_service import AIServiceError

# Import middleware
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_context import RequestContextMiddleware
from middleware.error_handler import ErrorHandlingMiddleware

from auth.routes import router as auth_router
from meta.routes import router as meta_router
from apps import load_apps
from apps.registry import registry

# Load apps at module level so routers are registered before app starts
load_apps()

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

# Determine CORS origins from env; default to frontend dev origin for cookie auth
cors_origins = settings.cors_allowed_origins or ["http://localhost:3000"]

app = FastAPI(
    title="Co-Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    message = str(exc)
    if message.startswith("Input blocked"):
        status_code = 400
    elif message.startswith("Output blocked"):
        status_code = 422
    else:
        status_code = 503
    req_id = get_request_id()
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "request_id": req_id},
        headers={REQUEST_ID_HEADER: req_id},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = get_request_id()
    headers = dict(getattr(exc, "headers", None) or {})
    headers[REQUEST_ID_HEADER] = req_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": req_id},
        headers=headers,
    )

# Add middleware (order matters - first added = last executed)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, requests_per_second=20)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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

# Meta/config endpoints
app.include_router(meta_router, prefix="/api/meta", tags=["meta"])

# Register app routers from registry
for router_info in registry.get_routers():
    router, prefix, tags = router_info
    app.include_router(router, prefix=prefix, tags=tags)
