from .models import LMSCourse


INITIAL_COURSES = [
    {
        "title": "Introduction to Artificial Intelligence",
        "description": "Learn the fundamentals of AI, machine learning, and neural networks. Perfect for beginners.",
        "category": "AI",
        "difficulty": "Beginner",
        "duration_hours": 40
    },
    {
        "title": "Advanced Machine Learning with Python",
        "description": "Deep dive into ML algorithms, model optimization, and real-world applications.",
        "category": "AI",
        "difficulty": "Advanced",
        "duration_hours": 60
    },
    {
        "title": "DevOps Fundamentals",
        "description": "Master CI/CD pipelines, automation, and DevOps best practices.",
        "category": "DevOps",
        "difficulty": "Intermediate",
        "duration_hours": 35
    },
    {
        "title": "Docker Mastery: From Beginner to Pro",
        "description": "Complete guide to containerization with Docker, including multi-stage builds and optimization.",
        "category": "Docker",
        "difficulty": "Beginner",
        "duration_hours": 25
    },
    {
        "title": "Kubernetes for Developers",
        "description": "Deploy and manage containerized applications with Kubernetes orchestration.",
        "category": "Kubernetes",
        "difficulty": "Intermediate",
        "duration_hours": 45
    },
    {
        "title": "Advanced Kubernetes: Production Patterns",
        "description": "Learn advanced K8s concepts including operators, service mesh, and security.",
        "category": "Kubernetes",
        "difficulty": "Advanced",
        "duration_hours": 50
    },
    {
        "title": "Deep Learning and Neural Networks",
        "description": "Build and train deep learning models using TensorFlow and PyTorch.",
        "category": "AI",
        "difficulty": "Advanced",
        "duration_hours": 70
    },
    {
        "title": "Infrastructure as Code with Terraform",
        "description": "Automate infrastructure deployment across cloud providers using Terraform.",
        "category": "DevOps",
        "difficulty": "Intermediate",
        "duration_hours": 30
    },
    {
        "title": "Docker Compose and Multi-Container Apps",
        "description": "Orchestrate multi-container applications with Docker Compose.",
        "category": "Docker",
        "difficulty": "Intermediate",
        "duration_hours": 20
    },
    {
        "title": "Natural Language Processing with Transformers",
        "description": "Master NLP techniques using modern transformer architectures like BERT and GPT.",
        "category": "AI",
        "difficulty": "Advanced",
        "duration_hours": 55
    }
]


async def init_lms_db():
    """Initialize database with sample courses"""
    course_count = await LMSCourse.all().count()
    
    if course_count == 0:
        for course_data in INITIAL_COURSES:
            await LMSCourse.create(**course_data)
        print(f"✓ Initialized LMS with {len(INITIAL_COURSES)} courses")
