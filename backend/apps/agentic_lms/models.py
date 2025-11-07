from tortoise import fields, models
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class LMSCourse(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    description = fields.TextField()
    category = fields.CharField(max_length=100)
    difficulty = fields.CharField(max_length=50)
    duration_hours = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    
    enrollments: fields.ReverseRelation["LMSEnrollment"]

    class Meta:
        table = "lms_courses"


class LMSEnrollment(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()  # Reference to User.id from auth
    course = fields.ForeignKeyField("models.LMSCourse", related_name="enrollments")
    enrolled_at = fields.DatetimeField(auto_now_add=True)
    progress = fields.IntField(default=0)
    completed = fields.BooleanField(default=False)

    class Meta:
        table = "lms_enrollments"
        unique_together = (("user_id", "course"),)


class LMSChatHistory(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()  # Reference to User.id from auth
    message = fields.TextField()
    response = fields.TextField()
    model_used = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "lms_chat_history"


# Pydantic models
class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    description: str
    category: str
    difficulty: str
    duration_hours: int
    created_at: datetime


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    progress: int
    completed: bool


class ChatRequest(BaseModel):
    message: str
    model: str = "gemini-2.5-flash-lite"


class ChatResponse(BaseModel):
    response: str
    model_used: str
