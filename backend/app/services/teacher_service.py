"""Teacher service — class analytics, student proficiency, assignments."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Teacher, Class, Student, User, Enrollment, Course, Topic,
    Quiz, QuizAttempt, StudentResponse, Question,
    Mastery, Assignment, Notification, NotificationType, AssignmentStatus,
)
from app.schemas import (
    TeacherOut, UserOut, ClassOut, StudentProficiency,
    AssignmentOut, AssignmentCreate,
)


def get_teacher_dashboard(db: Session, teacher: Teacher, class_id: Optional[uuid.UUID] = None) -> dict:
    """Build teacher dashboard with class-level analytics."""
    user = teacher.user

    # Get teacher's classes
    classes = db.query(Class).filter(Class.teacher_id == teacher.id).all()
    class_list = []
    for cls in classes:
        enrollment_count = db.query(Enrollment).filter(Enrollment.class_id == cls.id).count()
        class_list.append(ClassOut(
            id=cls.id, name=cls.name, section=cls.section,
            course_id=cls.course_id, student_count=enrollment_count,
        ))

    # Select class
    selected_class = None
    if class_id:
        selected_class = next((c for c in class_list if c.id == class_id), None)
    if not selected_class and class_list:
        selected_class = class_list[0]

    if not selected_class:
        return _empty_teacher_dashboard(teacher, user, class_list)

    # Get students in selected class
    enrollments = db.query(Enrollment).filter(Enrollment.class_id == selected_class.id).all()
    student_ids = [e.student_id for e in enrollments]
    students = db.query(Student).filter(Student.id.in_(student_ids)).all() if student_ids else []

    # Get course topics
    topics = db.query(Topic).filter(Topic.course_id == selected_class.course_id).all()

    # Calculate proficiency for each student
    student_proficiency = []
    total_class_score = 0
    total_questions = 0
    students_needing_attention = 0
    topics_mastered_total = 0

    for student in students:
        s_user = student.user
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.student_id == student.id,
            QuizAttempt.status == "completed"
        ).all()

        q_completed = sum(a.total_questions for a in attempts)
        q_correct = sum(a.correct_answers for a in attempts)
        avg_score = (q_correct / q_completed * 100) if q_completed > 0 else 0

        # Topic mastery counts
        masteries = db.query(Mastery).filter(Mastery.student_id == student.id).all()
        mastered = sum(1 for m in masteries if m.mastery_score >= 0.8)
        working = sum(1 for m in masteries if 0.5 <= m.mastery_score < 0.8)
        needs_att = sum(1 for m in masteries if 0 < m.mastery_score < 0.5)

        if needs_att > 0 or (q_completed > 5 and avg_score < 50):
            students_needing_attention += 1

        total_class_score += avg_score
        total_questions += q_completed
        topics_mastered_total += mastered

        student_proficiency.append(StudentProficiency(
            student_id=student.id,
            student_name=s_user.full_name,
            avatar_url=s_user.avatar_url,
            questions_completed=q_completed,
            average_score=round(avg_score, 1),
            needs_attention=needs_att,
            working_towards=working,
            mastered=mastered,
        ))

    class_avg = round(total_class_score / len(students), 1) if students else 0

    # Class performance over time
    class_performance = _get_class_performance(db, student_ids)

    # Topic distribution
    topic_distribution = _get_topic_distribution(db, student_ids, topics)

    # Alerts
    alerts = _get_teacher_alerts(db, students, topics)

    teacher_out = TeacherOut(
        id=teacher.id, user_id=teacher.user_id,
        teacher_code=teacher.teacher_code, department=teacher.department,
        user=UserOut(
            id=user.id, email=user.email, full_name=user.full_name,
            role=user.role.value, avatar_url=user.avatar_url,
        )
    )

    return {
        "teacher": teacher_out.model_dump(),
        "classes": [c.model_dump() for c in class_list],
        "selected_class": selected_class.model_dump() if selected_class else None,
        "class_average_score": class_avg,
        "total_students": len(students),
        "total_questions_completed": total_questions,
        "students_needing_attention": students_needing_attention,
        "topics_mastered_count": topics_mastered_total,
        "student_proficiency": [sp.model_dump() for sp in student_proficiency],
        "class_performance": class_performance,
        "topic_distribution": topic_distribution,
        "alerts": alerts,
    }


def _empty_teacher_dashboard(teacher, user, class_list):
    teacher_out = TeacherOut(
        id=teacher.id, user_id=teacher.user_id,
        teacher_code=teacher.teacher_code, department=teacher.department,
        user=UserOut(id=user.id, email=user.email, full_name=user.full_name,
                     role=user.role.value, avatar_url=user.avatar_url)
    )
    return {
        "teacher": teacher_out.model_dump(),
        "classes": [c.model_dump() for c in class_list],
        "selected_class": None,
        "class_average_score": 0, "total_students": 0,
        "total_questions_completed": 0, "students_needing_attention": 0,
        "topics_mastered_count": 0, "student_proficiency": [],
        "class_performance": [], "topic_distribution": [], "alerts": [],
    }


def _get_class_performance(db: Session, student_ids: list[uuid.UUID]) -> list[dict]:
    """Aggregate class performance over time."""
    if not student_ids:
        return []
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id.in_(student_ids),
        QuizAttempt.status == "completed"
    ).order_by(QuizAttempt.completed_at).all()

    # Group by date
    by_date = {}
    for a in attempts:
        if a.completed_at:
            d = a.completed_at.strftime("%Y-%m-%d")
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(a.score if a.score else 0)

    return [
        {"date": d, "average_score": round(sum(scores) / len(scores), 1), "count": len(scores)}
        for d, scores in sorted(by_date.items())
    ]


def _get_topic_distribution(db: Session, student_ids: list[uuid.UUID], topics) -> list[dict]:
    """Get mastery distribution per topic."""
    dist = []
    for topic in topics:
        masteries = db.query(Mastery).filter(
            Mastery.student_id.in_(student_ids),
            Mastery.topic_id == topic.id
        ).all() if student_ids else []

        mastered = sum(1 for m in masteries if m.mastery_score >= 0.8)
        working = sum(1 for m in masteries if 0.5 <= m.mastery_score < 0.8)
        needs_att = sum(1 for m in masteries if 0 < m.mastery_score < 0.5)
        not_started = len(student_ids) - len(masteries)

        dist.append({
            "topic": topic.name,
            "topic_id": str(topic.id),
            "mastered": mastered, "working_towards": working,
            "needs_attention": needs_att, "not_started": not_started,
        })
    return dist


def _get_teacher_alerts(db: Session, students, topics) -> list[dict]:
    """Generate alerts for students needing attention."""
    alerts = []
    for student in students:
        user = student.user
        for topic in topics:
            mastery = db.query(Mastery).filter(
                Mastery.student_id == student.id,
                Mastery.topic_id == topic.id
            ).first()
            if mastery and 0 < mastery.mastery_score < 0.4 and mastery.questions_attempted >= 3:
                alerts.append({
                    "student_id": str(student.id),
                    "student_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "topic": topic.name,
                    "topic_id": str(topic.id),
                    "mastery": round(mastery.mastery_score * 100, 1),
                    "reason": f"Low mastery ({round(mastery.mastery_score * 100)}%) after {mastery.questions_attempted} questions",
                    "recommended_action": "Assign targeted practice",
                })
    return alerts[:20]


def create_assignment(db: Session, teacher: Teacher, data: AssignmentCreate) -> Assignment:
    """Create a new assignment and notify the student."""
    topic = db.query(Topic).filter(Topic.id == data.topic_id).first()
    assignment = Assignment(
        teacher_id=teacher.id,
        student_id=data.student_id,
        topic_id=data.topic_id,
        title=data.title,
        description=data.description,
        difficulty=data.difficulty,
        question_count=data.question_count,
        due_date=data.due_date,
        status=AssignmentStatus.PENDING,
    )
    db.add(assignment)

    # Send notification
    notification = Notification(
        student_id=data.student_id,
        type=NotificationType.ASSIGNMENT,
        title="New Assignment",
        message=f"You have a new assignment: {data.title}" + (f" on {topic.name}" if topic else ""),
        link=f"/student/assignments/{assignment.id}",
    )
    db.add(notification)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_student_detail(db: Session, teacher: Teacher, student_id: uuid.UUID) -> dict:
    """Get detailed student analytics for a teacher."""
    # Verify the student is in one of the teacher's classes
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None

    user = student.user
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == student.id,
        QuizAttempt.status == "completed"
    ).order_by(QuizAttempt.completed_at.desc()).all()

    total_q = sum(a.total_questions for a in attempts)
    total_c = sum(a.correct_answers for a in attempts)
    overall = round((total_c / total_q * 100), 1) if total_q > 0 else 0

    # Topic mastery
    masteries = db.query(Mastery).filter(Mastery.student_id == student.id).all()
    topic_data = []
    for m in masteries:
        topic = db.query(Topic).filter(Topic.id == m.topic_id).first()
        topic_data.append({
            "topic_id": str(m.topic_id),
            "topic_name": topic.name if topic else "Unknown",
            "mastery_score": round(m.mastery_score * 100, 1),
            "questions_attempted": m.questions_attempted,
            "questions_correct": m.questions_correct,
        })

    # Quiz history
    quiz_history = []
    for a in attempts[:20]:
        quiz = db.query(Quiz).filter(Quiz.id == a.quiz_id).first()
        quiz_history.append({
            "attempt_id": str(a.id),
            "quiz_title": quiz.title if quiz else "Quiz",
            "score": round(a.score, 1) if a.score else 0,
            "total_questions": a.total_questions,
            "correct_answers": a.correct_answers,
            "date": a.completed_at.isoformat() if a.completed_at else "",
        })

    # Assignments
    assignments = db.query(Assignment).filter(
        Assignment.student_id == student.id,
        Assignment.teacher_id == teacher.id
    ).order_by(Assignment.created_at.desc()).all()

    return {
        "student_id": str(student.id),
        "student_name": user.full_name,
        "avatar_url": user.avatar_url,
        "email": user.email,
        "overall_score": overall,
        "total_questions": total_q,
        "total_correct": total_c,
        "quizzes_completed": len(attempts),
        "topic_mastery": topic_data,
        "quiz_history": quiz_history,
        "assignments": [
            {
                "id": str(a.id), "title": a.title,
                "status": a.status.value if hasattr(a.status, 'value') else a.status,
                "score": a.score, "due_date": a.due_date.isoformat() if a.due_date else None,
            }
            for a in assignments
        ],
    }
