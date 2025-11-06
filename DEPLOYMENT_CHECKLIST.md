# Agentic Barista Deployment Checklist

## ✅ Pre-Deployment Checklist

### Local Development Setup
- [ ] Seed menu data: `python -m apps.agentic_barista.seed_menu`
- [ ] Start backend: `uvicorn main:app --reload`
- [ ] Start frontend: `npm run dev`
- [ ] Test chat interface at http://localhost:3000
- [ ] Verify menu display works
- [ ] Test adding items to cart
- [ ] Test cart display
- [ ] Test order confirmation
- [ ] Check database for saved orders

### Backend Verification
- [ ] All imports working (no ModuleNotFoundError)
- [ ] Database tables created (barista_menu_items, barista_orders)
- [ ] API endpoints responding:
  - [ ] POST /api/apps/agentic-barista/chat
  - [ ] GET /api/apps/agentic-barista/menu
  - [ ] GET /api/apps/agentic-barista/orders/{session_id}
- [ ] LangGraph workflow executing without errors
- [ ] All 3 agents responding correctly
- [ ] Cart state persisting across messages
- [ ] Orders saving to database

### Frontend Verification
- [ ] Page loads at /apps/agentic-barista
- [ ] Chat interface renders correctly
- [ ] Model selector dropdown works
- [ ] Cart badge updates in real-time
- [ ] Total amount displays correctly
- [ ] Messages display with agent labels
- [ ] Loading animation shows during requests
- [ ] Error handling works

### Integration Testing
- [ ] Homepage shows Agentic Barista card
- [ ] Card links to correct route
- [ ] API URL configured correctly
- [ ] Database connection working
- [ ] No CORS errors
- [ ] Authentication (if enabled) working

## 🐳 Docker Deployment

### Build Images
- [ ] Backend Dockerfile includes agentic_barista app
- [ ] Frontend build includes new route
- [ ] Build backend image: `docker build -t co-intelligence-backend .`
- [ ] Build frontend image: `docker build -t co-intelligence-frontend .`
- [ ] Test images locally with docker-compose

### Docker Compose
- [ ] Update docker-compose.yml if needed
- [ ] Run: `docker-compose up -d --build`
- [ ] Verify containers running: `docker-compose ps`
- [ ] Check logs: `docker-compose logs -f backend`
- [ ] Test app at http://localhost:3000
- [ ] Seed menu in container: `docker-compose exec backend python -m apps.agentic_barista.seed_menu`

## ☸️ Kubernetes Deployment

### Pre-Deployment
- [ ] Update kubeconfig: `aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1`
- [ ] Get AWS account ID: `aws sts get-caller-identity --query Account --output text`
- [ ] Login to ECR: `aws ecr get-login-password --region us-east-1 | docker login ...`

### Push Images
- [ ] Tag backend: `docker tag co-intelligence-backend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest`
- [ ] Push backend: `docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest`
- [ ] Tag frontend: `docker tag co-intelligence-frontend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest`
- [ ] Push frontend: `docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest`

### Deploy to EKS
- [ ] Apply manifests: `kubectl apply -f k8s/`
- [ ] Check pods: `kubectl get pods`
- [ ] Check services: `kubectl get svc`
- [ ] Check logs: `kubectl logs -f deployment/backend`
- [ ] Wait for LoadBalancer: `kubectl get svc frontend -w`

### Post-Deployment
- [ ] Get LoadBalancer URL: `kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'`
- [ ] Seed menu in pod: `kubectl exec -it deployment/backend -- python -m apps.agentic_barista.seed_menu`
- [ ] Test app at LoadBalancer URL
- [ ] Verify all features working
- [ ] Check HPA status: `kubectl get hpa`
- [ ] Monitor pod health: `kubectl get pods -w`

## 🔍 Post-Deployment Testing

### Functional Tests
- [ ] Homepage loads correctly
- [ ] Agentic Barista card visible
- [ ] Click card opens chat interface
- [ ] Model selector shows all 4 models
- [ ] "Show menu" command works
- [ ] Menu displays all 10 items
- [ ] "Add 2 lattes" adds to cart
- [ ] Cart badge shows correct count
- [ ] "Show cart" displays items and total
- [ ] "Confirm order" saves to database
- [ ] Cart clears after confirmation
- [ ] Order ID returned in response

### Performance Tests
- [ ] Response time < 2 seconds
- [ ] No memory leaks
- [ ] Database queries optimized
- [ ] Cart operations fast (< 100ms)
- [ ] Menu queries cached

### Error Handling
- [ ] Invalid commands handled gracefully
- [ ] Empty cart confirmation prevented
- [ ] Database errors caught
- [ ] API errors displayed to user
- [ ] Network errors handled

## 🔐 Security Checklist

- [ ] No API keys in frontend code
- [ ] Environment variables properly set
- [ ] Database credentials secure
- [ ] CORS configured correctly
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM)
- [ ] XSS prevention (React escaping)

## 📊 Monitoring

### Metrics to Track
- [ ] API response times
- [ ] Error rates
- [ ] Order completion rate
- [ ] Cart abandonment rate
- [ ] Most popular items
- [ ] Peak usage times

### Logging
- [ ] Backend logs accessible
- [ ] Frontend errors logged
- [ ] Database queries logged
- [ ] Agent decisions logged

### Alerts
- [ ] High error rate alert
- [ ] Slow response time alert
- [ ] Database connection issues
- [ ] Pod restart alerts

## 🚀 Production Readiness

### Performance
- [ ] Load testing completed
- [ ] Concurrent user testing done
- [ ] Database indexes added
- [ ] Caching implemented (if needed)
- [ ] CDN configured for frontend

### Scalability
- [ ] HPA configured and tested
- [ ] Database connection pooling
- [ ] Redis for cart storage (optional)
- [ ] Multiple replicas running

### Reliability
- [ ] Health checks configured
- [ ] Liveness probes working
- [ ] Readiness probes working
- [ ] Auto-restart on failure
- [ ] Backup strategy in place

### Documentation
- [ ] README updated
- [ ] API documentation complete
- [ ] Architecture diagrams created
- [ ] Runbooks written
- [ ] Troubleshooting guide available

## 📝 Rollback Plan

### If Issues Occur
1. [ ] Check pod logs: `kubectl logs -f deployment/backend`
2. [ ] Check events: `kubectl get events --sort-by='.lastTimestamp'`
3. [ ] Rollback deployment: `kubectl rollout undo deployment/backend`
4. [ ] Verify previous version working
5. [ ] Investigate issue in logs
6. [ ] Fix and redeploy

### Emergency Contacts
- [ ] DevOps team contact info
- [ ] Database admin contact
- [ ] AWS support access

## ✅ Sign-Off

- [ ] Development team tested
- [ ] QA team approved
- [ ] Product owner reviewed
- [ ] DevOps team ready
- [ ] Documentation complete
- [ ] Monitoring configured
- [ ] Rollback plan tested

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Version**: v1.0.0

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

## Quick Commands Reference

```bash
# Seed menu
python -m apps.agentic_barista.seed_menu

# Test locally
python test_barista.py

# Build Docker
docker-compose up -d --build

# Deploy K8s
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get svc
kubectl logs -f deployment/backend

# Seed in K8s
kubectl exec -it deployment/backend -- python -m apps.agentic_barista.seed_menu

# Rollback
kubectl rollout undo deployment/backend
```
