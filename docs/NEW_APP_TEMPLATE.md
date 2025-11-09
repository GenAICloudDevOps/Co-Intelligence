# Adding a New App - Quick Guide

## Backend (5 minutes)

### 1. Create app directory structure
```bash
mkdir -p backend/apps/my-app
cd backend/apps/my-app
```

### 2. Create `models.py`
```python
from models.base import BaseModel
from tortoise import fields

class MyAppData(BaseModel):
    user_id = fields.IntField()
    name = fields.CharField(max_length=255)
    
    class Meta:
        table = "my_app_data"
```

### 3. Create `routes.py`
```python
from fastapi import APIRouter, Depends
from auth.utils import get_current_user
from auth.models import User

router = APIRouter()

@router.get("/data")
async def get_data(current_user: User = Depends(get_current_user)):
    return {"message": "Hello from my app"}
```

### 4. Create `__init__.py` (Register the app)
```python
from apps.registry import registry, AppConfig
from apps.my_app.routes import router

registry.register(AppConfig(
    name="my-app",
    router=router,
    models_module="apps.my_app.models",
    display_name="My App",
    description="Description of my app",
    icon="🚀",
    color="#ec4899",
    status="active"
))
```

### 5. Import in `main.py`
```python
# Add this line with other app imports
import apps.my_app
```

**Done!** Backend is ready. API available at `/api/apps/my-app/*`

---

## Frontend (5 minutes)

### 1. Add to `frontend/app/config/apps.ts`
```typescript
{
  id: 'my-app',
  name: 'My App',
  description: [
    'Feature 1',
    'Feature 2',
    'Feature 3',
    'Feature 4'
  ],
  icon: '🚀',
  color: '#ec4899',
  route: '/apps/my-app',
  status: 'active',
  requiresAuth: true
}
```

### 2. Create page `frontend/app/apps/my-app/page.tsx`
```typescript
'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'

export default function MyApp() {
  const { user, loading } = useAuth(true)

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <AppHeader appName="My App" />
      
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
        <Card>
          <h1>Welcome to My App</h1>
          <p>Hello {user?.username}!</p>
        </Card>
      </div>
    </div>
  )
}
```

**Done!** App appears on homepage and is fully functional.

---

## Optional: Add Initialization Function

If your app needs database seeding:

```python
# In apps/my_app/__init__.py
async def init_my_app():
    # Seed data here
    pass

registry.register(AppConfig(
    name="my-app",
    router=router,
    models_module="apps.my_app.models",
    init_function=init_my_app,  # Add this
    # ... rest of config
))
```

---

## Total Time: ~10 minutes

Your new app is now:
- ✅ Auto-registered in backend
- ✅ Visible on homepage
- ✅ Has its own route
- ✅ Uses shared components
- ✅ Follows platform patterns
