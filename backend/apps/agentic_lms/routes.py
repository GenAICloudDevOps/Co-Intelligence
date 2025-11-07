from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from auth.utils import get_current_user
from auth.models import User
from .models import LMSCourse, LMSEnrollment, LMSChatHistory, CourseResponse, EnrollmentResponse, ChatRequest, ChatResponse
from services.ai_service import ai_service
import json

router = APIRouter()


# Courses
@router.get("/courses", response_model=List[CourseResponse])
async def get_courses(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = LMSCourse.all()
    
    if category:
        query = query.filter(category=category)
    if difficulty:
        query = query.filter(difficulty=difficulty)
    if search:
        query = query.filter(title__icontains=search)
    
    courses = await query
    return [CourseResponse.model_validate(course) for course in courses]


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(course_id: int, current_user: User = Depends(get_current_user)):
    course = await LMSCourse.get_or_none(id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse.model_validate(course)


@router.get("/categories")
async def get_categories(current_user: User = Depends(get_current_user)):
    courses = await LMSCourse.all()
    categories = list(set([course.category for course in courses]))
    return {"categories": sorted(categories)}


# Enrollments
@router.get("/enrollments", response_model=List[dict])
async def get_enrollments(current_user: User = Depends(get_current_user)):
    enrollments = await LMSEnrollment.filter(user_id=current_user.id).prefetch_related('course')
    result = []
    for enrollment in enrollments:
        result.append({
            "id": enrollment.id,
            "user_id": enrollment.user_id,
            "course_id": enrollment.course.id,
            "enrolled_at": enrollment.enrolled_at,
            "progress": enrollment.progress,
            "completed": enrollment.completed,
            "course": CourseResponse.model_validate(enrollment.course)
        })
    return result


@router.post("/enrollments/{course_id}")
async def enroll_course(course_id: int, current_user: User = Depends(get_current_user)):
    course = await LMSCourse.get_or_none(id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    existing = await LMSEnrollment.get_or_none(user_id=current_user.id, course=course)
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    enrollment = await LMSEnrollment.create(user_id=current_user.id, course=course)
    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": course.id,
        "enrolled_at": enrollment.enrolled_at,
        "progress": enrollment.progress,
        "completed": enrollment.completed,
        "course": CourseResponse.model_validate(course)
    }


# Chat - simplified version using existing AI service
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    try:
        # Get all courses for context
        courses = await LMSCourse.all()
        course_list = "\n".join([f"- ID:{c.id} {c.title} ({c.category}, {c.difficulty})" for c in courses])
        
        # Get user enrollments
        enrollments = await LMSEnrollment.filter(user_id=current_user.id).prefetch_related('course')
        enrolled_courses = [e.course.title for e in enrollments]
        enrolled_ids = [e.course.id for e in enrollments]
        
        # Check if user wants to enroll
        message_lower = request.message.lower()
        enrolled_course = None
        
        if "enroll" in message_lower:
            # Try to find course by title match
            for course in courses:
                if course.title.lower() in message_lower and course.id not in enrolled_ids:
                    # Enroll the user
                    await LMSEnrollment.create(user_id=current_user.id, course=course)
                    enrolled_course = course.title
                    break
        
        if enrolled_course:
            response_text = f"✅ Great! You've been successfully enrolled in '{enrolled_course}'. You can view it under 'My Enrollments' tab. Happy learning!"
        else:
            # Build context-aware prompt
            system_context = f"""You are a helpful course advisor. Here are the available courses:

{course_list}

User is currently enrolled in: {', '.join(enrolled_courses) if enrolled_courses else 'No courses yet'}

Help the user discover courses and answer questions about them. Be conversational and helpful."""

            full_prompt = f"{system_context}\n\nUser: {request.message}"
            
            response_text = await ai_service.generate_response(
                prompt=full_prompt,
                model_name=request.model
            )
        
        await LMSChatHistory.create(
            user_id=current_user.id,
            message=request.message,
            response=response_text,
            model_used=request.model
        )
        
        return ChatResponse(response=response_text, model_used=request.model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
