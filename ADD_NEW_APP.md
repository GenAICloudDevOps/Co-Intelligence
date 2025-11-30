# Adding a New App to Co-Intelligence

Quick guide to add a new app in ~10 minutes.

## Backend Setup (5 min)

### 1. Create App Directory

```bash
mkdir -p backend/apps/my_app
```

### 2. Create `models.py`

```python
from models.base import BaseModel
from tortoise import fields

class MyAppItem(BaseModel):
    user_id = fields.IntField()
    name = fields.CharField(max_length=255)
    
    class Meta:
        table = "my_app_items"
```

### 3. Create `routes.py`

```python
from fastapi import APIRouter, Depends
from auth.utils import get_current_user
from auth.models import User

router = APIRouter()

@router.get("/items")
async def get_items(current_user: User = Depends(get_current_user)):
    return {"items": []}

@router.post("/items")
async def create_item(data: dict, current_user: User = Depends(get_current_user)):
    return {"success": True}
```

### 4. Create `__init__.py`

```python
from apps.registry import registry, AppConfig
from apps.my_app.routes import router

registry.register(AppConfig(
    name="my-app",
    router=router,
    models_module="apps.my_app.models",
    display_name="My App",
    description="My app description",
    icon="🚀",
    color="#ec4899",
    status="active"
))
```

### 5. Import in `backend/main.py`

```python
# Add with other app imports
import apps.my_app
```

✅ Backend done! API at `/api/apps/my-app/*`

---

## Frontend Setup (5 min)

### 1. Add to `frontend/app/config/apps.ts`

```typescript
{
  id: 'my-app',
  name: 'My App',
  description: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4'],
  icon: '🚀',
  color: '#ec4899',
  route: '/apps/my-app',
  status: 'active',
  requiresAuth: true
}
```

### 2. Create `frontend/app/apps/my-app/page.tsx`

```typescript
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import { api } from '@/app/services/api'
import { DEFAULT_MODEL } from '@/app/config/models'
import type { Message } from '@/app/types'

export default function MyApp() {
  const { user, loading } = useAuth(true)
  const [items, setItems] = useState([])
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)

  useEffect(() => {
    if (user) loadItems()
  }, [user])

  const loadItems = async () => {
    const data = await api.get('/api/apps/my-app/items')
    setItems(data.items)
  }

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <AppHeader 
        appName="My App" 
        showModelSelector={true}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />
      
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
        <Card padding="lg">
          <h1>Welcome, {user?.username}!</h1>
        </Card>
      </div>
    </div>
  )
}
```

✅ Frontend done! App visible on homepage.

---

## Available Imports

### Shared Types (`@/app/types`)
```typescript
import type { Message, Session, User, Document } from '@/app/types'
```

### API Service (`@/app/services/api`)
```typescript
import { api } from '@/app/services/api'

// Usage
await api.get<T>('/endpoint')
await api.post<T>('/endpoint', data)
await api.put<T>('/endpoint', data)
await api.delete<T>('/endpoint')
```

### Model Config (`@/app/config/models`)
```typescript
import { AI_MODELS, DEFAULT_MODEL, ModelSelector } from '@/app/config/models'
```

### Components (`@/app/components/*`)
```typescript
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import Button from '@/app/components/Button'
import Modal from '@/app/components/Modal'
```

### Auth Hook (`@/app/hooks/useAuth`)
```typescript
import { useAuth } from '@/app/hooks/useAuth'

const { user, loading, token, logout } = useAuth(true) // true = require auth
```

---

## Adding AI Chat Feature

```typescript
const [messages, setMessages] = useState<Message[]>([])
const [input, setInput] = useState('')

const sendMessage = async () => {
  const userMsg = { role: 'user', content: input }
  setMessages(prev => [...prev, userMsg])
  
  const data = await api.post('/api/apps/my-app/chat', {
    message: input,
    model: selectedModel
  })
  
  setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
  setInput('')
}
```

---

## Checklist

- [ ] Backend `models.py` created
- [ ] Backend `routes.py` created  
- [ ] Backend `__init__.py` with registry
- [ ] Import added to `main.py`
- [ ] Frontend config in `apps.ts`
- [ ] Frontend page created
- [ ] Test locally with `docker-compose up`
