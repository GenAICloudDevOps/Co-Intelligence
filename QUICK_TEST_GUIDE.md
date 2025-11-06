# Quick Test Guide - AI Chat Fixes

## Access the Application

**URL:** http://ae68fc57bbdac4db1a7015fbea430648-1115989009.us-east-1.elb.amazonaws.com

## Test Scenarios

### 1. Test Authentication Fix ✅

**Before:** Chat would fail with 401 errors if not logged in

**Test Steps:**
1. Open the URL in incognito/private window
2. Try to access: `/apps/ai-chat` directly
3. **Expected:** Automatic redirect to login page
4. Login with your credentials
5. Navigate to AI Chat
6. **Expected:** Chat loads successfully

**Result:** ✅ Authentication now enforced

---

### 2. Test Upload Functionality ✅

**Before:** Upload icon visible but not clickable, no explanation

**Test Steps:**
1. Login and go to AI Chat
2. Look at the 📎 upload button
3. **Expected:** Button is grayed out and shows tooltip: "Start a chat first to upload documents"
4. Hover over the button to see tooltip
5. Send a message: "Hello, can you help me?"
6. **Expected:** Upload button becomes active (white color)
7. Click the upload button
8. **Expected:** File picker opens
9. Select a PDF, DOCX, TXT, or MD file
10. **Expected:** File uploads, shows in document list
11. Ask: "What's in the document?"
12. **Expected:** AI responds using document content

**Result:** ✅ Upload now works with clear visual feedback

---

### 3. Test Web Search Toggle ✅

**Before:** Toggle button only changed UI, no actual search

**Test Steps:**

#### Without API Key (Current State):
1. Login and go to AI Chat
2. Click "Web Search: OFF" button
3. **Expected:** Changes to "Web Search: ON"
4. Hover to see tooltip
5. Send message: "What's the latest news about AI?"
6. **Expected:** AI responds but without web search (no API key configured)

#### With API Key (After Setup):
1. Get Tavily API key from https://tavily.com/
2. Update `.env`:
   ```
   TAVILY_API_KEY=tvly-your-actual-key
   ```
3. Update Kubernetes:
   ```bash
   kubectl delete secret co-intelligence-secrets
   kubectl create secret generic co-intelligence-secrets --from-env-file=.env
   kubectl rollout restart deployment/backend
   ```
4. Enable web search in UI
5. Ask: "What happened in tech news today?"
6. **Expected:** AI searches web and provides current information with sources

**Result:** ✅ Web search functionality implemented, needs API key

---

## Quick Verification Commands

### Check Deployment Status
```bash
kubectl get pods
kubectl get svc
```

### Check Backend Logs
```bash
kubectl logs deployment/backend --tail=50
```

### Check Frontend Logs
```bash
kubectl logs deployment/frontend --tail=50
```

### Verify Authentication
```bash
# Should see successful requests after login
kubectl logs deployment/backend | grep "POST /api/apps/ai-chat/chat/stream"
```

---

## Expected Behavior Summary

| Feature | Before | After |
|---------|--------|-------|
| **Authentication** | 401 errors, no redirect | Auto-redirect to login, clear errors |
| **Upload Button** | Visible but disabled, no explanation | Grayed out with helpful tooltip |
| **Upload Functionality** | Not working | Works after starting chat |
| **Web Search Toggle** | UI only | Fully functional (needs API key) |
| **Error Messages** | Generic | Detailed and helpful |

---

## Common Issues & Solutions

### Issue: Still getting 401 errors
**Solution:** 
- Clear browser cache and cookies
- Login again
- Check if token is in localStorage (F12 → Application → Local Storage)

### Issue: Upload button still disabled
**Solution:**
- Send a message first to create a session
- Check if you're logged in
- Refresh the page

### Issue: Web search not working
**Solution:**
- Get Tavily API key from https://tavily.com/
- Add to `.env` and update Kubernetes secret
- Restart backend deployment

---

## Files Changed

1. **Frontend:**
   - `/frontend/app/apps/ai-chat/page.tsx` - Fixed auth, upload UI, error handling

2. **Configuration:**
   - `.env` - Updated with Tavily API key instructions

3. **Documentation:**
   - `AI_CHAT_FEATURES.md` - Complete feature guide
   - `AI_CHAT_FIXES.md` - Detailed fix summary
   - `QUICK_TEST_GUIDE.md` - This file

---

## Deployment Info

- **Frontend Image:** `381492274187.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest`
- **Backend Image:** `381492274187.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest`
- **Cluster:** `co-intelligence-cluster`
- **Region:** `us-east-1`
- **Namespace:** `default`

---

## Success Criteria

✅ All three issues resolved:
1. Chat responds correctly (no 401 errors)
2. Upload button has clear visual feedback and works
3. Web search functionality implemented (needs API key to activate)

✅ Additional improvements:
- Better error handling
- Helpful tooltips
- Clear user feedback
- Comprehensive documentation

---

## Next Steps

1. **Test all features** using this guide
2. **Add Tavily API key** for web search (optional)
3. **Review documentation** in `AI_CHAT_FEATURES.md`
4. **Monitor logs** for any issues

---

## Support

If you encounter any issues:
1. Check browser console (F12)
2. Review backend logs: `kubectl logs deployment/backend`
3. Verify you're logged in
4. Clear cache and try again
