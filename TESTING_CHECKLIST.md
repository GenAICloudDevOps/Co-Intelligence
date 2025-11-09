# Testing Checklist - Refactored Co-Intelligence

## Pre-Testing Setup

```bash
# Ensure you're in the project root
cd /Users/gayathri/Documents/Python/venkat/Co-Intelligence

# Check all new files exist
ls -la backend/apps/registry.py
ls -la backend/init_all.py
ls -la frontend/app/config/apps.ts
ls -la frontend/app/hooks/useAuth.ts
ls -la frontend/app/components/
ls -la create_app.sh
```

---

## Backend Testing

### 1. Test App Registry
```bash
cd backend
python -c "
import apps.ai_chat
import apps.agentic_barista
import apps.insurance_claims
import apps.agentic_lms
from apps.registry import registry

print('Registered apps:', len(registry.get_all()))
for app in registry.get_all():
    print(f'  - {app.name}: {app.display_name}')
"
```

**Expected:** Should show 4 registered apps

### 2. Test Database Initialization
```bash
cd backend
python init_all.py
```

**Expected:** 
- ✓ Database connected
- ✓ Schemas created
- ✓ All apps initialized
- ✓ Barista menu seeded
- ✓ Insurance users seeded

### 3. Test Backend Server
```bash
cd backend
python -m uvicorn main:app --reload
```

**Test in browser:**
- http://localhost:8000/docs
- Check all routes are registered:
  - `/api/apps/ai-chat/*`
  - `/api/apps/agentic-barista/*`
  - `/api/apps/insurance-claims/*`
  - `/api/apps/agentic-lms/*`

**Expected:** All routes visible in Swagger UI

---

## Frontend Testing

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Test Frontend Build
```bash
npm run build
```

**Expected:** Build succeeds with no errors

### 3. Test Frontend Dev Server
```bash
npm run dev
```

**Test in browser:** http://localhost:3000

### 4. Homepage Tests
- [ ] Homepage loads without errors
- [ ] 4 app cards displayed (AI Chat, Barista, Insurance, LMS)
- [ ] App count shows "4" in metrics
- [ ] Login/Register buttons work
- [ ] Auth modal opens and closes
- [ ] Can register new user
- [ ] Can login with user
- [ ] User menu shows username and email
- [ ] Logout works

### 5. App Launch Tests
- [ ] AI Chat launches (no auth required)
- [ ] Agentic Barista launches (no auth required)
- [ ] Insurance Claims requires auth
- [ ] Agentic LMS requires auth
- [ ] All apps load without errors

### 6. Component Tests
- [ ] AppHeader displays correctly on app pages
- [ ] Cards render properly
- [ ] Modal opens/closes smoothly
- [ ] Buttons respond to clicks

---

## Integration Testing

### 1. Full User Flow
1. Open homepage
2. Register new account
3. Login
4. Launch each app
5. Verify app functionality
6. Logout
7. Try to access protected app (should redirect)

### 2. API Integration
```bash
# Test AI Chat
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"test","password":"test123"}'

# Get token from response, then test app endpoint
curl http://localhost:8000/api/apps/ai-chat/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## New App Creation Test

### Test the scaffolding script:
```bash
./create_app.sh test-app "Test App" "🧪" "#ff6b6b"
```

**Expected:**
- Creates `backend/apps/test_app/` with models, routes, __init__
- Creates `frontend/app/apps/test-app/page.tsx`
- Shows next steps

### Manual steps:
1. Add `import apps.test_app` to `backend/main.py`
2. Add config to `frontend/app/config/apps.ts`
3. Restart servers
4. Check app appears on homepage
5. Launch app and verify it works

---

## Deployment Testing

### 1. Docker Build Test
```bash
# Test backend Docker build
cd backend
docker build -t test-backend .

# Test frontend Docker build
cd ../frontend
docker build -t test-frontend .
```

**Expected:** Both builds succeed

### 2. Deploy to EKS (if ready)
```bash
./deploy.sh
```

**Expected:** 
- Deployment succeeds
- All pods running
- Services accessible via LoadBalancer

---

## Regression Testing

Verify all existing functionality still works:

### AI Chat
- [ ] Create session
- [ ] Send messages
- [ ] Upload documents
- [ ] Web search
- [ ] Code execution
- [ ] Model switching

### Agentic Barista
- [ ] View menu
- [ ] Add items to cart
- [ ] Place order
- [ ] View order history

### Insurance Claims
- [ ] Buy policy
- [ ] Submit claim
- [ ] View claims
- [ ] Role-based access

### Agentic LMS
- [ ] Browse courses
- [ ] Enroll in course
- [ ] Track progress
- [ ] AI chat

---

## Performance Testing

- [ ] Homepage loads in < 2 seconds
- [ ] App pages load in < 1 second
- [ ] API responses < 500ms
- [ ] No console errors
- [ ] No memory leaks

---

## Checklist Summary

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] All integration tests pass
- [ ] New app creation works
- [ ] Docker builds succeed
- [ ] All existing features work
- [ ] No regressions found
- [ ] Performance acceptable

---

## If Issues Found

1. Check console for errors
2. Check backend logs: `docker-compose logs backend`
3. Check frontend logs: `npm run dev` output
4. Verify all imports are correct
5. Ensure all files were created
6. Check file permissions

---

## Success Criteria

✅ All 4 apps visible on homepage  
✅ All apps launch and work  
✅ Auth flow works  
✅ New app can be created in < 10 minutes  
✅ No breaking changes to existing functionality  
✅ Code is cleaner and more maintainable  

---

## Report Issues

If you find any issues, note:
1. What you were doing
2. Expected behavior
3. Actual behavior
4. Error messages
5. Browser/environment details
