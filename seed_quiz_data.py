"""
Seed data for Habit Personality Quiz
Run this script to populate quiz questions, personality types, and habit templates
"""

import json

from app import app
from extensions import db
from models import HabitTemplate, PersonalityType, QuizQuestion


def seed_quiz_questions():
    """Create quiz questions"""
    questions = [
        {
            'question_number': 1,
            'question_text': "What's your current energy level in the morning?",
            'option_a': "Zombie mode (need 3 alarms)",
            'option_b': "Groggy but manageable",
            'option_c': "Awake and ready",
            'option_d': "Energized and excited",
            'scoring_category': 'energy'
        },
        {
            'question_number': 2,
            'question_text': "How do you prefer to track your progress?",
            'option_a': "Visual charts and graphs",
            'option_b': "Written journal entries",
            'option_c': "Simple checkboxes",
            'option_d': "I don't track, I just do",
            'scoring_category': 'motivation'
        },
        {
            'question_number': 3,
            'question_text': "What motivates you most?",
            'option_a': "Competing with others",
            'option_b': "Personal growth",
            'option_c': "Rewards and achievements",
            'option_d': "Fear of consequences",
            'scoring_category': 'motivation'
        },
        {
            'question_number': 4,
            'question_text': "How much structure do you need in your daily routine?",
            'option_a': "Very rigid schedule",
            'option_b': "Moderate structure",
            'option_c': "Loose routine with flexibility",
            'option_d': "No schedule, spontaneous",
            'scoring_category': 'structure'
        },
        {
            'question_number': 5,
            'question_text': "How do you handle setbacks or missed habits?",
            'option_a': "Analyze what went wrong",
            'option_b': "Double down with determination",
            'option_c': "Move on quickly without dwelling",
            'option_d': "Feel discouraged for a while",
            'scoring_category': 'resilience'
        }
    ]

    for q_data in questions:
        existing = QuizQuestion.query.filter_by(question_number=q_data['question_number']).first()
        if not existing:
            question = QuizQuestion(**q_data)
            db.session.add(question)

    db.session.commit()
    print("Quiz questions seeded successfully!")


def seed_personality_types():
    """Create personality types"""
    personalities = [
        {
            'name': 'Morning Warrior',
            'emoji': '🌅',
            'description': 'You thrive in the early hours with high energy and focus. Your peak productivity happens before most people wake up.',
            'peak_time': '6-9 AM',
            'energy_level': 'High',
            'motivation_style': 'Goal-driven',
            'commitment_level': 'Dedicated',
            'insights': json.dumps([
                "Front-load difficult habits in the morning when your willpower is highest",
                "Avoid evening habits - your energy depletes as the day goes on",
                "Set SMART goals with measurable outcomes for best results",
                "You succeed with structured routines and clear schedules"
            ]),
            'avoid_habits': json.dumps([
                "Evening workouts (low energy time)",
                "Spontaneous habits without structure",
                "Long meditation sessions (prefer action-oriented habits)"
            ])
        },
        {
            'name': 'Night Owl',
            'emoji': '🦉',
            'description': 'Your energy peaks in the evening. You work best when the world is quiet and distractions fade away.',
            'peak_time': '8 PM - 12 AM',
            'energy_level': 'High (Evening)',
            'motivation_style': 'Independent',
            'commitment_level': 'Focused',
            'insights': json.dumps([
                "Schedule important habits for evening hours",
                "Don't force morning routines - work with your natural rhythm",
                "Use late-night focus for creative and challenging tasks",
                "Build momentum with evening wins"
            ]),
            'avoid_habits': json.dumps([
                "Early morning workouts",
                "6 AM wake-up goals",
                "Morning meditation (try evening instead)"
            ])
        },
        {
            'name': 'Steady Achiever',
            'emoji': '📈',
            'description': 'You value consistency over intensity. Slow and steady wins your race, building habits through reliable routines.',
            'peak_time': 'Consistent throughout day',
            'energy_level': 'Moderate',
            'motivation_style': 'Process-focused',
            'commitment_level': 'Reliable',
            'insights': json.dumps([
                "Focus on small, sustainable habits rather than big dramatic changes",
                "Consistency is your superpower - use it!",
                "Track progress with simple methods",
                "Build one habit at a time for best results"
            ]),
            'avoid_habits': json.dumps([
                "Extreme fitness challenges",
                "Multiple new habits at once",
                "All-or-nothing approaches"
            ])
        }
    ]

    for p_data in personalities:
        existing = PersonalityType.query.filter_by(name=p_data['name']).first()
        if not existing:
            personality = PersonalityType(**p_data)
            db.session.add(personality)
        else:
            # Update existing
            for key, value in p_data.items():
                setattr(existing, key, value)

    db.session.commit()
    print("Personality types seeded successfully!")


def seed_habit_templates():
    """Create habit templates for each personality type"""

    # Get personality types
    morning_warrior = PersonalityType.query.filter_by(name='Morning Warrior').first()
    night_owl = PersonalityType.query.filter_by(name='Night Owl').first()
    steady_achiever = PersonalityType.query.filter_by(name='Steady Achiever').first()

    templates = [
        # Morning Warrior habits
        {
            'name': 'Wake at 6 AM',
            'description': 'Start your day early to maximize morning energy',
            'category': 'Health',
            'priority': 'High',
            'personality_type_id': morning_warrior.id,
            'reason': 'Matches your peak energy time'
        },
        {
            'name': '15-min Morning Workout',
            'description': 'Quick exercise routine to energize your day',
            'category': 'Fitness',
            'priority': 'High',
            'personality_type_id': morning_warrior.id,
            'reason': 'High energy baseline supports morning exercise'
        },
        {
            'name': 'Goal Planning Session',
            'description': 'Review and plan daily goals each morning',
            'category': 'Productivity',
            'priority': 'Medium',
            'personality_type_id': morning_warrior.id,
            'reason': 'Goal-driven style thrives on planning'
        },

        # Night Owl habits
        {
            'name': 'Evening Journaling',
            'description': 'Reflect on your day before bed',
            'category': 'Personal Growth',
            'priority': 'Medium',
            'personality_type_id': night_owl.id,
            'reason': 'Evening focus perfect for reflection'
        },
        {
            'name': 'Night Reading 30 mins',
            'description': 'Read before bed to wind down',
            'category': 'Learning',
            'priority': 'Medium',
            'personality_type_id': night_owl.id,
            'reason': 'Peak concentration in evening hours'
        },
        {
            'name': 'Evening Stretching',
            'description': 'Gentle stretching routine before sleep',
            'category': 'Health',
            'priority': 'Low',
            'personality_type_id': night_owl.id,
            'reason': 'Works with your natural evening rhythm'
        },

        # Steady Achiever habits
        {
            'name': 'Drink 8 Glasses of Water',
            'description': 'Stay hydrated throughout the day',
            'category': 'Health',
            'priority': 'Medium',
            'personality_type_id': steady_achiever.id,
            'reason': 'Simple, consistent habit perfect for your style'
        },
        {
            'name': 'Daily 10-Minute Walk',
            'description': 'Take a short walk every day',
            'category': 'Fitness',
            'priority': 'Medium',
            'personality_type_id': steady_achiever.id,
            'reason': 'Small, sustainable daily habit'
        },
        {
            'name': 'Read 10 Pages',
            'description': 'Read at least 10 pages each day',
            'category': 'Learning',
            'priority': 'Medium',
            'personality_type_id': steady_achiever.id,
            'reason': 'Achievable daily goal with steady progress'
        }
    ]

    for t_data in templates:
        existing = HabitTemplate.query.filter_by(
            name=t_data['name'],
            personality_type_id=t_data['personality_type_id']
        ).first()
        if not existing:
            template = HabitTemplate(**t_data)
            db.session.add(template)

    db.session.commit()
    print("Habit templates seeded successfully!")


if __name__ == '__main__':
    with app.app_context():
        print("Starting database seeding...")

        # Create tables if they don't exist
        db.create_all()

        # Seed data
        seed_quiz_questions()
        seed_personality_types()
        seed_habit_templates()

        print("\nDatabase seeding complete!")
        print(f"   - {QuizQuestion.query.count()} quiz questions")
        print(f"   - {PersonalityType.query.count()} personality types")
        print(f"   - {HabitTemplate.query.count()} habit templates")
