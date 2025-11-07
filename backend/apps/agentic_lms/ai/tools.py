from apps.agentic_lms.models import LMSCourse, LMSEnrollment
from typing import Optional, List, Dict


async def get_courses_tool(category: Optional[str] = None) -> List[Dict]:
    """Get all courses or filter by category"""
    query = LMSCourse.all()
    if category:
        query = query.filter(category=category)
    
    courses = await query
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "difficulty": c.difficulty,
            "duration_hours": c.duration_hours
        }
        for c in courses
    ]


async def search_courses_tool(query: str) -> List[Dict]:
    """Search courses by title or description"""
    courses = await LMSCourse.filter(
        title__icontains=query
    )
    
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "difficulty": c.difficulty
        }
        for c in courses
    ]


async def enroll_student_tool(student_id: int, course_id: int) -> Dict:
    """Enroll a student in a course"""
    course = await LMSCourse.get_or_none(id=course_id)
    if not course:
        return {"success": False, "error": "Course not found"}
    
    existing = await LMSEnrollment.get_or_none(
        user_id=student_id,
        course_id=course_id
    )
    if existing:
        return {"success": False, "error": "Already enrolled"}
    
    await LMSEnrollment.create(user_id=student_id, course=course)
    
    return {
        "success": True,
        "message": f"Successfully enrolled in {course.title}"
    }
