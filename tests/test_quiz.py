"""
Tests for the Habit Personality Quiz feature.

This module tests the quiz functionality including:
- Quiz route access and authentication
- Question navigation
- Answer submission
- Personality calculation
- Habit recommendations
- Results display
"""

import json

import pytest

from extensions import db
from models import Habit, HabitTemplate, PersonalityType, QuizQuestion, UserQuizResult

# === Quiz Data Fixtures ===


@pytest.fixture
def quiz_data(app):
    """Create quiz questions, personality types, and habit templates for testing."""
    with app.app_context():
        # Create personality types
        morning_warrior = PersonalityType(
            name="Morning Warrior",
            emoji="🌅",
            description="You thrive in the early hours",
            peak_time="6-9 AM",
            energy_level="High",
            motivation_style="Goal-driven",
            commitment_level="Dedicated",
            insights=json.dumps(
                ["Front-load difficult habits in the morning", "Avoid evening habits"]
            ),
            avoid_habits=json.dumps(["Evening workouts", "Spontaneous habits"]),
        )

        night_owl = PersonalityType(
            name="Night Owl",
            emoji="🦉",
            description="Your energy peaks in the evening",
            peak_time="8 PM - 12 AM",
            energy_level="High (Evening)",
            motivation_style="Independent",
            commitment_level="Focused",
            insights=json.dumps(
                ["Schedule important habits for evening", "Don't force morning routines"]
            ),
            avoid_habits=json.dumps(["Early morning workouts", "6 AM wake-up goals"]),
        )

        steady_achiever = PersonalityType(
            name="Steady Achiever",
            emoji="📈",
            description="You value consistency over intensity",
            peak_time="Consistent throughout day",
            energy_level="Moderate",
            motivation_style="Process-focused",
            commitment_level="Reliable",
            insights=json.dumps(
                ["Focus on small, sustainable habits", "Consistency is your superpower"]
            ),
            avoid_habits=json.dumps(["Extreme fitness challenges", "Multiple new habits at once"]),
        )

        db.session.add_all([morning_warrior, night_owl, steady_achiever])
        db.session.commit()

        # Create quiz questions
        questions = [
            QuizQuestion(
                question_number=1,
                question_text="What's your current energy level in the morning?",
                option_a="Zombie mode",
                option_b="Groggy but manageable",
                option_c="Awake and ready",
                option_d="Energized and excited",
                scoring_category="energy",
            ),
            QuizQuestion(
                question_number=2,
                question_text="How do you prefer to track your progress?",
                option_a="Visual charts",
                option_b="Written journal",
                option_c="Simple checkboxes",
                option_d="I don't track",
                scoring_category="motivation",
            ),
            QuizQuestion(
                question_number=3,
                question_text="What motivates you most?",
                option_a="Competing with others",
                option_b="Personal growth",
                option_c="Rewards and achievements",
                option_d="Fear of consequences",
                scoring_category="motivation",
            ),
            QuizQuestion(
                question_number=4,
                question_text="How consistent is your energy throughout the day?",
                option_a="Very low all day",
                option_b="Varies significantly",
                option_c="Pretty consistent",
                option_d="Always high",
                scoring_category="energy",
            ),
        ]

        db.session.add_all(questions)
        db.session.commit()

        # Create habit templates
        templates = [
            HabitTemplate(
                name="Wake at 6 AM",
                description="Start your day early",
                category="Health",
                priority="High",
                personality_type_id=morning_warrior.id,
                reason="Matches your peak energy time",
            ),
            HabitTemplate(
                name="15-min Morning Workout",
                description="Quick exercise routine",
                category="Fitness",
                priority="High",
                personality_type_id=morning_warrior.id,
                reason="High energy baseline supports morning exercise",
            ),
            HabitTemplate(
                name="Evening Journaling",
                description="Reflect on your day",
                category="Personal Growth",
                priority="Medium",
                personality_type_id=night_owl.id,
                reason="Evening focus perfect for reflection",
            ),
        ]

        db.session.add_all(templates)
        db.session.commit()

        return {
            "morning_warrior": morning_warrior,
            "night_owl": night_owl,
            "steady_achiever": steady_achiever,
            "questions": questions,
            "templates": templates,
        }


# === Quiz Route Tests ===


def test_quiz_start_requires_auth(client, quiz_data):
    """Test that /quiz/start requires authentication."""
    response = client.get("/habit-tracker/quiz/start")
    assert response.status_code == 302  # Redirect to signin
    assert "/signin" in response.location


def test_quiz_start_authenticated(logged_in_client, quiz_data):
    """Test that authenticated users can access quiz start page."""
    response = logged_in_client.get("/habit-tracker/quiz/start")
    assert response.status_code == 200
    assert b"Discover Your Habit Personality" in response.data


def test_quiz_start_shows_question_count(logged_in_client, quiz_data):
    """Test that quiz start page shows total question count."""
    response = logged_in_client.get("/habit-tracker/quiz/start")
    assert response.status_code == 200
    # Should show "4 simple questions" since we have 4 questions
    assert b"4" in response.data


def test_quiz_question_requires_auth(client, quiz_data):
    """Test that /quiz/question requires authentication."""
    response = client.get("/habit-tracker/quiz/question/1")
    assert response.status_code == 302  # Redirect to signin


def test_quiz_question_authenticated(logged_in_client, quiz_data):
    """Test that authenticated users can access quiz questions."""
    response = logged_in_client.get("/habit-tracker/quiz/question/1")
    assert response.status_code == 200
    assert b"energy level" in response.data


def test_quiz_question_shows_options(logged_in_client, quiz_data):
    """Test that question page displays all answer options."""
    response = logged_in_client.get("/habit-tracker/quiz/question/1")
    assert response.status_code == 200
    assert b"Zombie mode" in response.data
    assert b"Groggy but manageable" in response.data
    assert b"Awake and ready" in response.data
    assert b"Energized and excited" in response.data


def test_quiz_question_invalid_redirects(logged_in_client, quiz_data):
    """Test that invalid question numbers redirect to start."""
    response = logged_in_client.get("/habit-tracker/quiz/question/999")
    assert response.status_code == 302
    assert "/quiz/start" in response.location


def test_quiz_answer_requires_auth(client, quiz_data):
    """Test that /quiz/answer requires authentication."""
    response = client.post("/habit-tracker/quiz/answer")
    assert response.status_code == 302  # Redirect to signin


def test_quiz_answer_submission(logged_in_client, quiz_data, app):
    """Test submitting an answer to a quiz question."""
    with app.app_context():
        question = QuizQuestion.query.filter_by(question_number=1).first()
        question_id = question.id

    response = logged_in_client.post(
        "/habit-tracker/quiz/answer",
        data={"question_id": str(question_id), "answer": "D", "current": "1", "total": "4"},
    )

    assert response.status_code == 302  # Redirect to next question
    assert "/quiz/question/2" in response.location


def test_quiz_answer_stored_in_session(logged_in_client, quiz_data, app):
    """Test that quiz answers are stored in session."""
    with app.app_context():
        question = QuizQuestion.query.filter_by(question_number=1).first()
        question_id = question.id

    with logged_in_client.session_transaction() as sess:
        sess["quiz_answers"] = {}

    logged_in_client.post(
        "/habit-tracker/quiz/answer",
        data={"question_id": str(question_id), "answer": "D", "current": "1", "total": "4"},
    )

    with logged_in_client.session_transaction() as sess:
        assert "quiz_answers" in sess
        assert str(question_id) in sess["quiz_answers"]
        assert sess["quiz_answers"][str(question_id)] == "D"


def test_quiz_last_answer_redirects_to_results(logged_in_client, quiz_data, app):
    """Test that answering the last question redirects to results."""
    with app.app_context():
        question = QuizQuestion.query.filter_by(question_number=1).first()
        question_id = question.id

    response = logged_in_client.post(
        "/habit-tracker/quiz/answer",
        data={"question_id": str(question_id), "answer": "D", "current": "4", "total": "4"},
    )

    assert response.status_code == 302
    assert "/quiz/results" in response.location


# === Personality Calculation Tests ===


def test_morning_warrior_calculation(logged_in_client, quiz_data, app):
    """Test that high energy answers result in Morning Warrior personality."""
    with app.app_context():
        questions = QuizQuestion.query.order_by(QuizQuestion.question_number).all()

        # Answer all energy questions with high scores (D = 4)
        with logged_in_client.session_transaction() as sess:
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Morning Warrior" in response.data
        assert b"\xf0\x9f\x8c\x85" in response.data  # 🌅 emoji


def test_night_owl_calculation(logged_in_client, quiz_data, app):
    """Test that low energy answers result in Night Owl personality."""
    with app.app_context():
        questions = QuizQuestion.query.order_by(QuizQuestion.question_number).all()

        # Answer all energy questions with low scores (A = 1)
        with logged_in_client.session_transaction() as sess:
            sess["quiz_answers"] = {str(q.id): "A" for q in questions}

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Night Owl" in response.data


def test_steady_achiever_calculation(logged_in_client, quiz_data, app):
    """Test that moderate energy answers result in Steady Achiever personality."""
    with app.app_context():
        questions = QuizQuestion.query.order_by(QuizQuestion.question_number).all()

        # Need energy_avg between 2.0 and 3.0
        # Question 1 (energy): B = 2
        # Question 2 (motivation): doesn't matter
        # Question 3 (motivation): doesn't matter
        # Question 4 (energy): C = 3
        # energy_avg = (2 + 3) / 2 = 2.5 (should be Steady Achiever)
        with logged_in_client.session_transaction() as sess:
            answers = {}
            for q in questions:
                if q.question_number == 1:
                    answers[str(q.id)] = "B"  # energy question: score 2
                elif q.question_number == 4:
                    answers[str(q.id)] = "C"  # energy question: score 3
                else:
                    answers[str(q.id)] = "B"  # motivation questions: don't matter
            sess["quiz_answers"] = answers

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Steady Achiever" in response.data


def test_results_requires_auth(client, quiz_data):
    """Test that /quiz/results requires authentication."""
    response = client.get("/habit-tracker/quiz/results")
    assert response.status_code == 302


def test_results_without_answers_redirects(logged_in_client, quiz_data):
    """Test that accessing results without answers redirects to start."""
    response = logged_in_client.get("/habit-tracker/quiz/results")
    assert response.status_code == 302
    assert "/quiz/start" in response.location


def test_results_saves_to_database(logged_in_client, quiz_data, app):
    """Test that quiz results are saved to the database."""
    with app.app_context():
        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        logged_in_client.get("/habit-tracker/quiz/results")

        result = UserQuizResult.query.filter_by(user_id=1).first()
        assert result is not None
        assert result.personality_type_id is not None


def test_results_updates_existing_result(logged_in_client, quiz_data, app):
    """Test that retaking quiz updates existing result."""
    with app.app_context():
        # Get personality type ID
        steady_achiever = PersonalityType.query.filter_by(name="Steady Achiever").first()

        # Create initial result
        initial_result = UserQuizResult(
            user_id=1, personality_type_id=steady_achiever.id, quiz_answers="{}"
        )
        db.session.add(initial_result)
        db.session.commit()
        initial_id = initial_result.id

        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        logged_in_client.get("/habit-tracker/quiz/results")

        # Check that result was updated, not created
        results = UserQuizResult.query.filter_by(user_id=1).all()
        assert len(results) == 1
        assert results[0].id == initial_id


def test_results_shows_recommendations(logged_in_client, quiz_data, app):
    """Test that results page shows habit recommendations."""
    with app.app_context():
        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Wake at 6 AM" in response.data
        assert b"15-min Morning Workout" in response.data


def test_results_shows_insights(logged_in_client, quiz_data, app):
    """Test that results page shows personalized insights."""
    with app.app_context():
        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Front-load difficult habits in the morning" in response.data


def test_results_shows_avoid_habits(logged_in_client, quiz_data, app):
    """Test that results page shows habits to avoid."""
    with app.app_context():
        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        response = logged_in_client.get("/habit-tracker/quiz/results")
        assert response.status_code == 200
        assert b"Evening workouts" in response.data


def test_results_clears_session_answers(logged_in_client, quiz_data, app):
    """Test that viewing results clears quiz answers from session."""
    with app.app_context():
        questions = QuizQuestion.query.all()

        with logged_in_client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["quiz_answers"] = {str(q.id): "D" for q in questions}

        logged_in_client.get("/habit-tracker/quiz/results")

        with logged_in_client.session_transaction() as sess:
            assert "quiz_answers" not in sess


# === Habit Import Tests ===


def test_add_habits_requires_auth(client, quiz_data):
    """Test that /quiz/add-habits requires authentication."""
    response = client.post("/habit-tracker/quiz/add-habits")
    assert response.status_code == 302


def test_add_habits_creates_habits(logged_in_client, quiz_data, app):
    """Test that add-habits creates habits from templates."""
    with app.app_context():
        template = HabitTemplate.query.filter_by(name="Wake at 6 AM").first()
        template_id = template.id
        template_name = template.name
        template_desc = template.description
        template_cat = template.category
        template_prio = template.priority

    with logged_in_client.session_transaction() as sess:
        sess["user_id"] = 1

    response = logged_in_client.post(
        "/habit-tracker/quiz/add-habits", data={"habit_ids": [str(template_id)]}
    )

    assert response.status_code == 302
    assert "/habit-tracker" in response.location

    with app.app_context():
        habit = Habit.query.filter_by(user_id=1, name=template_name).first()
        assert habit is not None
        assert habit.description == template_desc
        assert habit.category == template_cat
        assert habit.priority == template_prio


def test_add_habits_multiple(logged_in_client, quiz_data, app):
    """Test adding multiple habits at once."""
    with app.app_context():
        templates = HabitTemplate.query.limit(2).all()
        template_ids = [str(t.id) for t in templates]

    with logged_in_client.session_transaction() as sess:
        sess["user_id"] = 1

    logged_in_client.post("/habit-tracker/quiz/add-habits", data={"habit_ids": template_ids})

    with app.app_context():
        habits = Habit.query.filter_by(user_id=1).all()
        assert len(habits) == 2


def test_add_habits_prevents_duplicates(logged_in_client, quiz_data, app):
    """Test that adding existing habit doesn't create duplicates."""
    with app.app_context():
        template = HabitTemplate.query.filter_by(name="Wake at 6 AM").first()
        template_id = template.id
        template_name = template.name

        # Create existing habit
        existing_habit = Habit(
            user_id=1,
            name=template_name,
            description="Existing",
            category="Health",
            priority="High",
        )
        db.session.add(existing_habit)
        db.session.commit()

    with logged_in_client.session_transaction() as sess:
        sess["user_id"] = 1

    logged_in_client.post("/habit-tracker/quiz/add-habits", data={"habit_ids": [str(template_id)]})

    with app.app_context():
        # Should still be only 1 habit
        habits = Habit.query.filter_by(user_id=1, name=template_name).all()
        assert len(habits) == 1


def test_add_habits_no_selection_shows_warning(logged_in_client, quiz_data):
    """Test that submitting without selecting habits shows warning."""
    with logged_in_client.session_transaction() as sess:
        sess["user_id"] = 1

    response = logged_in_client.post("/habit-tracker/quiz/add-habits", data={})

    assert response.status_code == 302
    assert "/quiz/results" in response.location


# === Progress Bar Tests ===


def test_progress_bar_calculation(logged_in_client, quiz_data):
    """Test that progress bar shows correct percentage."""
    response = logged_in_client.get("/habit-tracker/quiz/question/1")
    assert response.status_code == 200
    assert b"25%" in response.data  # 1/4 = 25%

    response = logged_in_client.get("/habit-tracker/quiz/question/2")
    assert response.status_code == 200
    assert b"50%" in response.data  # 2/4 = 50%


def test_question_navigation_back_button(logged_in_client, quiz_data):
    """Test that back button appears on question 2+."""
    response = logged_in_client.get("/habit-tracker/quiz/question/1")
    assert b"Back" not in response.data  # No back button on first question

    response = logged_in_client.get("/habit-tracker/quiz/question/2")
    assert b"Back" in response.data


def test_question_navigation_next_button(logged_in_client, quiz_data):
    """Test that next button changes to 'See Results' on last question."""
    response = logged_in_client.get("/habit-tracker/quiz/question/2")
    assert b"Next" in response.data

    response = logged_in_client.get("/habit-tracker/quiz/question/4")
    assert b"See Results" in response.data
