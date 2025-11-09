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
import apps.agentic_tutor

from apps.registry import registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== LIFESPAN START ===")
    # Build model modules list
    model_modules = [
        'auth.models',
        'models.app_role',
        'apps.ai_chat.models',
        'apps.agentic_barista.models',
        'apps.insurance_claims.models',
        'apps.agentic_lms.models',
        'apps.agentic_tutor.models'
    ]
    
    print(f"Initializing with models: {model_modules}")
    
    # Parse DATABASE_URL
    import re
    db_url = settings.DATABASE_URL
    match = re.match(r'postgres://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)', db_url)
    
    if match:
        user, password, host, port, database = match.groups()
        print(f"Database: {user}@{host}:{port}/{database}")
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
                        'ssl': None
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
        print("Calling Tortoise.init...")
        await Tortoise.init(config=db_config)
        print("✓ Tortoise initialized")
    else:
        print("ERROR: Could not parse DATABASE_URL")
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': model_modules}
        )
    
    print("Generating schemas...")
    await Tortoise.generate_schemas()
    print("✓ Schemas generated")
    
    print("Initializing apps...")
    await registry.initialize_apps()
    print("✓ Apps initialized")
    print("=== LIFESPAN READY ===")
    
    yield
    
    print("=== LIFESPAN SHUTDOWN ===")
    await Tortoise.close_connections()
    print("✓ Connections closed")

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
