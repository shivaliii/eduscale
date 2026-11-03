"""Quiz service — quiz management, attempt handling, answer evaluation, mastery updates."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import (
    Student, Quiz, QuizQuestion, Question, QuizAttempt,
    StudentResponse, Mastery, Topic,
)
from app.schemas import (
    QuizOut, QuestionOut, ResponseSubmit, AttemptResult, ResponseResult,
)


def get_quizzes_for_student(db: Session, student_id: uuid.UUID, course_id: Optional[uuid.UUID] = None, topic_id: Optional[uuid.UUID] = None) -> list[dict]:
    """Get available quizzes, optionally filtered."""
    query = db.query(Quiz)
    if course_id:
        query = query.filter(Quiz.course_id == course_id)
    if topic_id:
        query = query.filter(Quiz.topic_id == topic_id)
    quizzes = query.all()
    return [
        {
            "id": str(q.id), "title": q.title, "description": q.description,
            "course_id": str(q.course_id),
            "topic_id": str(q.topic_id) if q.topic_id else None,
            "difficulty": q.difficulty, "question_count": q.question_count,
            "time_limit_minutes": q.time_limit_minutes, "is_practice": q.is_practice,
        }
        for q in quizzes
    ]


def start_attempt(db: Session, student: Student, quiz_id: uuid.UUID) -> dict:
    """Start a new quiz attempt and return questions."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return None

    # Get quiz questions
    qq_items = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id
    ).order_by(QuizQuestion.order_index).all()

    questions = []
    for qq in qq_items:
        q = db.query(Question).filter(Question.id == qq.question_id).first()
        if q:
            questions.append({
                "id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type.value if hasattr(q.question_type, 'value') else q.question_type,
                "difficulty": q.difficulty.value if hasattr(q.difficulty, 'value') else q.difficulty,
                "code_snippet": q.code_snippet,
                "options": q.options,
            })

    # Create attempt
    attempt = QuizAttempt(
        student_id=student.id,
        quiz_id=quiz_id,
        total_questions=len(questions),
        status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": str(attempt.id),
        "quiz": {
            "id": str(quiz.id), "title": quiz.title,
            "time_limit_minutes": quiz.time_limit_minutes,
        },
        "questions": questions,
    }


def submit_response(db: Session, attempt_id: uuid.UUID, data: ResponseSubmit) -> dict:
    """Submit a single question response."""
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt or attempt.status != "in_progress":
        return None

    question = db.query(Question).filter(Question.id == data.question_id).first()
    if not question:
        return None

    is_correct = data.submitted_answer.strip().upper() == question.correct_answer.strip().upper()

    response = StudentResponse(
        attempt_id=attempt_id,
        question_id=data.question_id,
        submitted_answer=data.submitted_answer,
        is_correct=is_correct,
        time_spent_seconds=data.time_spent_seconds,
    )
    db.add(response)
    db.commit()

    return {"is_correct": is_correct, "question_id": str(data.question_id)}


def submit_attempt(db: Session, student: Student, attempt_id: uuid.UUID) -> dict:
    """Complete a quiz attempt, calculate score, update mastery."""
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == attempt_id,
        QuizAttempt.student_id == student.id
    ).first()
    if not attempt:
        return None

    responses = db.query(StudentResponse).filter(
        StudentResponse.attempt_id == attempt_id
    ).all()

    correct = sum(1 for r in responses if r.is_correct)
    total = len(responses)
    score = (correct / total * 100) if total > 0 else 0

    attempt.correct_answers = correct
    attempt.total_questions = total
    attempt.score = score
    attempt.status = "completed"
    attempt.completed_at = datetime.utcnow()
    db.commit()

    # Update topic mastery
    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    if quiz and quiz.topic_id:
        _update_mastery(db, student.id, quiz.topic_id)

    # Build result
    result_responses = []
    for r in responses:
        q = db.query(Question).filter(Question.id == r.question_id).first()
        result_responses.append(ResponseResult(
            question_id=r.question_id,
            question_text=q.question_text if q else "",
            submitted_answer=r.submitted_answer or "",
            correct_answer=q.correct_answer if q else "",
            is_correct=r.is_correct,
            explanation=q.explanation if q else None,
        ))

    recommendations = []
    if score < 60:
        recommendations.append("Review the important notes for this topic")
        recommendations.append("Try another practice test at an easier difficulty")
    elif score < 80:
        recommendations.append("Good effort! Review your incorrect answers")
        recommendations.append("Try practice questions on the topics you missed")
    else:
        recommendations.append("Excellent work! Try a harder difficulty level")

    return AttemptResult(
        attempt_id=attempt_id,
        quiz_title=quiz.title if quiz else "Quiz",
        score=round(score, 1),
        total_questions=total,
        correct_answers=correct,
        responses=result_responses,
        recommendations=recommendations,
    ).model_dump()


def _update_mastery(db: Session, student_id: uuid.UUID, topic_id: uuid.UUID):
    """Update topic mastery based on all responses for this topic."""
    # Get all responses for this topic
    topic_questions = db.query(Question).filter(Question.topic_id == topic_id).all()
    q_ids = [q.id for q in topic_questions]

    if not q_ids:
        return

    responses = db.query(StudentResponse).join(QuizAttempt).filter(
        QuizAttempt.student_id == student_id,
        StudentResponse.question_id.in_(q_ids),
    ).all()

    total = len(responses)
    correct = sum(1 for r in responses if r.is_correct)
    mastery_score = correct / total if total > 0 else 0

    # Upsert mastery
    mastery = db.query(Mastery).filter(
        Mastery.student_id == student_id,
        Mastery.topic_id == topic_id
    ).first()

    if mastery:
        mastery.mastery_score = mastery_score
        mastery.questions_attempted = total
        mastery.questions_correct = correct
        mastery.source = "heuristic"
        mastery.updated_at = datetime.utcnow()
    else:
        mastery = Mastery(
            student_id=student_id,
            topic_id=topic_id,
            mastery_score=mastery_score,
            questions_attempted=total,
            questions_correct=correct,
            source="heuristic",
        )
        db.add(mastery)
    db.commit()


def get_attempt_result(db: Session, student: Student, attempt_id: uuid.UUID) -> dict:
    """Get results for a completed attempt."""
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == attempt_id,
        QuizAttempt.student_id == student.id,
        QuizAttempt.status == "completed"
    ).first()
    if not attempt:
        return None

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    responses = db.query(StudentResponse).filter(
        StudentResponse.attempt_id == attempt_id
    ).all()

    result_responses = []
    for r in responses:
        q = db.query(Question).filter(Question.id == r.question_id).first()
        result_responses.append({
            "question_id": str(r.question_id),
            "question_text": q.question_text if q else "",
            "submitted_answer": r.submitted_answer or "",
            "correct_answer": q.correct_answer if q else "",
            "is_correct": r.is_correct,
            "explanation": q.explanation if q else None,
        })

    return {
        "attempt_id": str(attempt.id),
        "quiz_title": quiz.title if quiz else "Quiz",
        "score": round(attempt.score, 1) if attempt.score else 0,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "started_at": attempt.started_at.isoformat(),
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        "responses": result_responses,
    }


def generate_practice_test(
    db: Session, student: Student,
    topic_id: uuid.UUID, difficulty: str = "beginner",
    question_count: int = 5
) -> dict:
    """Generate a practice test from the question bank."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        return None

    # Get questions, preferring ones the student hasn't seen
    answered_q_ids = db.query(StudentResponse.question_id).join(QuizAttempt).filter(
        QuizAttempt.student_id == student.id
    ).distinct().all()
    answered_ids = [r[0] for r in answered_q_ids]

    # First try unanswered questions
    questions = db.query(Question).filter(
        Question.topic_id == topic_id,
        Question.difficulty == difficulty,
        ~Question.id.in_(answered_ids) if answered_ids else True,
    ).limit(question_count).all()

    # If not enough, include previously answered
    if len(questions) < question_count:
        remaining = question_count - len(questions)
        existing_ids = [q.id for q in questions]
        more = db.query(Question).filter(
            Question.topic_id == topic_id,
            Question.difficulty == difficulty,
            ~Question.id.in_(existing_ids) if existing_ids else True,
        ).limit(remaining).all()
        questions.extend(more)

    if not questions:
        return None

    # Create a practice quiz
    quiz = Quiz(
        course_id=topic.course_id,
        topic_id=topic_id,
        title=f"Practice: {topic.name} ({difficulty.capitalize()})",
        difficulty=difficulty,
        question_count=len(questions),
        is_practice=True,
    )
    db.add(quiz)
    db.flush()

    for i, q in enumerate(questions):
        qq = QuizQuestion(quiz_id=quiz.id, question_id=q.id, order_index=i)
        db.add(qq)

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": str(quiz.id),
        "title": quiz.title,
        "topic": topic.name,
        "difficulty": difficulty,
        "question_count": len(questions),
    }
