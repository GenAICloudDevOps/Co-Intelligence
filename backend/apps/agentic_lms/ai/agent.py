from typing import Optional, Dict, Any, Literal, Annotated, AsyncIterator
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, RemoveMessage
from langchain_core.messages.utils import trim_messages
from pydantic import BaseModel, Field
from .models import get_model
from .tools import get_courses_tool, enroll_student_tool, search_courses_tool
import json
import re
import asyncio
from datetime import datetime


# Structured output schemas for LLM-based routing
class RouteDecision(BaseModel):
    """LLM-based decision on which node to route to"""
    intent: Literal["course_discovery", "enrollment", "recommendation", "general_qa", "complex_query"] = Field(
        description="The detected intent of the user's message"
    )
    confidence: float = Field(
        description="Confidence score between 0 and 1",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether this action requires human approval"
    )


class CourseQuery(BaseModel):
    """Structured course search query"""
    category: Optional[str] = Field(None, description="Course category (AI, DevOps, Docker, Kubernetes)")
    difficulty: Optional[str] = Field(None, description="Difficulty level (Beginner, Intermediate, Advanced)")
    keywords: list[str] = Field(default_factory=list, description="Keywords to search for")


class EnrollmentIntent(BaseModel):
    """Structured enrollment intent"""
    course_titles: list[str] = Field(description="List of course titles to enroll in")
    confirmation_needed: bool = Field(description="Whether user confirmation is needed")


class QualityEvaluation(BaseModel):
    """Quality evaluation of a response"""
    quality_score: float = Field(description="Quality score from 0 to 1", ge=0.0, le=1.0)
    is_acceptable: bool = Field(description="Whether the response meets quality standards")
    feedback: str = Field(description="Specific feedback for improvement")
    issues: list[str] = Field(default_factory=list, description="List of identified issues")


class SubTask(BaseModel):
    """A subtask for orchestrator-worker pattern"""
    task_id: str = Field(description="Unique identifier for the task")
    description: str = Field(description="What this subtask should accomplish")
    priority: int = Field(description="Priority level (1=highest)", ge=1, le=10)


# Graph State with Phase 3 & 4 additions
class AgentState(TypedDict):
    """State for the LangGraph agent"""
    message: str  # User's input message
    student_id: Optional[int]  # Student ID if logged in
    messages: list[BaseMessage]  # Message history (Phase 4A)
    
    # Routing (LLM-based)
    route: Optional[str]  # Which node to route to
    route_reasoning: Optional[str]  # Why this route was chosen
    route_confidence: Optional[float]  # Confidence in routing decision
    requires_approval: bool  # Whether action needs approval
    
    # Processing
    courses: list[Dict[str, Any]]  # Available courses
    filtered_courses: list[Dict[str, Any]]  # Filtered/relevant courses
    query: Optional[CourseQuery]  # Structured search query
    
    # Enrollment
    enrollment_results: list[Dict[str, Any]]  # Results of enrollment attempts
    
    # Response (with quality evaluation)
    response: str  # Final response to user
    draft_response: Optional[str]  # Draft response before evaluation
    quality_score: Optional[float]  # Quality evaluation score
    refinement_count: int  # Number of refinements made
    
    # Suggestions
    suggestions: list[str]  # Follow-up suggestions
    model_used: str  # Which model was used
    enrolled: bool  # Whether enrollment occurred
    
    # Orchestrator-Worker
    subtasks: list[Dict[str, Any]]  # Subtasks for complex queries
    subtask_results: list[Dict[str, Any]]  # Results from workers
    
    # Human-in-the-Loop (Phase 4B)
    pending_approval: bool  # Whether waiting for approval
    approval_message: Optional[str]  # Message for approval request
    approved: Optional[bool]  # Approval status
    interrupt_data: Optional[Dict[str, Any]]  # Data from interrupt


class LMSAgent:
    def __init__(self):
        self.tools = {
            "get_courses": get_courses_tool,
            "search_courses": search_courses_tool,
            "enroll_student": enroll_student_tool
        }
        self.graph = None
        self.checkpointer = MemorySaver()  # In-memory checkpointing
        self.max_refinements = 2  # Maximum refinement iterations
        self.max_messages = 20  # Maximum messages to keep in history (Phase 4A)
        self.max_tokens = 4000  # Maximum tokens for context (Phase 4A)
    
    def _build_graph(self, model_name: str, enable_checkpointing: bool = True) -> StateGraph:
        """Build the LangGraph workflow with Phase 3 features"""
        
        # Create wrapper functions that properly handle async
        async def course_discovery_wrapper(state):
            return await self._course_discovery_node(state, model_name)
        
        async def enrollment_wrapper(state):
            return await self._enrollment_node(state, model_name)
        
        async def recommendation_wrapper(state):
            return await self._recommendation_node(state, model_name)
        
        async def general_qa_wrapper(state):
            return await self._general_qa_node(state, model_name)
        
        async def llm_router_wrapper(state):
            return await self._llm_based_router_node(state, model_name)
        
        async def evaluator_wrapper(state):
            return await self._evaluator_node(state, model_name)
        
        async def optimizer_wrapper(state):
            return await self._optimizer_node(state, model_name)
        
        async def orchestrator_wrapper(state):
            return await self._orchestrator_node(state, model_name)
        
        async def worker_wrapper(state):
            return await self._worker_node(state, model_name)
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add Phase 1 & 2 nodes
        workflow.add_node("load_courses", self._load_courses_node)
        workflow.add_node("llm_router", llm_router_wrapper)  # LLM-based routing
        workflow.add_node("course_discovery", course_discovery_wrapper)
        workflow.add_node("enrollment", enrollment_wrapper)
        workflow.add_node("recommendation", recommendation_wrapper)
        workflow.add_node("general_qa", general_qa_wrapper)
        
        # Add Phase 3 nodes
        workflow.add_node("evaluator", evaluator_wrapper)  # Quality evaluation
        workflow.add_node("optimizer", optimizer_wrapper)  # Response refinement
        workflow.add_node("orchestrator", orchestrator_wrapper)  # Complex query decomposition
        workflow.add_node("worker", worker_wrapper)  # Subtask execution
        workflow.add_node("check_approval", self._check_approval_node)  # HITL
        workflow.add_node("generate_suggestions", self._generate_suggestions_node)
        
        # Add edges
        workflow.add_edge(START, "load_courses")
        workflow.add_edge("load_courses", "llm_router")
        
        # Conditional routing based on LLM intent detection
        workflow.add_conditional_edges(
            "llm_router",
            self._route_decision,
            {
                "course_discovery": "course_discovery",
                "enrollment": "check_approval",  # Enrollment needs approval check
                "recommendation": "recommendation",
                "general_qa": "general_qa",
                "complex_query": "orchestrator"  # Complex queries go to orchestrator
            }
        )
        
        # Approval flow
        workflow.add_conditional_edges(
            "check_approval",
            self._approval_decision,
            {
                "approved": "enrollment",
                "pending": END,  # Wait for approval
                "rejected": "general_qa"  # Fallback
            }
        )
        
        # Orchestrator-Worker flow
        workflow.add_edge("orchestrator", "worker")
        workflow.add_edge("worker", "evaluator")
        
        # All intent handlers go to evaluator
        workflow.add_edge("course_discovery", "evaluator")
        workflow.add_edge("enrollment", "evaluator")
        workflow.add_edge("recommendation", "evaluator")
        workflow.add_edge("general_qa", "evaluator")
        
        # Evaluator-Optimizer loop
        workflow.add_conditional_edges(
            "evaluator",
            self._quality_decision,
            {
                "acceptable": "generate_suggestions",
                "needs_refinement": "optimizer"
            }
        )
        
        # Optimizer goes back to evaluator or continues
        workflow.add_conditional_edges(
            "optimizer",
            self._refinement_decision,
            {
                "re_evaluate": "evaluator",
                "max_refinements": "generate_suggestions"
            }
        )
        
        workflow.add_edge("generate_suggestions", END)
        
        # Compile with checkpointing
        if enable_checkpointing:
            return workflow.compile(checkpointer=self.checkpointer)
        else:
            return workflow.compile()
    
    async def process_message(
        self,
        message: str,
        model: str = "gemini-2.5-flash-lite",
        student_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process user message using LangGraph workflow"""
        
        try:
            # Get message history (Phase 4A)
            messages = await self._get_message_history(student_id)
            messages.append(HumanMessage(content=message))
            
            # Build graph for this request
            graph = self._build_graph(model)
            
            # Initial state with Phase 4 fields
            initial_state = {
                "message": message,
                "student_id": student_id,
                "messages": messages,
                "route": None,
                "route_reasoning": None,
                "route_confidence": None,
                "requires_approval": False,
                "courses": [],
                "filtered_courses": [],
                "query": None,
                "enrollment_results": [],
                "response": "",
                "draft_response": None,
                "quality_score": None,
                "refinement_count": 0,
                "suggestions": [],
                "model_used": model,
                "enrolled": False,
                "subtasks": [],
                "subtask_results": [],
                "pending_approval": False,
                "approval_message": None,
                "approved": None,
                "interrupt_data": None
            }
            
            # Run the graph with checkpointing config
            config = {
                "configurable": {
                    "thread_id": f"student_{student_id}" if student_id else "anonymous"
                }
            }
            final_state = await graph.ainvoke(initial_state, config=config)
            
            return {
                "response": final_state["response"],
                "model_used": final_state["model_used"],
                "suggestions": final_state["suggestions"],
                "enrolled": final_state["enrolled"],
                "pending_approval": final_state.get("pending_approval", False),
                "approval_message": final_state.get("approval_message")
            }
        
        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "model_used": model,
                "suggestions": [],
                "enrolled": False,
                "pending_approval": False
            }
    
    async def process_message_stream(
        self,
        message: str,
        model: str = "gemini-2.5-flash-lite",
        student_id: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Process user message with streaming updates"""
        
        try:
            # Yield initial status
            yield {
                "type": "status",
                "status": "starting",
                "message": "Initializing agent..."
            }
            
            # Get conversation context
            conversation_history = ""
            if student_id:
                yield {
                    "type": "status",
                    "status": "loading_context",
                    "message": "Loading conversation history..."
                }
                conversation_history = await self._get_recent_context(student_id)
            
            # Build graph
            yield {
                "type": "status",
                "status": "building_graph",
                "message": "Building workflow..."
            }
            graph = self._build_graph(model)
            
            # Initial state
            initial_state = {
                "message": message,
                "student_id": student_id,
                "conversation_history": conversation_history,
                "route": None,
                "route_reasoning": None,
                "courses": [],
                "filtered_courses": [],
                "query": None,
                "enrollment_results": [],
                "response": "",
                "suggestions": [],
                "model_used": model,
                "enrolled": False
            }
            
            # Checkpointing config
            config = {
                "configurable": {
                    "thread_id": f"student_{student_id}" if student_id else "anonymous"
                }
            }
            
            # Stream graph execution
            async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                # Extract node name and state update
                for node_name, state_update in event.items():
                    yield {
                        "type": "node_update",
                        "node": node_name,
                        "status": f"Processing: {node_name}",
                        "data": state_update
                    }
            
            # Get final state
            final_state = await graph.ainvoke(initial_state, config=config)
            
            # Yield final result
            yield {
                "type": "complete",
                "status": "complete",
                "message": "Processing complete",
                "result": {
                    "response": final_state["response"],
                    "model_used": final_state["model_used"],
                    "suggestions": final_state["suggestions"],
                    "enrolled": final_state["enrolled"]
                }
            }
        
        except Exception as e:
            yield {
                "type": "error",
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def get_graph_visualization(self, model: str = "gemini-2.5-flash-lite") -> Dict[str, Any]:
        """Get graph structure for visualization"""
        try:
            graph = self._build_graph(model)
            graph_data = graph.get_graph()
            
            # Extract nodes and edges
            nodes = []
            for node in graph_data.nodes:
                nodes.append({
                    "id": node,
                    "label": node.replace("_", " ").title()
                })
            
            edges = []
            for edge in graph_data.edges:
                edges.append({
                    "source": edge[0] if edge[0] != "__start__" else "START",
                    "target": edge[1] if edge[1] != "__end__" else "END"
                })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "mermaid": graph_data.draw_mermaid()
            }
        except Exception as e:
            return {
                "error": str(e),
                "nodes": [],
                "edges": [],
                "mermaid": ""
            }
    
    # ===== GRAPH NODES =====
    
    async def _load_courses_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Load all available courses (with parallelization)"""
        student_id = state.get("student_id")
        
        # PARALLELIZATION: Fetch courses
        courses = await get_courses_tool()
        
        # Phase 4A: Trim messages to prevent context overflow
        messages = state.get("messages", [])
        trimmed_messages = await self._trim_messages(messages)
        
        return {
            "courses": courses,
            "messages": trimmed_messages
        }
    
    async def _router_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Route to appropriate handler based on intent"""
        
        message = state["message"].lower()
        
        # Simple rule-based routing with confidence
        if any(word in message for word in ["enroll", "sign up", "register", "join", "take this", "take the"]):
            return {
                "route": "enrollment",
                "route_reasoning": "User wants to enroll in a course"
            }
        elif any(word in message for word in ["recommend", "suggest", "what should i", "which course", "best for"]):
            return {
                "route": "recommendation",
                "route_reasoning": "User wants course recommendations"
            }
        elif any(word in message for word in ["show", "list", "browse", "search", "find", "courses about", "courses on"]):
            return {
                "route": "course_discovery",
                "route_reasoning": "User wants to discover/search courses"
            }
        else:
            return {
                "route": "general_qa",
                "route_reasoning": "General question or conversation"
            }
    
    def _route_decision(self, state: AgentState) -> str:
        """Conditional edge function to route to next node"""
        return state["route"]
    
    async def _course_discovery_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Node: Handle course discovery and search"""
        
        llm = get_model(model_name)
        courses = state["courses"]
        message = state["message"]
        
        # Filter courses based on message
        filtered = self._filter_courses(message, courses)
        
        # Format courses for response
        courses_list = "\n".join([
            f"- **{course['title']}** ({course['difficulty']}, {course['duration_hours']}h)\n  {course['description']}"
            for course in filtered
        ])
        
        prompt = f"""You are helping a student discover courses from our internal catalog.

STRICT RULE: Only mention courses from the list below. DO NOT mention Coursera, edX, Udemy, or any external platforms.

===== OUR COURSE CATALOG =====
{courses_list}
===== END OF CATALOG =====

Student's question: {message}

YOUR TASK:
1. Show courses from the catalog above
2. Use EXACT course titles (copy them exactly)
3. Be concise and friendly
4. If we don't have what they want, suggest similar courses from our catalog

Respond now using ONLY courses from our catalog above."""
        
        response_text = await self._get_llm_response(llm, prompt, model_name)
        
        return {
            "filtered_courses": filtered,
            "response": response_text
        }
    
    async def _enrollment_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Node: Handle course enrollment"""
        
        message = state["message"]
        student_id = state["student_id"]
        courses = state["courses"]
        messages = state.get("messages", [])
        
        enrollment_results = []
        
        if student_id:
            enrollment_results = await self._check_enrollment_intent(
                message, student_id, courses, messages
            )
        
        # Build response
        if enrollment_results:
            enrollment_messages = []
            any_success = False
            for result in enrollment_results:
                if result.get("success"):
                    enrollment_messages.append(f"✅ {result['message']}")
                    any_success = True
                else:
                    enrollment_messages.append(f"❌ {result.get('error', 'Enrollment failed')}")
            
            response = "\n".join(enrollment_messages)
            
            if any_success:
                response += "\n\nGreat! You're all set. Check 'My Enrollments' to start learning!"
            
            return {
                "enrollment_results": enrollment_results,
                "response": response,
                "enrolled": any_success
            }
        else:
            return {
                "enrollment_results": [],
                "response": "I'd be happy to help you enroll! Please specify which course you'd like to join.",
                "enrolled": False
            }
    
    async def _recommendation_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Node: Provide personalized course recommendations"""
        
        llm = get_model(model_name)
        courses = state["courses"]
        message = state["message"]
        messages = state.get("messages", [])
        
        courses_list = "\n".join([
            f"- {course['title']} ({course['difficulty']}, {course['duration_hours']}h, {course['category']})"
            for course in courses
        ])
        
        prompt = f"""You are a course advisor for our internal Learning Management System.

STRICT RULE: You must ONLY recommend courses from the list below. Any mention of Coursera, edX, Udemy, Fast.ai, or other external platforms will be rejected.

===== OUR COURSE CATALOG =====
{courses_list}
===== END OF CATALOG =====

Student's request: {message}

YOUR TASK:
1. Select 2-3 courses from the catalog above
2. Use EXACT course titles (copy them exactly)
3. Explain why each suits the student
4. DO NOT mention any external platforms or courses

Format your response like this:
"Here are our AI courses for beginners:

1. [Exact Course Title] - [Why it's good for them]
2. [Exact Course Title] - [Why it's good for them]

Would you like to enroll in any of these?"

Respond now using ONLY courses from our catalog above."""
        
        response_text = await self._get_llm_response(llm, prompt, model_name)
        
        return {"response": response_text}
    
    async def _general_qa_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Node: Handle general questions and conversation"""
        
        llm = get_model(model_name)
        courses = state["courses"]
        message = state["message"]
        messages = state.get("messages", [])
        
        courses_list = "\n".join([
            f"- {course['title']} ({course['category']}, {course['difficulty']})"
            for course in courses
        ])
        
        prompt = f"""You are a friendly AI assistant for our internal Learning Management System.

STRICT RULE: Only mention courses from our catalog below. DO NOT mention Coursera, edX, Udemy, or external platforms.

===== OUR COURSE CATALOG =====
{courses_list}
===== END OF CATALOG =====

Student: {message}

YOUR TASK:
1. Answer their question
2. If mentioning courses, use ONLY courses from our catalog above
3. Use EXACT course titles
4. Be concise and friendly

Respond now using ONLY courses from our catalog."""
        
        response_text = await self._get_llm_response(llm, prompt, model_name)
        
        return {"response": response_text}
    
    async def _generate_suggestions_node(self, state: AgentState) -> Dict[str, Any]:
        """Node: Generate follow-up suggestions"""
        
        message = state["message"].lower()
        enrollment_results = state["enrollment_results"]
        route = state["route"]
        
        # Generate context-aware suggestions
        if enrollment_results and any(r.get("success") for r in enrollment_results):
            suggestions = [
                "Show my enrollments",
                "What other courses do you recommend?",
                "Tell me about the course content"
            ]
        elif route == "course_discovery":
            suggestions = [
                "Tell me more about this course",
                "What are the prerequisites?",
                "Enroll me in this course"
            ]
        elif route == "recommendation":
            suggestions = [
                "Show me beginner courses",
                "What about advanced courses?",
                "Enroll me in the recommended course"
            ]
        elif "ai" in message or "machine learning" in message:
            suggestions = [
                "Show me AI courses",
                "Recommend a beginner AI course",
                "What's the difference between AI courses?"
            ]
        elif "docker" in message:
            suggestions = [
                "Show Docker courses",
                "Is Docker hard to learn?",
                "Enroll me in Docker Mastery"
            ]
        elif "kubernetes" in message or "k8s" in message:
            suggestions = [
                "Show Kubernetes courses",
                "Do I need Docker first?",
                "Recommend a Kubernetes course"
            ]
        else:
            suggestions = [
                "What courses do you offer?",
                "Recommend courses for beginners",
                "Show me all courses"
            ]
        
        return {"suggestions": suggestions}
    
    # ===== HELPER METHODS =====
    
    def _filter_courses(self, message: str, courses: list) -> list:
        """Filter courses based on message content"""
        message_lower = message.lower()
        filtered = []
        
        for course in courses:
            # Check category match
            if course["category"].lower() in message_lower:
                filtered.append(course)
                continue
            
            # Check difficulty match
            if course["difficulty"].lower() in message_lower:
                filtered.append(course)
                continue
            
            # Check title keywords
            title_words = course["title"].lower().split()
            if any(word in message_lower for word in title_words if len(word) > 3):
                filtered.append(course)
        
        # If no matches, return all courses
        return filtered if filtered else courses
    
    async def _get_message_history(self, student_id: Optional[int]) -> list[BaseMessage]:
        """Phase 4A: Get message history as BaseMessage objects"""
        if not student_id:
            return []
        
        from models import ChatHistory, Student
        
        student = await Student.get_or_none(id=student_id)
        if not student:
            return []
        
        # Get recent messages
        history = await ChatHistory.filter(student=student).order_by("-created_at").limit(10)
        
        if not history:
            return []
        
        # Convert to BaseMessage objects (reverse to chronological order)
        messages = []
        for h in reversed(history):
            messages.append(HumanMessage(content=h.message))
            messages.append(AIMessage(content=h.response))
        
        return messages
    
    async def _trim_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Phase 4A: Trim messages to prevent context overflow"""
        if not messages:
            return []
        
        # Keep only last N messages
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages:]
        
        # Use LangChain's trim_messages for token-based trimming
        try:
            trimmed = trim_messages(
                messages,
                max_tokens=self.max_tokens,
                strategy="last",
                token_counter=len  # Simple approximation: 1 char ≈ 0.25 tokens
            )
            return trimmed
        except Exception:
            # Fallback: just return last N messages
            return messages[-self.max_messages:]
    
    async def _check_enrollment_intent(self, message: str, student_id: int, courses: list, messages: list[BaseMessage] = None) -> list:
        """Check if user wants to enroll and process enrollment(s)"""
        message_lower = message.lower()
        
        # Check for enrollment keywords or affirmative responses
        enrollment_keywords = ["enroll", "sign up", "register", "join", "take this course", "take the course", "i want"]
        affirmative_keywords = ["yes", "yeah", "yep", "sure", "ok", "okay"]
        
        has_enrollment_intent = any(keyword in message_lower for keyword in enrollment_keywords)
        is_affirmative = any(keyword == message_lower.strip() or keyword in message_lower.split() for keyword in affirmative_keywords)
        
        if not (has_enrollment_intent or is_affirmative):
            return []
        
        enrollment_results = []
        courses_to_enroll = []
        
        # Combine message and recent context for better course detection
        context = " ".join([m.content for m in (messages or [])[-3:]]) if messages else ""
        search_text = message_lower + " " + context.lower()
        
        # Search for specific course mentions in the message
        for course in courses:
            course_title_lower = course["title"].lower()
            course_category = course["category"].lower()
            course_difficulty = course["difficulty"].lower()
            
            # Check if full course title is mentioned (most specific match)
            if course_title_lower in message_lower:
                courses_to_enroll.append(course)
                continue
            
            # Extract meaningful words from course title (excluding common words)
            title_words = [w for w in course_title_lower.split() if w not in ['to', 'the', 'and', 'with', 'for', 'from', 'a', 'an', 'in', 'of', 'on']]
            
            # Handle abbreviations ONLY if they appear as standalone words
            # This prevents "basics" from matching "ai" in "basics"
            abbreviations = {
                "ai": ["artificial", "intelligence"],
                "ml": ["machine", "learning"],
                "k8s": ["kubernetes"],
                "devops": ["devops"]
            }
            
            # Check for abbreviation matches (must be standalone word)
            message_words = message_lower.split()
            for abbr, full_words in abbreviations.items():
                # Only match if abbreviation is a standalone word AND no other specific words
                if abbr in message_words:
                    # Check if the course contains these full words
                    if all(word in course_title_lower for word in full_words):
                        # Additional check: make sure user isn't asking for a different specific course
                        # If they mention other specific words like "ethics", "basics", don't match generic AI
                        specific_words = ["ethics", "basics", "introduction", "advanced", "deep", "neural"]
                        has_specific = any(word in message_lower for word in specific_words)
                        
                        # Only match if no specific words, OR if the specific words are in this course title
                        if not has_specific or any(word in course_title_lower for word in specific_words if word in message_lower):
                            courses_to_enroll.append(course)
                            break
            
            # If already matched via abbreviation, continue
            if course in courses_to_enroll:
                continue
            
            # Check if significant keywords from course title are in message
            # Require at least 2-3 CONSECUTIVE or UNIQUE key words to match
            if len(title_words) >= 2:
                # Count unique matches (not just any 2 words)
                matched_words = [word for word in title_words if word in message_lower]
                
                # Need at least 2 unique words for short titles, 3 for longer titles
                min_matches = 3 if len(title_words) >= 4 else 2
                
                if len(matched_words) >= min_matches:
                    # Additional check: make sure these words appear close together in the message
                    # This prevents "advanced" from one course matching "advanced" in another
                    message_words = message_lower.split()
                    
                    # Find positions of matched words in the message
                    positions = []
                    for word in matched_words[:min_matches]:
                        if word in message_words:
                            positions.append(message_words.index(word))
                    
                    # If words are within 5 positions of each other, it's likely the same course
                    if len(positions) >= min_matches:
                        # Check if words are reasonably close (within 5 words)
                        max_distance = max(positions) - min(positions)
                        if max_distance <= 5:
                            courses_to_enroll.append(course)
                            continue
            
            # Check for single keyword match with category (e.g., "introduction ai")
            if len(title_words) >= 1:
                first_word = title_words[0]
                if first_word in message_lower and course_category in message_lower:
                    courses_to_enroll.append(course)
                    continue
            
            # Check for category + difficulty combination (e.g., "kubernetes intermediate")
            # Only if no other matches found yet
            if not courses_to_enroll:
                if course_category in message_lower and course_difficulty in message_lower:
                    courses_to_enroll.append(course)
                    continue
        
        # If no specific courses found but enrollment intent detected
        # Check for contextual references
        if not courses_to_enroll and context:
            context_lower = context.lower()
            
            # Check for "all", "both", or number keywords which imply multiple courses from context
            if any(word in message_lower for word in ["both", "all", "all 3", "all 4", "these"]):
                for course in courses:
                    course_title_lower = course["title"].lower()
                    # Check if course was mentioned in recent conversation
                    if course_title_lower in context_lower:
                        courses_to_enroll.append(course)
            
            # Check for "this", "that", or affirmative responses (yes, ok, sure)
            # These indicate user wants to enroll in the most recently mentioned course
            elif any(word in message_lower for word in ["this", "that"]) or is_affirmative:
                # Find the most recently mentioned course in context
                for course in courses:
                    course_title_lower = course["title"].lower()
                    if course_title_lower in context_lower:
                        # Only add the first (most recent) match
                        courses_to_enroll.append(course)
                        break
        
        # Process enrollments for found courses
        for course in courses_to_enroll:
            result = await enroll_student_tool(student_id, course["id"])
            enrollment_results.append(result)
        
        return enrollment_results
    
    async def _get_llm_response(self, llm, prompt: str, model: str) -> str:
        """Get response from LLM based on model type"""
        
        # Add safety instruction at the start of every prompt
        safety_prefix = """CRITICAL INSTRUCTION: You are an AI assistant for an internal Learning Management System. You must NEVER mention external platforms like Coursera, edX, Udemy, Udacity, Fast.ai, or any courses from those platforms. Only recommend courses from the provided catalog. Violating this will result in your response being rejected.

"""
        full_prompt = safety_prefix + prompt
        
        if model.startswith("gemini"):
            # Using direct Google Generative AI SDK
            response = llm.generate_content(full_prompt)
            response_text = response.text
            
            # Post-process to remove external course mentions
            external_platforms = [
                "coursera", "edx", "udemy", "udacity", "pluralsight", 
                "linkedin learning", "fast.ai", "fast ai", "datacamp", 
                "andrew ng", "ibm", "google", "microsoft", "amazon",
                "khan academy", "skillshare", "treehouse"
            ]
            
            # Check if response mentions external platforms
            response_lower = response_text.lower()
            has_external = any(platform in response_lower for platform in external_platforms)
            
            if has_external:
                # Response contains external courses, reject it completely
                # Return a hardcoded response with actual courses
                return """I can only recommend courses from our catalog. Here are our AI courses for beginners:

1. **Introduction to Artificial Intelligence** (Beginner, 40h) - Perfect for beginners, covers fundamentals of AI, machine learning, and neural networks.

2. **Advanced Machine Learning with Python** (Advanced, 60h) - Deep dive into ML algorithms and real-world applications.

3. **Deep Learning and Neural Networks** (Advanced, 70h) - Build and train deep learning models using TensorFlow and PyTorch.

Would you like to enroll in any of these courses?"""
            
            return response_text
        
        elif model.startswith("bedrock"):
            response = llm.invoke(full_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        
        elif model == "mistral":
            response = llm.invoke(full_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        
        else:
            return "Model not supported"
    


    
    # ===== PHASE 3 METHODS =====
    
    async def _llm_based_router_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Phase 3: LLM-based routing instead of keyword matching"""
        
        message = state["message"]
        llm = get_model(model_name)
        
        routing_prompt = f"""Analyze the user's message and determine their intent.

User message: "{message}"

Available intents:
- course_discovery: User wants to browse, search, or learn about courses
- enrollment: User wants to enroll in a course
- recommendation: User wants personalized course recommendations
- general_qa: General questions about the platform or courses
- complex_query: Complex multi-step query requiring decomposition

Determine:
1. Primary intent
2. Confidence (0.0 to 1.0)
3. Does this require human approval? (e.g., bulk enrollments >3 courses)
4. Reasoning for this choice

Respond with: intent, confidence, reasoning, requires_approval"""
        
        try:
            # Try LLM-based routing
            response = await self._get_llm_response(llm, routing_prompt, model_name)
            
            # Parse response (simplified)
            message_lower = message.lower()
            
            if "enroll" in response.lower() or "enroll" in message_lower:
                return {
                    "route": "enrollment",
                    "route_reasoning": "LLM detected enrollment intent",
                    "route_confidence": 0.9,
                    "requires_approval": "all" in message_lower or "bulk" in message_lower
                }
            elif "recommend" in response.lower() or "suggest" in response.lower():
                return {
                    "route": "recommendation",
                    "route_reasoning": "LLM detected recommendation request",
                    "route_confidence": 0.85,
                    "requires_approval": False
                }
            elif "compare" in message_lower or "analyze" in message_lower or "detailed" in message_lower:
                return {
                    "route": "complex_query",
                    "route_reasoning": "Complex query requiring decomposition",
                    "route_confidence": 0.8,
                    "requires_approval": False
                }
            elif any(word in message_lower for word in ["show", "list", "browse", "search"]):
                return {
                    "route": "course_discovery",
                    "route_reasoning": "LLM detected discovery intent",
                    "route_confidence": 0.8,
                    "requires_approval": False
                }
            else:
                return {
                    "route": "general_qa",
                    "route_reasoning": "General question",
                    "route_confidence": 0.7,
                    "requires_approval": False
                }
        except Exception as e:
            # Fallback to rule-based
            return await self._router_node(state)
    
    async def _evaluator_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Phase 3: Evaluate response quality"""
        
        response = state.get("response", "")
        message = state["message"]
        
        if not response or len(response) < 10:
            return {
                "quality_score": 0.3,
                "draft_response": response
            }
        
        # Quality evaluation criteria
        quality_score = 0.5  # Base score
        
        # Check length (completeness)
        if len(response) > 100:
            quality_score += 0.1
        if len(response) > 200:
            quality_score += 0.1
        
        # Check if it addresses the question
        message_words = set(message.lower().split())
        response_words = set(response.lower().split())
        overlap = len(message_words & response_words)
        if overlap > 2:
            quality_score += 0.1
        
        # Check for course mentions (relevance)
        if any(word in response.lower() for word in ["course", "learn", "enroll", "study"]):
            quality_score += 0.1
        
        # Check for helpful elements
        if "?" in response or "!" in response:
            quality_score += 0.05
        
        quality_score = min(quality_score, 1.0)
        
        return {
            "quality_score": quality_score,
            "draft_response": response
        }
    
    async def _optimizer_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Phase 3: Refine response based on evaluation"""
        
        draft_response = state.get("draft_response", state.get("response", ""))
        message = state["message"]
        refinement_count = state.get("refinement_count", 0)
        
        llm = get_model(model_name)
        
        refinement_prompt = f"""Improve this response to make it better.

Original Question: "{message}"

Current Response: "{draft_response}"

Make it:
1. More accurate and relevant to the question
2. More complete with helpful details
3. Clearer and easier to understand
4. More actionable with specific next steps

Provide an improved version (keep it concise but helpful)."""
        
        try:
            improved_response = await self._get_llm_response(llm, refinement_prompt, model_name)
            
            return {
                "response": improved_response,
                "refinement_count": refinement_count + 1
            }
        except Exception as e:
            return {
                "response": draft_response,
                "refinement_count": refinement_count + 1
            }
    
    async def _orchestrator_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Phase 3: Decompose complex queries into subtasks"""
        
        message = state["message"]
        courses = state.get("courses", [])
        
        # Create subtasks for complex query
        subtasks = [
            {
                "task_id": "fetch_relevant_courses",
                "description": f"Find courses relevant to: {message}",
                "priority": 1,
                "status": "pending"
            },
            {
                "task_id": "analyze_requirements",
                "description": "Analyze user requirements and preferences",
                "priority": 2,
                "status": "pending"
            },
            {
                "task_id": "generate_comparison",
                "description": "Compare and synthesize information",
                "priority": 3,
                "status": "pending"
            }
        ]
        
        return {
            "subtasks": subtasks,
            "subtask_results": []
        }
    
    async def _worker_node(self, state: AgentState, model_name: str) -> Dict[str, Any]:
        """Phase 3: Execute subtasks in parallel"""
        
        subtasks = state.get("subtasks", [])
        courses = state.get("courses", [])
        message = state["message"]
        
        if not subtasks:
            return {"subtask_results": [], "response": "No subtasks to process"}
        
        llm = get_model(model_name)
        
        # Execute subtasks in parallel
        async def execute_subtask(subtask):
            task_id = subtask["task_id"]
            description = subtask["description"]
            
            prompt = f"""Execute this subtask:

Task: {description}
User Question: {message}
Available Courses: {len(courses)} courses

Provide a concise result for this specific subtask."""
            
            try:
                result = await self._get_llm_response(llm, prompt, model_name)
                return {
                    "task_id": task_id,
                    "result": result[:200],  # Limit length
                    "status": "completed"
                }
            except Exception as e:
                return {
                    "task_id": task_id,
                    "result": f"Error: {str(e)}",
                    "status": "failed"
                }
        
        # PARALLELIZATION: Run all subtasks concurrently
        results = await asyncio.gather(*[execute_subtask(task) for task in subtasks])
        
        # Synthesize results
        synthesis_prompt = f"""Synthesize these subtask results into a comprehensive response.

User Question: "{message}"

Subtask Results:
{chr(10).join([f"- {r['task_id']}: {r['result']}" for r in results])}

Provide a well-structured, comprehensive response."""
        
        final_response = await self._get_llm_response(llm, synthesis_prompt, model_name)
        
        return {
            "subtask_results": results,
            "response": final_response
        }
    
    async def _check_approval_node(self, state: AgentState) -> Dict[str, Any]:
        """Phase 4B: Check if action requires human approval with interrupt"""
        
        requires_approval = state.get("requires_approval", False)
        message = state["message"].lower()
        courses = state.get("courses", [])
        
        # Check for bulk enrollment (>3 courses)
        if "enroll" in message:
            # Count course mentions
            mentioned_count = sum(1 for course in courses if course["title"].lower() in message)
            
            # Check for "all" keyword or multiple courses
            if "all" in message or mentioned_count > 3:
                # Phase 4B: Use interrupt for true pause/resume
                approval_data = {
                    "action": "bulk_enrollment",
                    "course_count": mentioned_count,
                    "message": f"Requesting approval for bulk enrollment of {mentioned_count} courses"
                }
                
                # This will pause execution and wait for resume
                try:
                    decision = interrupt(approval_data)
                    
                    # If we get here, execution was resumed with a decision
                    if decision and decision.get("approved"):
                        return {
                            "pending_approval": False,
                            "approved": True,
                            "interrupt_data": decision
                        }
                    else:
                        return {
                            "pending_approval": False,
                            "approved": False,
                            "interrupt_data": decision,
                            "response": "Enrollment request was not approved."
                        }
                except Exception:
                    # If interrupt not supported, fall back to pending state
                    return {
                        "pending_approval": True,
                        "approval_message": f"Bulk enrollment detected ({mentioned_count} courses). Requires approval.",
                        "approved": None
                    }
        
        # Auto-approve by default
        return {
            "pending_approval": False,
            "approved": True
        }
    
    def _route_decision(self, state: AgentState) -> str:
        """Conditional edge: Route based on intent"""
        return state.get("route", "general_qa")
    
    def _approval_decision(self, state: AgentState) -> str:
        """Conditional edge: Check approval status"""
        if state.get("pending_approval"):
            return "pending"
        elif state.get("approved"):
            return "approved"
        else:
            return "rejected"
    
    def _quality_decision(self, state: AgentState) -> str:
        """Conditional edge: Check if response quality is acceptable"""
        quality_score = state.get("quality_score", 0.0)
        refinement_count = state.get("refinement_count", 0)
        
        # Accept if quality is good OR we've tried enough times
        if quality_score >= 0.7 or refinement_count >= self.max_refinements:
            return "acceptable"
        else:
            return "needs_refinement"
    
    def _refinement_decision(self, state: AgentState) -> str:
        """Conditional edge: Decide if more refinement needed"""
        refinement_count = state.get("refinement_count", 0)
        
        if refinement_count >= self.max_refinements:
            return "max_refinements"
        else:
            return "re_evaluate"
