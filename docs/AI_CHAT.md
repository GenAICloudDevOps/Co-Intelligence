# AI Chat Features Guide

## Overview
The AI Chat application provides multi-model AI conversations with document upload, web search, and autonomous code execution capabilities.

## Features

### 1. **Multi-Model Support**
- **Gemini 2.5 Flash Lite**: Fast, efficient responses with function calling
- **Groq Mixtral**: High-quality reasoning
- **AWS Bedrock Nova**: Enterprise-grade AI

### 2. **Code Execution** ⚡
AI automatically runs Python code when needed to answer questions.

**How it works:**
- AI detects when computation is needed
- Generates Python code automatically
- Executes in secure AWS Lambda sandbox
- Uses result to provide accurate answers

**Examples:**
- "What's 15% of 2847?" → Executes calculation
- "Generate first 10 Fibonacci numbers" → Runs algorithm
- "What's the square root of 144?" → Uses math module

**Security:**
- Sandboxed Lambda execution
- Whitelisted safe modules only (math, json, datetime, etc.)
- Blocks dangerous modules (os, sys, subprocess)
- 30-second timeout, 512MB memory limit

See [CODE_EXECUTION.md](CODE_EXECUTION.md) for details.

### 3. **Document Upload** 📎
Upload documents to provide context to the AI.

**Supported Formats:**
- PDF (.pdf)
- Word Documents (.docx)
- Text Files (.txt)
- Markdown (.md)

**How to Use:**
1. Start a chat session (send your first message)
2. Click the 📎 upload button
3. Select your document
4. The AI will use the document content to answer questions

**Limitations:**
- Maximum 50,000 characters per document
- First 5,000 characters used per document in context
- Upload only works after starting a chat session

### 4. **Web Search** 🌐
Enable real-time web search for current information.

**Setup Required:**
1. Get a free API key from [Tavily](https://tavily.com/)
2. Add to `.env` file:
   ```
   TAVILY_API_KEY=tvly-your-actual-key-here
   ```
3. Restart the backend

**How to Use:**
1. Click "Web Search: OFF" button to toggle ON
2. Ask questions requiring current information
3. AI will search the web and provide sourced answers

**Note:** Without a valid Tavily API key, web search will not work (button is just a toggle).

### 5. **Context Memory**
The AI remembers previous messages in the conversation.

**Settings:**
- 5 pairs (10 messages)
- 10 pairs (20 messages) - Default
- 20 pairs (40 messages)
- 50 pairs (100 messages)

**Features:**
- Visual indicator showing context usage
- Clear context button to reset memory
- Adjustable context size per session

### 6. **Voice Input** 🎤
Speak your messages instead of typing.

**Requirements:**
- Chrome/Edge browser (uses Web Speech API)
- Microphone permission

**How to Use:**
1. Click the 🎤 microphone button
2. Speak your message
3. Text appears automatically in input field

### 7. **Export Conversations**
Download your chat history.

**Formats:**
- PDF: Formatted document
- TXT: Plain text with timestamps

### 8. **Session Management**
- Create multiple chat sessions
- Switch between conversations
- Delete old sessions
- Auto-save all messages

## Troubleshooting

### Chat Not Responding
**Issue:** 401 Unauthorized errors

**Solution:**
1. Make sure you're logged in
2. Check if token is valid
3. Try logging out and back in

### Upload Button Disabled
**Issue:** Can't click upload button

**Solution:**
- Start a chat first by sending a message
- Upload only works within an active session

### Web Search Not Working
**Issue:** Web search toggle doesn't fetch results

**Solution:**
1. Check if `TAVILY_API_KEY` is set in `.env`
2. Get a valid key from https://tavily.com/
3. Restart backend after adding key:
   ```bash
   kubectl rollout restart deployment/backend
   ```

### Code Execution Not Working
**Issue:** AI not running code

**Solution:**
1. Verify you're using **Gemini** model (only model with function calling)
2. Check Lambda function exists: `aws lambda get-function --function-name co-intelligence-code-executor`
3. Check backend logs: `kubectl logs deployment/backend`

### Authentication Errors
**Issue:** "Session expired" message

**Solution:**
1. Login again from homepage
2. Token expires after 30 minutes
3. Check backend logs for auth issues

## API Endpoints

### Chat
- `POST /api/apps/ai-chat/chat/stream` - Stream AI responses
- `POST /api/apps/ai-chat/sessions` - Create session
- `GET /api/apps/ai-chat/sessions` - List sessions
- `GET /api/apps/ai-chat/sessions/{id}/messages` - Get messages

### Documents
- `POST /api/apps/ai-chat/upload` - Upload document
- `GET /api/apps/ai-chat/sessions/{id}/documents` - List documents
- `DELETE /api/apps/ai-chat/documents/{id}` - Delete document

### Context
- `GET /api/apps/ai-chat/sessions/{id}/context` - Get context info

## Configuration

### Environment Variables

**Required:**
```env
GEMINI_API_KEY=your-gemini-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
DATABASE_URL=your-postgres-url
SECRET_KEY=your-secret-key
AWS_REGION=us-east-1
```

**Optional:**
```env
GROQ_API_KEY=your-groq-key
TAVILY_API_KEY=your-tavily-key  # For web search
S3_BUCKET_NAME=your-bucket      # For document storage
```

### Backend Dependencies
```
google-generativeai==0.3.2
groq>=0.11.0
boto3>=1.40.19
PyPDF2==3.0.1
python-docx==1.1.0
tavily-python==0.3.0
langgraph==1.0.1
```

## Best Practices

1. **Start Simple**: Begin with basic questions before uploading documents
2. **Context Size**: Use smaller context (5-10 pairs) for faster responses
3. **Document Size**: Keep documents under 10MB for best performance
4. **Web Search**: Only enable when you need current information
5. **Code Execution**: Use Gemini model for autonomous code execution
6. **Session Management**: Create new sessions for different topics

## Known Limitations

1. **Upload**: Only works after starting a session
2. **Web Search**: Requires Tavily API key (not included by default)
3. **Voice Input**: Chrome/Edge only
4. **Context**: Limited by model token limits
5. **Streaming**: May not work with some proxy configurations
6. **Code Execution**: Only works with Gemini model, Python only

## Future Enhancements

- [ ] Image upload and analysis
- [ ] Multi-file upload
- [ ] Advanced search filters
- [ ] Conversation branching
- [ ] Custom system prompts
- [ ] API rate limiting display
- [ ] Cost tracking per session
- [ ] Support for more languages in code execution
- [ ] Code approval before execution (optional)
