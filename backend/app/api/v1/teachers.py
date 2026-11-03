"""Teacher API routes."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_teacher
from app.models import Teacher, Course, Topic
from app.services.teacher_service import (
    get_teacher_dashboard, create_assignment, get_student_detail,
)
from app.schemas import AssignmentCreate

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("/me/dashboard")
def teacher_dashboard(
    class_id: Optional[uuid.UUID] = None,
    teacher: Teacher = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return get_teacher_dashboard(db, teacher, class_id)


@router.get("/me/classes")
def list_classes(
    teacher: Teacher = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    from app.models import Class, Enrollment
    classes = db.query(Class).filter(Class.teacher_id == teacher.id).all()
    result = []
    for c in classes:
        count = db.query(Enrollment).filter(Enrollment.class_id == c.id).count()
        course = db.query(Course).filter(Course.id == c.course_id).first()
        result.append({
            "id": str(c.id), "name": c.name, "section": c.section,
            "course_id": str(c.course_id),
            "course_name": course.name if course else None,
            "student_count": count,
        })
    return result


@router.get("/students/{student_id}")
def view_student(
    student_id: uuid.UUID,
    teacher: Teacher = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    detail = get_student_detail(db, teacher, student_id)
    if not detail:
        raise HTTPException(404, "Student not found")
    return detail


@router.post("/assignments")
def assign_practice(
    data: AssignmentCreate,
    teacher: Teacher = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    assignment = create_assignment(db, teacher, data)
    return {
        "id": str(assignment.id),
        "title": assignment.title,
        "status": assignment.status.value,
        "message": "Assignment created and student notified",
    }


@router.get("/courses")
def list_courses(
    teacher: Teacher = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    from app.models import Class
    class_course_ids = db.query(Class.course_id).filter(
        Class.teacher_id == teacher.id
    ).distinct().all()
    course_ids = [c[0] for c in class_course_ids]
    courses = db.query(Course).filter(Course.id.in_(course_ids)).all() if course_ids else []
    return [
        {
            "id": str(c.id), "name": c.name, "code": c.code,
            "description": c.description,
            "topics": [
                {"id": str(t.id), "name": t.name}
                for t in db.query(Topic).filter(Topic.course_id == c.id).order_by(Topic.order_index).all()
            ],
        }
        for c in courses
    ]
