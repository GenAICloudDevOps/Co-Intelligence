# Agentic Tutor - Multi-Agent Architecture

## Agent Flow Diagram

```
                         USER INPUT
                    "Teach me" / "Quiz me"
                             │
                             ▼
                    ┌────────────────┐
                    │ Intent Detector│ ◄─── Routes to correct agent
                    └────────┬───────┘
                             │
        ┌────────────────────┼────────────────────┬──────────────┐
        │                    │                    │              │
        ▼                    ▼                    ▼              ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌──────────┐
│ 👨‍🏫 TUTOR     │   │ 📝 ASSESSOR   │   │ 💡 HINT       │   │ 📊 PROGRESS│
│ Explains      │   │ Creates       │   │ Guides        │   │ Tracks    │
│ concepts      │   │ quizzes       │   │ thinking      │   │ stats     │
└───────┬───────┘   └───────┬───────┘   └───────────────┘   └──────────┘
        │                    │
        │                    ▼
        │           ┌───────────────┐
        │           │ ✅ GRADER     │
        │           │ Evaluates     │
        │           │ & scores      │
        │           └───────┬───────┘
        │                    │
        └────────────────────┼─────────────────────────────────┐
                             │                                  │
                             ▼                                  ▼
                    ┌────────────────┐                 ┌────────────────┐
                    │   DATABASE     │                 │   RESPONSE     │
                    │   (Postgres)   │                 │   to User      │
                    └────────────────┘                 └────────────────┘
```

## 5 Agents

| Agent | Trigger | Function |
|-------|---------|----------|
| 👨‍🏫 **Tutor** | "teach", "explain" | Explains concepts with examples |
| 📝 **Assessor** | "quiz", "test" | Generates questions (MCQ/coding) |
| ✅ **Grader** | Answer submitted | Evaluates & provides feedback |
| 💡 **Hint** | "help", "stuck" | Progressive hints (3 levels) |
| 📊 **Progress** | "stats", "progress" | Tracks performance & recommends |

## Example Flow

```
User: "Give me a Python quiz"
  → Assessor: Generates question
  → User: Submits answer
  → Grader: Scores (90/100) + feedback
  → Progress: Updates stats
  → Response: "Great! Score: 90/100..."
```

## Tech Stack
- **LangGraph**: Agent orchestration
- **Gemini 2.0**: AI model
- **PostgreSQL**: Data storage
- **FastAPI + Next.js**: Backend + Frontend

## Key Features
✅ 15 topics across 5 categories  
✅ Adaptive difficulty  
✅ Real-time feedback  
✅ Progress tracking  
✅ Natural conversation
