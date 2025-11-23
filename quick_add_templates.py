"""
Quick Add Habit Templates
General templates available to all users for quick habit creation
"""

from extensions import db
from models import HabitTemplate

QUICK_ADD_TEMPLATES = [
    # Health Category
    {
        "name": "Drink 8 Glasses of Water",
        "description": "Stay hydrated throughout the day",
        "category": "Health",
        "priority": "Medium",
    },
    {
        "name": "Take Vitamins Daily",
        "description": "Remember to take daily vitamins and supplements",
        "category": "Health",
        "priority": "Medium",
    },
    {
        "name": "Sleep 8 Hours",
        "description": "Get quality sleep every night",
        "category": "Health",
        "priority": "High",
    },
    {
        "name": "No Snacking After 8 PM",
        "description": "Avoid late-night eating for better health",
        "category": "Health",
        "priority": "Medium",
    },
    {
        "name": "Eat 5 Servings of Fruits/Veggies",
        "description": "Consume nutritious fruits and vegetables daily",
        "category": "Health",
        "priority": "High",
    },
    # Fitness Category
    {
        "name": "10 Min Exercise",
        "description": "Quick daily workout routine",
        "category": "Fitness",
        "priority": "High",
    },
    {
        "name": "Morning Yoga",
        "description": "Start your day with stretching and yoga",
        "category": "Fitness",
        "priority": "Medium",
    },
    {
        "name": "10,000 Steps Daily",
        "description": "Walk 10,000 steps each day",
        "category": "Fitness",
        "priority": "Medium",
    },
    {
        "name": "Gym 3x Per Week",
        "description": "Regular gym sessions for fitness",
        "category": "Fitness",
        "priority": "High",
    },
    {
        "name": "Evening Stretching",
        "description": "Gentle stretching routine before bed",
        "category": "Fitness",
        "priority": "Low",
    },
    # Study Category
    {
        "name": "Read 10 Pages",
        "description": "Daily reading habit",
        "category": "Study",
        "priority": "Medium",
    },
    {
        "name": "Study for 1 Hour",
        "description": "Dedicated study time each day",
        "category": "Study",
        "priority": "High",
    },
    {
        "name": "Practice Coding",
        "description": "Work on coding exercises daily",
        "category": "Study",
        "priority": "High",
    },
    {
        "name": "Learn New Vocabulary",
        "description": "Study 10 new words daily",
        "category": "Study",
        "priority": "Medium",
    },
    {
        "name": "Review Notes",
        "description": "Review class or meeting notes",
        "category": "Study",
        "priority": "Medium",
    },
    # Productivity Category
    {
        "name": "Make Tomorrow's To-Do List",
        "description": "Plan ahead for productivity",
        "category": "Productivity",
        "priority": "Medium",
    },
    {
        "name": "Clear Inbox to Zero",
        "description": "Process all emails daily",
        "category": "Productivity",
        "priority": "Low",
    },
    {
        "name": "No Social Media Before Noon",
        "description": "Focus on work in the morning",
        "category": "Productivity",
        "priority": "High",
    },
    {
        "name": "Desk Organization",
        "description": "Keep workspace clean and organized",
        "category": "Productivity",
        "priority": "Low",
    },
    {
        "name": "2-Hour Deep Work Session",
        "description": "Focused work without distractions",
        "category": "Productivity",
        "priority": "High",
    },
    # Mindfulness Category
    {
        "name": "10 Min Meditation",
        "description": "Daily mindfulness practice",
        "category": "Mindfulness",
        "priority": "Medium",
    },
    {
        "name": "Gratitude Journal",
        "description": "Write 3 things you're grateful for",
        "category": "Mindfulness",
        "priority": "Medium",
    },
    {
        "name": "Evening Reflection",
        "description": "Reflect on the day before bed",
        "category": "Mindfulness",
        "priority": "Low",
    },
    {
        "name": "Deep Breathing Exercise",
        "description": "5 minutes of focused breathing",
        "category": "Mindfulness",
        "priority": "Low",
    },
    {
        "name": "Morning Affirmations",
        "description": "Start day with positive affirmations",
        "category": "Mindfulness",
        "priority": "Medium",
    },
    # Finance Category
    {
        "name": "Track Daily Expenses",
        "description": "Record all spending in budget app",
        "category": "Finance",
        "priority": "High",
    },
    {
        "name": "Review Budget Weekly",
        "description": "Check financial goals and spending",
        "category": "Finance",
        "priority": "Medium",
    },
    {
        "name": "Save $10 Daily",
        "description": "Put aside money for savings",
        "category": "Finance",
        "priority": "Medium",
    },
    {
        "name": "No Impulse Purchases",
        "description": "Wait 24 hours before buying",
        "category": "Finance",
        "priority": "Medium",
    },
    # Social Category
    {
        "name": "Call a Friend",
        "description": "Stay connected with loved ones",
        "category": "Social",
        "priority": "Low",
    },
    {
        "name": "Text Family",
        "description": "Check in with family members",
        "category": "Social",
        "priority": "Low",
    },
    {
        "name": "Compliment Someone",
        "description": "Spread kindness daily",
        "category": "Social",
        "priority": "Low",
    },
    {
        "name": "Reach Out to Someone New",
        "description": "Expand your social circle",
        "category": "Social",
        "priority": "Low",
    },
    # Chores Category
    {
        "name": "Make Your Bed",
        "description": "Start the day with a small win",
        "category": "Chores",
        "priority": "Low",
    },
    {
        "name": "Do the Dishes",
        "description": "Keep kitchen clean",
        "category": "Chores",
        "priority": "Medium",
    },
    {
        "name": "Laundry Day",
        "description": "Wash and fold clothes",
        "category": "Chores",
        "priority": "Medium",
    },
    {
        "name": "Weekly Cleaning",
        "description": "Deep clean your living space",
        "category": "Chores",
        "priority": "Medium",
    },
    {
        "name": "10-Min Declutter",
        "description": "Organize one area of your home",
        "category": "Chores",
        "priority": "Low",
    },
]


def populate_quick_add_templates():
    """Populate database with quick-add habit templates"""
    added_count = 0

    for template_data in QUICK_ADD_TEMPLATES:
        # Check if template already exists
        existing = HabitTemplate.query.filter_by(
            name=template_data["name"], personality_type_id=None
        ).first()

        if not existing:
            template = HabitTemplate(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                priority=template_data["priority"],
                personality_type_id=None,  # General template
                reason=None,
            )
            db.session.add(template)
            added_count += 1

    db.session.commit()
    print(f"Quick-add templates populated: {added_count} new templates added")
    return added_count
