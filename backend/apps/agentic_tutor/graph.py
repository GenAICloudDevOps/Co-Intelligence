from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

class TutorState(TypedDict):
    user_id: int
    session_id: int
    topic: str
    difficulty: str
    user_message: str
    conversation_history: list
    intent: str
    response: str
    current_question: dict
    assessment_mode: bool

def detect_intent(state: TutorState) -> TutorState:
    """Detect user intent"""
    message = state['user_message'].lower()
    
    if any(word in message for word in ['quiz', 'test', 'assess', 'practice']):
        state['intent'] = 'assess'
    elif any(word in message for word in ['hint', 'help', 'stuck', 'clue']):
        state['intent'] = 'hint'
    elif any(word in message for word in ['progress', 'score', 'stats']):
        state['intent'] = 'progress'
    elif state.get('assessment_mode'):
        state['intent'] = 'grade'
    else:
        state['intent'] = 'teach'
    
    return state

def tutor_agent(state: TutorState) -> TutorState:
    """Main teaching agent"""
    prompt = f"""You are an expert tutor teaching {state['topic']}.
Difficulty level: {state['difficulty']}

Conversation history:
{state['conversation_history'][-4:] if state['conversation_history'] else 'New conversation'}

Student question: {state['user_message']}

Provide a clear, concise explanation with examples. Be encouraging and adaptive."""

    response = model.generate_content(prompt)
    state['response'] = response.text
    return state

def assessor_agent(state: TutorState) -> TutorState:
    """Generate assessment questions"""
    prompt = f"""Generate a {state['difficulty']} level question about {state['topic']}.

Format:
Question: [question text]
Type: [mcq/coding/short_answer]
Options: [if MCQ, provide 4 options]
Correct Answer: [answer]

Make it practical and test understanding."""

    response = model.generate_content(prompt)
    text = response.text
    
    state['current_question'] = {
        'question': text.split('Question:')[1].split('Type:')[0].strip() if 'Question:' in text else text,
        'type': 'mcq',
        'generated': text
    }
    state['assessment_mode'] = True
    state['response'] = state['current_question']['question']
    return state

def grader_agent(state: TutorState) -> TutorState:
    """Grade student answers"""
    prompt = f"""Question: {state['current_question'].get('question', 'Previous question')}
Student Answer: {state['user_message']}

Evaluate the answer:
1. Is it correct? (Yes/No)
2. Score (0-100)
3. Brief feedback
4. What they got right/wrong

Be constructive and encouraging."""

    response = model.generate_content(prompt)
    state['response'] = response.text
    state['assessment_mode'] = False
    return state

def hint_agent(state: TutorState) -> TutorState:
    """Provide progressive hints"""
    prompt = f"""Student is stuck on: {state['current_question'].get('question', state['user_message'])}

Provide a helpful hint that:
- Doesn't give away the answer
- Guides their thinking
- Encourages them to try again

Keep it brief and supportive."""

    response = model.generate_content(prompt)
    state['response'] = response.text
    return state

def progress_agent(state: TutorState) -> TutorState:
    """Show progress summary"""
    state['response'] = "Progress tracking will show your stats, scores, and recommendations."
    return state

def route_intent(state: TutorState) -> Literal["teach", "assess", "grade", "hint", "progress"]:
    """Route to appropriate agent"""
    return state['intent']

# Build graph
def create_tutor_graph():
    workflow = StateGraph(TutorState)
    
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("teach", tutor_agent)
    workflow.add_node("assess", assessor_agent)
    workflow.add_node("grade", grader_agent)
    workflow.add_node("hint", hint_agent)
    workflow.add_node("progress", progress_agent)
    
    workflow.set_entry_point("detect_intent")
    
    workflow.add_conditional_edges(
        "detect_intent",
        route_intent,
        {
            "teach": "teach",
            "assess": "assess",
            "grade": "grade",
            "hint": "hint",
            "progress": "progress"
        }
    )
    
    workflow.add_edge("teach", END)
    workflow.add_edge("assess", END)
    workflow.add_edge("grade", END)
    workflow.add_edge("hint", END)
    workflow.add_edge("progress", END)
    
    return workflow.compile()
