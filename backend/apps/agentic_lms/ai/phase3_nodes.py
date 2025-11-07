"""
Phase 3 Advanced LangGraph Nodes
- LLM-based Routing
- Evaluator-Optimizer
- Orchestrator-Worker
- Human-in-the-Loop
"""
from typing import Dict, Any
import asyncio
from pydantic import BaseModel, Field
from typing import Literal


# These will be methods added to LMSAgent class
# Keeping them here for organization

async def llm_based_router_node(self, state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Phase 3: LLM-based routing instead of keyword matching"""
    
    llm = self.get_model(model_name)
    message = state["message"]
    
    # Use LLM with structured output for routing
    router_llm = llm.with_structured_output(self.RouteDecision) if hasattr(llm, 'with_structured_output') else None
    
    if router_llm:
        # LLM-based routing
        routing_prompt = f"""Analyze the user's message and determine their intent.

User message: "{message}"

Available intents:
- course_discovery: User wants to browse, search, or learn about courses
- enrollment: User wants to enroll in a course
- recommendation: User wants personalized course recommendations
- general_qa: General questions about the platform or courses
- complex_query: Complex multi-step query requiring decomposition

Consider:
1. What is the primary intent?
2. How confident are you? (0.0 to 1.0)
3. Does this require human approval? (e.g., bulk enrollments, account changes)
4. Why did you choose this intent?

Provide your analysis."""
        
        try:
            decision = await router_llm.ainvoke(routing_prompt)
            return {
                "route": decision.intent,
                "route_reasoning": decision.reasoning,
                "route_confidence": decision.confidence,
                "requires_approval": decision.requires_approval
            }
        except:
            # Fallback to rule-based
            pass
    
    # Fallback to rule-based routing
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["enroll", "sign up", "register"]):
        return {
            "route": "enrollment",
            "route_reasoning": "Keyword-based: enrollment intent detected",
            "route_confidence": 0.8,
            "requires_approval": False
        }
    elif any(word in message_lower for word in ["recommend", "suggest", "which course"]):
        return {
            "route": "recommendation",
            "route_reasoning": "Keyword-based: recommendation request",
            "route_confidence": 0.7,
            "requires_approval": False
        }
    elif any(word in message_lower for word in ["show", "list", "browse", "search"]):
        return {
            "route": "course_discovery",
            "route_reasoning": "Keyword-based: discovery intent",
            "route_confidence": 0.7,
            "requires_approval": False
        }
    elif any(word in message_lower for word in ["compare", "analyze", "detailed report"]):
        return {
            "route": "complex_query",
            "route_reasoning": "Complex query requiring decomposition",
            "route_confidence": 0.6,
            "requires_approval": False
        }
    else:
        return {
            "route": "general_qa",
            "route_reasoning": "Default: general question",
            "route_confidence": 0.5,
            "requires_approval": False
        }


async def evaluator_node(self, state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Phase 3: Evaluate response quality"""
    
    response = state.get("response", "")
    message = state["message"]
    
    if not response:
        return {
            "quality_score": 0.0,
            "draft_response": response
        }
    
    llm = self.get_model(model_name)
    
    evaluation_prompt = f"""Evaluate the quality of this response.

User Question: "{message}"

Response: "{response}"

Evaluate based on:
1. Relevance: Does it answer the question?
2. Accuracy: Is the information correct?
3. Completeness: Is it thorough enough?
4. Clarity: Is it easy to understand?
5. Helpfulness: Does it provide value?

Provide:
- quality_score: 0.0 to 1.0 (0.7+ is acceptable)
- is_acceptable: true/false
- feedback: Specific suggestions for improvement
- issues: List of problems found

Score 0.7+ means acceptable, below needs refinement."""
    
    try:
        # Simple quality check for now
        quality_score = 0.8 if len(response) > 50 else 0.5
        
        return {
            "quality_score": quality_score,
            "draft_response": response
        }
    except Exception as e:
        return {
            "quality_score": 0.6,
            "draft_response": response
        }


async def optimizer_node(self, state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Phase 3: Refine response based on evaluation"""
    
    draft_response = state.get("draft_response", state.get("response", ""))
    message = state["message"]
    refinement_count = state.get("refinement_count", 0)
    
    llm = self.get_model(model_name)
    
    refinement_prompt = f"""Improve this response based on the feedback.

Original Question: "{message}"

Current Response: "{draft_response}"

Make it:
1. More accurate and relevant
2. More complete and thorough
3. Clearer and easier to understand
4. More helpful and actionable

Provide an improved version."""
    
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


async def orchestrator_node(self, state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Phase 3: Decompose complex queries into subtasks"""
    
    message = state["message"]
    llm = self.get_model(model_name)
    
    orchestration_prompt = f"""Break down this complex query into subtasks.

Query: "{message}"

Identify 2-4 subtasks that need to be completed.
For each subtask provide:
- task_id: unique identifier
- description: what needs to be done
- priority: 1 (highest) to 10 (lowest)

Example subtasks:
- Fetch relevant courses
- Analyze user's background
- Compare course features
- Generate recommendations"""
    
    # For now, create simple subtasks
    subtasks = [
        {
            "task_id": "fetch_data",
            "description": "Fetch relevant course information",
            "priority": 1,
            "status": "pending"
        },
        {
            "task_id": "analyze",
            "description": "Analyze and process the information",
            "priority": 2,
            "status": "pending"
        },
        {
            "task_id": "synthesize",
            "description": "Synthesize final response",
            "priority": 3,
            "status": "pending"
        }
    ]
    
    return {
        "subtasks": subtasks,
        "subtask_results": []
    }


async def worker_node(self, state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Phase 3: Execute subtasks in parallel"""
    
    subtasks = state.get("subtasks", [])
    courses = state.get("courses", [])
    message = state["message"]
    
    if not subtasks:
        return {"subtask_results": [], "response": "No subtasks to process"}
    
    llm = self.get_model(model_name)
    
    # Execute subtasks in parallel
    async def execute_subtask(subtask):
        task_id = subtask["task_id"]
        description = subtask["description"]
        
        prompt = f"""Execute this subtask:

Task: {description}
Context: User asked "{message}"
Available courses: {len(courses)} courses

Provide a concise result for this subtask."""
        
        try:
            result = await self._get_llm_response(llm, prompt, model_name)
            return {
                "task_id": task_id,
                "result": result,
                "status": "completed"
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "result": f"Error: {str(e)}",
                "status": "failed"
            }
    
    # Run subtasks in parallel
    results = await asyncio.gather(*[execute_subtask(task) for task in subtasks])
    
    # Synthesize results
    synthesis_prompt = f"""Synthesize these subtask results into a final response.

User Question: "{message}"

Subtask Results:
{chr(10).join([f"- {r['task_id']}: {r['result']}" for r in results])}

Provide a comprehensive, well-structured response."""
    
    final_response = await self._get_llm_response(llm, synthesis_prompt, model_name)
    
    return {
        "subtask_results": results,
        "response": final_response
    }


def check_approval_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 3: Check if action requires human approval"""
    
    requires_approval = state.get("requires_approval", False)
    message = state["message"]
    
    # Check if enrollment requires approval
    # For now, auto-approve single enrollments, require approval for bulk
    if "enroll" in message.lower():
        # Count how many courses mentioned
        courses = state.get("courses", [])
        mentioned_courses = sum(1 for course in courses if course["title"].lower() in message.lower())
        
        if mentioned_courses > 3:
            return {
                "pending_approval": True,
                "approval_message": f"Bulk enrollment detected ({mentioned_courses} courses). Requires approval.",
                "approved": None
            }
    
    # Auto-approve by default
    return {
        "pending_approval": False,
        "approved": True
    }


def route_decision(self, state: Dict[str, Any]) -> str:
    """Conditional edge: Route based on intent"""
    return state.get("route", "general_qa")


def approval_decision(self, state: Dict[str, Any]) -> str:
    """Conditional edge: Check approval status"""
    if state.get("pending_approval"):
        return "pending"
    elif state.get("approved"):
        return "approved"
    else:
        return "rejected"


def quality_decision(self, state: Dict[str, Any]) -> str:
    """Conditional edge: Check if response quality is acceptable"""
    quality_score = state.get("quality_score", 0.0)
    refinement_count = state.get("refinement_count", 0)
    
    if quality_score >= 0.7 or refinement_count >= 2:
        return "acceptable"
    else:
        return "needs_refinement"


def refinement_decision(self, state: Dict[str, Any]) -> str:
    """Conditional edge: Decide if more refinement needed"""
    refinement_count = state.get("refinement_count", 0)
    
    if refinement_count >= self.max_refinements:
        return "max_refinements"
    else:
        return "re_evaluate"
