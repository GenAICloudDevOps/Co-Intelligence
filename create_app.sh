#!/bin/bash

# Quick app scaffolding script
# Usage: ./create_app.sh my-app "My App" "🚀" "#ec4899"

if [ -z "$1" ]; then
    echo "Usage: ./create_app.sh <app-name> <display-name> <icon> <color>"
    echo "Example: ./create_app.sh my-app \"My App\" \"🚀\" \"#ec4899\""
    exit 1
fi

APP_NAME=$1
DISPLAY_NAME=${2:-$APP_NAME}
ICON=${3:-"🤖"}
COLOR=${4:-"#6366f1"}
APP_NAME_UNDERSCORE=$(echo $APP_NAME | tr '-' '_')

echo "🚀 Creating new app: $APP_NAME"

# Create backend structure
echo "📁 Creating backend structure..."
mkdir -p backend/apps/$APP_NAME_UNDERSCORE

# Create models.py
cat > backend/apps/$APP_NAME_UNDERSCORE/models.py << EOF
from models.base import BaseModel
from tortoise import fields

class ${APP_NAME_UNDERSCORE^}Data(BaseModel):
    user_id = fields.IntField()
    name = fields.CharField(max_length=255)
    
    class Meta:
        table = "${APP_NAME_UNDERSCORE}_data"
EOF

# Create routes.py
cat > backend/apps/$APP_NAME_UNDERSCORE/routes.py << EOF
from fastapi import APIRouter, Depends
from auth.utils import get_current_user
from auth.models import User

router = APIRouter()

@router.get("/data")
async def get_data(current_user: User = Depends(get_current_user)):
    return {"message": "Hello from $DISPLAY_NAME"}
EOF

# Create __init__.py
cat > backend/apps/$APP_NAME_UNDERSCORE/__init__.py << EOF
from apps.registry import registry, AppConfig
from apps.$APP_NAME_UNDERSCORE.routes import router

registry.register(AppConfig(
    name="$APP_NAME",
    router=router,
    models_module="apps.$APP_NAME_UNDERSCORE.models",
    display_name="$DISPLAY_NAME",
    description="$DISPLAY_NAME application",
    icon="$ICON",
    color="$COLOR",
    status="active"
))
EOF

# Create frontend structure
echo "📁 Creating frontend structure..."
mkdir -p frontend/app/apps/$APP_NAME

# Create page.tsx
cat > frontend/app/apps/$APP_NAME/page.tsx << EOF
'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'

export default function ${APP_NAME_UNDERSCORE^}() {
  const { user, loading } = useAuth(true)

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <AppHeader appName="$DISPLAY_NAME" />
      
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
        <Card>
          <h1>Welcome to $DISPLAY_NAME</h1>
          <p>Hello {user?.username}!</p>
        </Card>
      </div>
    </div>
  )
}
EOF

echo ""
echo "✅ App structure created!"
echo ""
echo "📝 Next steps:"
echo "1. Add import to backend/main.py:"
echo "   import apps.$APP_NAME_UNDERSCORE"
echo ""
echo "2. Add to frontend/app/config/apps.ts:"
echo "   {"
echo "     id: '$APP_NAME',"
echo "     name: '$DISPLAY_NAME',"
echo "     description: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4'],"
echo "     icon: '$ICON',"
echo "     color: '$COLOR',"
echo "     route: '/apps/$APP_NAME',"
echo "     status: 'active',"
echo "     requiresAuth: true"
echo "   }"
echo ""
echo "3. Test your app:"
echo "   Backend: http://localhost:8000/api/apps/$APP_NAME/data"
echo "   Frontend: http://localhost:3000/apps/$APP_NAME"
echo ""
echo "🎉 Happy coding!"
