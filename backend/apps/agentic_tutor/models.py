from models.base import BaseModel
from tortoise import fields

class Topic(BaseModel):
    name = fields.CharField(max_length=200)
    category = fields.CharField(max_length=100)
    difficulty = fields.CharField(max_length=50)
    description = fields.TextField()
    
    class Meta:
        table = "tutor_topics"

class TutorSession(BaseModel):
    user_id = fields.IntField()
    topic = fields.ForeignKeyField('models.Topic', related_name='sessions')
    status = fields.CharField(max_length=50, default='active')
    current_difficulty = fields.CharField(max_length=50, default='beginner')
    
    class Meta:
        table = "tutor_sessions"

class Assessment(BaseModel):
    session = fields.ForeignKeyField('models.TutorSession', related_name='assessments')
    question = fields.TextField()
    question_type = fields.CharField(max_length=50)
    correct_answer = fields.TextField()
    student_answer = fields.TextField(null=True)
    score = fields.IntField(null=True)
    hints_used = fields.IntField(default=0)
    
    class Meta:
        table = "tutor_assessments"

class Progress(BaseModel):
    user_id = fields.IntField()
    topic = fields.ForeignKeyField('models.Topic', related_name='progress')
    assessments_taken = fields.IntField(default=0)
    average_score = fields.FloatField(default=0)
    total_score = fields.IntField(default=0)
    completed = fields.BooleanField(default=False)
    
    class Meta:
        table = "tutor_progress"

class ChatMessage(BaseModel):
    session = fields.ForeignKeyField('models.TutorSession', related_name='messages')
    role = fields.CharField(max_length=50)
    content = fields.TextField()
    agent_type = fields.CharField(max_length=50, null=True)
    
    class Meta:
        table = "tutor_chat_messages"
