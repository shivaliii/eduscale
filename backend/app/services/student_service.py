"""Student service — dashboard data, performance, mastery, recommendations."""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    Student, User, Enrollment, Class, Course, Topic,
    Quiz, QuizAttempt, StudentResponse, Question,
    Mastery, Note, NoteCompletion, Assignment, Notification,
)
from app.schemas import (
    StudentOut, UserOut, StudentDashboard, TopicMasteryOut,
    RecommendationOut, AssignmentOut, NotificationOut,
)


def get_student_dashboard(db: Session, student: Student) -> dict:
    """Build complete student dashboard data from database."""
    user = student.user

    # Overall performance
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student.id,
        QuizAttempt.status == "completed"
    ).all()

    total_questions = 0
    total_correct = 0
    for attempt in attempts:
        total_questions += attempt.total_questions
        total_correct += attempt.correct_answers

    overall_score = (total_correct / total_questions * 100) if total_questions > 0 else 0

    # Get enrolled courses and topics
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    class_ids = [e.class_id for e in enrollments]
    classes = db.query(Class).filter(Class.id.in_(class_ids)).all() if class_ids else []
    course_ids = list(set(c.course_id for c in classes))
    topics = db.query(Topic).filter(Topic.course_id.in_(course_ids)).all() if course_ids else []

    # Topic mastery
    topic_mastery_list = []
    mastered_count = 0
    attention_count = 0
    for topic in topics:
        mastery = db.query(Mastery).filter(
            Mastery.student_id == student.id,
            Mastery.topic_id == topic.id
        ).first()

        score = mastery.mastery_score if mastery else 0
        q_attempted = mastery.questions_attempted if mastery else 0
        q_correct = mastery.questions_correct if mastery else 0

        if score >= 0.8:
            status = "mastered"
            mastered_count += 1
            action = None
        elif score >= 0.5:
            status = "working_towards"
            action = "Continue practicing"
        elif q_attempted > 0:
            status = "needs_attention"
            attention_count += 1
            action = "Review notes and take practice test"
        else:
            status = "not_started"
            action = "Start learning this topic"

        topic_mastery_list.append(TopicMasteryOut(
            topic_id=topic.id,
            topic_name=topic.name,
            mastery_score=round(score * 100, 1),
            questions_attempted=q_attempted,
            questions_correct=q_correct,
            status=status,
            recommended_action=action,
        ))

    # Performance trend (last 10 quizzes)
    recent_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student.id,
        QuizAttempt.status == "completed"
    ).order_by(QuizAttempt.completed_at.desc()).limit(20).all()

    performance_trend = []
    for att in reversed(recent_attempts):
        quiz = db.query(Quiz).filter(Quiz.id == att.quiz_id).first()
        performance_trend.append({
            "date": att.completed_at.isoformat() if att.completed_at else att.started_at.isoformat(),
            "score": round(att.score, 1) if att.score else 0,
            "quiz": quiz.title if quiz else "Quiz",
        })

    # Recommendations
    recommendations = _generate_recommendations(db, student, topic_mastery_list)

    # Upcoming assignments
    upcoming = db.query(Assignment).filter(
        Assignment.student_id == student.id,
        Assignment.status.in_(["pending", "in_progress"])
    ).order_by(Assignment.due_date).limit(5).all()

    assignment_list = []
    for a in upcoming:
        topic = db.query(Topic).filter(Topic.id == a.topic_id).first()
        assignment_list.append(AssignmentOut(
            id=a.id, title=a.title, description=a.description,
            topic_name=topic.name if topic else None,
            difficulty=a.difficulty, question_count=a.question_count,
            due_date=a.due_date, status=a.status.value if hasattr(a.status, 'value') else a.status,
            score=a.score, created_at=a.created_at,
        ))

    # Notifications
    notifs = db.query(Notification).filter(
        Notification.student_id == student.id
    ).order_by(Notification.created_at.desc()).limit(10).all()

    notif_list = [
        NotificationOut(
            id=n.id, type=n.type.value if hasattr(n.type, 'value') else n.type,
            title=n.title, message=n.message, is_read=n.is_read,
            link=n.link, created_at=n.created_at,
        ) for n in notifs
    ]

    # Recent activity
    recent_activity = []
    for att in recent_attempts[:5]:
        quiz = db.query(Quiz).filter(Quiz.id == att.quiz_id).first()
        recent_activity.append({
            "type": "quiz_completed",
            "title": f"Completed: {quiz.title}" if quiz else "Quiz completed",
            "score": round(att.score, 1) if att.score else 0,
            "date": att.completed_at.isoformat() if att.completed_at else "",
        })

    student_out = StudentOut(
        id=student.id, user_id=student.user_id,
        student_code=student.student_code, grade_level=student.grade_level,
        user=UserOut(
            id=user.id, email=user.email, full_name=user.full_name,
            role=user.role.value, avatar_url=user.avatar_url,
        )
    )

    return {
        "student": student_out.model_dump(),
        "overall_score": round(overall_score, 1),
        "total_questions_attempted": total_questions,
        "total_correct": total_correct,
        "quizzes_completed": len(attempts),
        "topics_mastered": mastered_count,
        "topics_needing_attention": attention_count,
        "total_topics": len(topics),
        "recent_activity": recent_activity,
        "performance_trend": performance_trend,
        "topic_mastery": [tm.model_dump() for tm in topic_mastery_list],
        "recommendations": [r.model_dump() for r in recommendations],
        "upcoming_assignments": [a.model_dump() for a in assignment_list],
        "notifications": [n.model_dump() for n in notif_list],
    }


def _generate_recommendations(
    db: Session, student: Student, topic_mastery: list[TopicMasteryOut]
) -> list[RecommendationOut]:
    """Generate personalized recommendations based on mastery data."""
    recs = []
    priority = 0

    for tm in sorted(topic_mastery, key=lambda x: x.mastery_score):
        if tm.status == "needs_attention":
            priority += 1
            recs.append(RecommendationOut(
                type="revise_topic",
                title=f"Review: {tm.topic_name}",
                description=f"Your mastery is {tm.mastery_score}%. Reviewing notes will help strengthen your understanding.",
                topic_id=tm.topic_id,
                topic_name=tm.topic_name,
                priority=priority,
                action_url=f"/student/notes?topic={tm.topic_id}",
            ))
            recs.append(RecommendationOut(
                type="practice_test",
                title=f"Practice: {tm.topic_name}",
                description=f"Take a practice test to improve your skills in {tm.topic_name}.",
                topic_id=tm.topic_id,
                topic_name=tm.topic_name,
                priority=priority,
                action_url=f"/student/practice?topic={tm.topic_id}",
            ))
        elif tm.status == "not_started" and tm.questions_attempted == 0:
            priority += 1
            recs.append(RecommendationOut(
                type="review_notes",
                title=f"Start Learning: {tm.topic_name}",
                description=f"Begin with the important notes for {tm.topic_name}.",
                topic_id=tm.topic_id,
                topic_name=tm.topic_name,
                priority=priority,
                action_url=f"/student/notes?topic={tm.topic_id}",
            ))

    return recs[:8]  # Limit to top 8 recommendations


def get_student_performance(db: Session, student: Student, days: int = 30) -> dict:
    """Get detailed performance data for a student."""
    since = datetime.utcnow() - timedelta(days=days)
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student.id,
        QuizAttempt.status == "completed",
        QuizAttempt.completed_at >= since
    ).order_by(QuizAttempt.completed_at).all()

    scores = [a.score for a in attempts if a.score is not None]
    return {
        "period_days": days,
        "total_attempts": len(attempts),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "highest_score": round(max(scores), 1) if scores else 0,
        "lowest_score": round(min(scores), 1) if scores else 0,
        "trend": [
            {
                "date": a.completed_at.isoformat(),
                "score": round(a.score, 1) if a.score else 0,
            }
            for a in attempts
        ],
    }
