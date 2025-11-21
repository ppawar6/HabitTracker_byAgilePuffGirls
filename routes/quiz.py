"""
Quiz routes for Habit Personality Assessment
"""

import json
from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from extensions import db
from models import QuizQuestion, PersonalityType, HabitTemplate, UserQuizResult, Habit

quiz_bp = Blueprint('quiz', __name__, url_prefix='/habit-tracker/quiz')


@quiz_bp.route('/start')
def start():
    """Display quiz introduction page"""
    if not session.get('authenticated'):
        return redirect(url_for('signin'))

    total_questions = QuizQuestion.query.count()

    return render_template('apps/habit_tracker/quiz/start.html', total_questions=total_questions)


@quiz_bp.route('/question/<int:question_num>')
def question(question_num):
    """Display a specific quiz question"""
    if not session.get('authenticated'):
        return redirect(url_for('signin'))

    question = QuizQuestion.query.filter_by(question_number=question_num).first()
    total_questions = QuizQuestion.query.count()

    if not question:
        return redirect(url_for('quiz.start'))

    progress = int((question_num / total_questions) * 100)

    return render_template('apps/habit_tracker/quiz/question.html',
                          question=question,
                          progress=progress,
                          current=question_num,
                          total=total_questions)


@quiz_bp.route('/answer', methods=['POST'])
def answer():
    """Process quiz answer and move to next question"""
    if not session.get('authenticated'):
        return redirect(url_for('signin'))

    # Initialize quiz answers in session if not exists
    if 'quiz_answers' not in session:
        session['quiz_answers'] = {}

    # Store answer
    question_id = request.form.get('question_id')
    answer = request.form.get('answer')

    quiz_answers = session['quiz_answers']
    quiz_answers[question_id] = answer
    session['quiz_answers'] = quiz_answers
    session.modified = True

    # Determine next step
    current = int(request.form.get('current'))
    total = int(request.form.get('total'))
    next_question = current + 1

    if next_question > total:
        # Quiz complete, go to results
        return redirect(url_for('quiz.results'))
    else:
        # Next question
        return redirect(url_for('quiz.question', question_num=next_question))


@quiz_bp.route('/results')
def results():
    """Calculate and display quiz results"""
    if not session.get('authenticated'):
        return redirect(url_for('signin'))

    answers = session.get('quiz_answers', {})

    if not answers:
        flash('Please complete the quiz first', 'warning')
        return redirect(url_for('quiz.start'))

    # Calculate personality type
    personality = calculate_personality(answers)

    if not personality:
        flash('Unable to calculate results. Please try again.', 'error')
        return redirect(url_for('quiz.start'))

    # Get habit recommendations
    recommendations = HabitTemplate.query.filter_by(personality_type_id=personality.id).all()

    # Save results to database
    user_id = session.get('user_id', 0)

    # Check if user already has quiz results
    existing_result = UserQuizResult.query.filter_by(user_id=user_id).first()

    if existing_result:
        # Update existing
        existing_result.personality_type_id = personality.id
        existing_result.quiz_answers = json.dumps(answers)
    else:
        # Create new
        result = UserQuizResult(
            user_id=user_id,
            personality_type_id=personality.id,
            quiz_answers=json.dumps(answers)
        )
        db.session.add(result)

    db.session.commit()

    # Parse insights and avoid habits from JSON
    insights = json.loads(personality.insights) if personality.insights else []
    avoid_habits = json.loads(personality.avoid_habits) if personality.avoid_habits else []

    # Clear quiz answers from session
    session.pop('quiz_answers', None)

    return render_template('apps/habit_tracker/quiz/results.html',
                          personality=personality,
                          recommendations=recommendations,
                          insights=insights,
                          avoid_habits=avoid_habits)


@quiz_bp.route('/add-habits', methods=['POST'])
def add_habits():
    """Add selected recommended habits to user's tracker"""
    if not session.get('authenticated'):
        return redirect(url_for('signin'))

    habit_template_ids = request.form.getlist('habit_ids')
    user_id = session.get('user_id', 0)

    if not habit_template_ids:
        flash('Please select at least one habit to add', 'warning')
        return redirect(url_for('quiz.results'))

    added_count = 0

    for template_id in habit_template_ids:
        template = HabitTemplate.query.get(int(template_id))

        if template:
            # Check if habit already exists for this user
            existing = Habit.query.filter_by(
                user_id=user_id,
                name=template.name
            ).first()

            if not existing:
                # Create new habit from template
                new_habit = Habit(
                    user_id=user_id,
                    name=template.name,
                    description=template.description,
                    category=template.category,
                    priority=template.priority
                )
                db.session.add(new_habit)
                added_count += 1

    db.session.commit()

    if added_count > 0:
        flash(f'Successfully added {added_count} habit{"s" if added_count != 1 else ""} to your tracker!', 'success')
    else:
        flash('No new habits added (you may already have these habits)', 'info')

    return redirect(url_for('habit_tracker'))


def calculate_personality(answers):
    """Calculate personality type based on quiz answers"""

    # Simple scoring system
    # A=1, B=2, C=3, D=4
    scores = {
        'energy': 0,
        'motivation': 0,
        'structure': 0,
        'resilience': 0
    }

    category_counts = {
        'energy': 0,
        'motivation': 0,
        'structure': 0,
        'resilience': 0
    }

    # Calculate scores by category
    for question_id, answer in answers.items():
        question = QuizQuestion.query.get(int(question_id))
        if question:
            category = question.scoring_category
            # Convert A, B, C, D to 1, 2, 3, 4
            score = ord(answer.upper()) - ord('A') + 1
            scores[category] += score
            category_counts[category] += 1

    # Calculate average score for energy
    energy_avg = scores['energy'] / category_counts['energy'] if category_counts['energy'] > 0 else 2.5

    # Determine personality type based on scores
    # High morning energy (3.0+) = Morning Warrior
    # Low morning energy (<2.0) = Night Owl
    # Otherwise = Steady Achiever

    if energy_avg >= 3.0:
        personality_name = 'Morning Warrior'
    elif energy_avg <= 2.0:
        personality_name = 'Night Owl'
    else:
        personality_name = 'Steady Achiever'

    personality = PersonalityType.query.filter_by(name=personality_name).first()

    return personality
