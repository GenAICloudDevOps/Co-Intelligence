from apps.agentic_tutor.models import Topic

async def seed_topics():
    """Seed initial topics"""
    from tortoise import Tortoise
    
    # Ensure connection is initialized
    if not Tortoise._inited:
        return
    
    topics = [
        # Python Programming
        {"name": "Python Basics", "category": "Python Programming", "difficulty": "beginner", 
         "description": "Variables, data types, operators, and basic syntax"},
        {"name": "Data Structures", "category": "Python Programming", "difficulty": "intermediate",
         "description": "Lists, dictionaries, sets, and tuples"},
        {"name": "Object-Oriented Programming", "category": "Python Programming", "difficulty": "intermediate",
         "description": "Classes, objects, inheritance, and polymorphism"},
        {"name": "File Handling", "category": "Python Programming", "difficulty": "beginner",
         "description": "Reading and writing files, working with CSV and JSON"},
        
        # Artificial Intelligence
        {"name": "AI Fundamentals", "category": "Artificial Intelligence", "difficulty": "beginner",
         "description": "Introduction to AI, machine learning, and neural networks"},
        {"name": "Machine Learning Basics", "category": "Artificial Intelligence", "difficulty": "intermediate",
         "description": "Supervised learning, regression, and classification"},
        {"name": "Neural Networks", "category": "Artificial Intelligence", "difficulty": "advanced",
         "description": "Deep learning, backpropagation, and optimization"},
        {"name": "Natural Language Processing", "category": "Artificial Intelligence", "difficulty": "intermediate",
         "description": "Text processing, sentiment analysis, and language models"},
        
        # Data Science
        {"name": "Pandas & NumPy", "category": "Data Science", "difficulty": "beginner",
         "description": "Data manipulation and numerical computing"},
        {"name": "Data Visualization", "category": "Data Science", "difficulty": "beginner",
         "description": "Creating charts and graphs with Matplotlib and Seaborn"},
        {"name": "Statistics Basics", "category": "Data Science", "difficulty": "intermediate",
         "description": "Probability, distributions, and hypothesis testing"},
        
        # Web Development
        {"name": "FastAPI Basics", "category": "Web Development", "difficulty": "beginner",
         "description": "Building REST APIs with FastAPI"},
        {"name": "Database Design", "category": "Web Development", "difficulty": "intermediate",
         "description": "SQL, ORMs, and database optimization"},
        
        # Algorithms
        {"name": "Sorting & Searching", "category": "Algorithms", "difficulty": "beginner",
         "description": "Common sorting and searching algorithms"},
        {"name": "Recursion", "category": "Algorithms", "difficulty": "intermediate",
         "description": "Recursive problem solving and backtracking"},
    ]
    
    for topic_data in topics:
        existing = await Topic.get_or_none(name=topic_data['name'])
        if not existing:
            await Topic.create(**topic_data)
            print(f"✓ Created topic: {topic_data['name']}")
    
    print(f"✅ Seeded {len(topics)} topics")
