"""Student API routes."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_student
from app.models import Student, Note, NoteCompletion, Topic, Notification
from app.services.student_service import get_student_dashboard, get_student_performance
from app.services.quiz_service import (
    get_quizzes_for_student, start_attempt, submit_response,
    submit_attempt, get_attempt_result, generate_practice_test,
)
from app.schemas import ResponseSubmit

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me/dashboard")
def student_dashboard(
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    return get_student_dashboard(db, student)


@router.get("/me/performance")
def student_performance(
    days: int = Query(30, ge=1, le=365),
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    return get_student_performance(db, student, days)


@router.get("/me/mastery")
def student_mastery(
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    from app.models import Mastery, Topic
    masteries = db.query(Mastery).filter(Mastery.student_id == student.id).all()
    result = []
    for m in masteries:
        topic = db.query(Topic).filter(Topic.id == m.topic_id).first()
        result.append({
            "topic_id": str(m.topic_id),
            "topic_name": topic.name if topic else "Unknown",
            "mastery_score": round(m.mastery_score * 100, 1),
            "questions_attempted": m.questions_attempted,
            "questions_correct": m.questions_correct,
            "source": m.source,
        })
    return result


# ─────────── Quizzes & Practice Tests ───────────

@router.get("/me/quizzes")
def list_quizzes(
    course_id: Optional[uuid.UUID] = None,
    topic_id: Optional[uuid.UUID] = None,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    return get_quizzes_for_student(db, student.id, course_id, topic_id)


@router.post("/me/quizzes/{quiz_id}/start")
def start_quiz(
    quiz_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    result = start_attempt(db, student, quiz_id)
    if not result:
        raise HTTPException(404, "Quiz not found")
    return result


@router.post("/me/attempts/{attempt_id}/respond")
def respond_to_question(
    attempt_id: uuid.UUID,
    data: ResponseSubmit,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    result = submit_response(db, attempt_id, data)
    if not result:
        raise HTTPException(400, "Invalid attempt or question")
    return result


@router.post("/me/attempts/{attempt_id}/submit")
def finish_attempt(
    attempt_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    result = submit_attempt(db, student, attempt_id)
    if not result:
        raise HTTPException(404, "Attempt not found")
    return result


@router.get("/me/attempts/{attempt_id}/results")
def attempt_results(
    attempt_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    result = get_attempt_result(db, student, attempt_id)
    if not result:
        raise HTTPException(404, "Attempt not found or not completed")
    return result


@router.post("/me/practice/generate")
def gen_practice(
    topic_id: uuid.UUID = Query(...),
    difficulty: str = Query("beginner"),
    count: int = Query(5, ge=1, le=20),
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    result = generate_practice_test(db, student, topic_id, difficulty, count)
    if not result:
        raise HTTPException(404, "No questions available for this topic/difficulty")
    return result


# ─────────── Notes ───────────

@router.get("/me/notes")
def list_notes(
    course_id: Optional[uuid.UUID] = None,
    topic_id: Optional[uuid.UUID] = None,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    query = db.query(Note)
    if course_id:
        query = query.filter(Note.course_id == course_id)
    if topic_id:
        query = query.filter(Note.topic_id == topic_id)
    notes = query.all()

    result = []
    for n in notes:
        topic = db.query(Topic).filter(Topic.id == n.topic_id).first()
        completion = db.query(NoteCompletion).filter(
            NoteCompletion.student_id == student.id,
            NoteCompletion.note_id == n.id,
        ).first()
        result.append({
            "id": str(n.id), "course_id": str(n.course_id),
            "topic_id": str(n.topic_id), "title": n.title,
            "summary": n.summary, "content": n.content,
            "is_ai_generated": n.is_ai_generated,
            "topic_name": topic.name if topic else None,
            "is_completed": completion.completed if completion else False,
        })
    return result


@router.get("/me/notes/{note_id}")
def get_note(
    note_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")

    # Record view
    completion = db.query(NoteCompletion).filter(
        NoteCompletion.student_id == student.id,
        NoteCompletion.note_id == note_id,
    ).first()
    if not completion:
        completion = NoteCompletion(student_id=student.id, note_id=note_id)
        db.add(completion)
        db.commit()

    topic = db.query(Topic).filter(Topic.id == note.topic_id).first()
    return {
        "id": str(note.id), "title": note.title, "summary": note.summary,
        "content": note.content, "topic_name": topic.name if topic else None,
        "is_ai_generated": note.is_ai_generated,
        "is_completed": completion.completed,
    }


@router.post("/me/notes/{note_id}/complete")
def complete_note(
    note_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    completion = db.query(NoteCompletion).filter(
        NoteCompletion.student_id == student.id,
        NoteCompletion.note_id == note_id,
    ).first()
    if not completion:
        completion = NoteCompletion(student_id=student.id, note_id=note_id,
                                    completed=True, completed_at=datetime.utcnow())
        db.add(completion)
    else:
        completion.completed = True
        completion.completed_at = datetime.utcnow()
    db.commit()
    return {"message": "Note marked as completed"}


# ─────────── Assignments & Notifications ───────────

@router.get("/me/assignments")
def list_assignments(
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    from app.models import Assignment
    assignments = db.query(Assignment).filter(
        Assignment.student_id == student.id
    ).order_by(Assignment.created_at.desc()).all()
    result = []
    for a in assignments:
        topic = db.query(Topic).filter(Topic.id == a.topic_id).first()
        result.append({
            "id": str(a.id), "title": a.title, "description": a.description,
            "topic_name": topic.name if topic else None,
            "difficulty": a.difficulty, "question_count": a.question_count,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "status": a.status.value if hasattr(a.status, 'value') else a.status,
            "score": a.score, "created_at": a.created_at.isoformat(),
        })
    return result


@router.get("/me/notifications")
def list_notifications(
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    notifs = db.query(Notification).filter(
        Notification.student_id == student.id
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return [
        {
            "id": str(n.id),
            "type": n.type.value if hasattr(n.type, 'value') else n.type,
            "title": n.title, "message": n.message,
            "is_read": n.is_read, "link": n.link,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]


@router.post("/me/notifications/{notification_id}/read")
def mark_read(
    notification_id: uuid.UUID,
    student: Student = Depends(require_student),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.student_id == student.id,
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Marked as read"}
