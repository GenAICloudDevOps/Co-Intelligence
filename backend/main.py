from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from tortoise import Tortoise
from config import settings
from auth.routes import router as auth_router

# Import apps to trigger registration
import apps.ai_chat
import apps.agentic_barista
import apps.insurance_claims
import apps.agentic_lms

from apps.registry import registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build model modules list from registry
    model_modules = ['auth.models', 'models.app_role'] + registry.get_model_modules()
    
    # Parse DATABASE_URL
    import re
    db_url = settings.DATABASE_URL
    match = re.match(r'postgres://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)', db_url)
    
    if match:
        user, password, host, port, database = match.groups()
        db_config = {
            'connections': {
                'default': {
                    'engine': 'tortoise.backends.asyncpg',
                    'credentials': {
                        'host': host,
                        'port': int(port),
                        'user': user,
                        'password': password,
                        'database': database,
                        'ssl': None  # Disable SSL
                    }
                }
            },
            'apps': {
                'models': {
                    'models': model_modules,
                    'default_connection': 'default'
                }
            }
        }
        await Tortoise.init(config=db_config)
    else:
        # Fallback to URL-based init
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': model_modules}
        )
    
    await Tortoise.generate_schemas()
    
    # Initialize all apps
    await registry.initialize_apps()
    
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

# Register auth router
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Auto-register all app routers
for router, prefix, tags in registry.get_routers():
    app.include_router(router, prefix=prefix, tags=tags)

@app.get("/")
async def root():
    return {"message": "Co-Intelligence API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
