"""Note and NoteCompletion models for Important Notes feature."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    # content structure: {
    #   "definitions": [...],
    #   "key_concepts": [...],
    #   "syntax": "...",
    #   "examples": [{"code": "...", "output": "...", "explanation": "..."}],
    #   "common_mistakes": [...],
    #   "revision_checklist": [...]
    # }
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    content_source: Mapped[str] = mapped_column(String(100), default="curated")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="notes")
    topic = relationship("Topic", back_populates="notes")
    completions = relationship("NoteCompletion", back_populates="note")


class NoteCompletion(Base):
    __tablename__ = "note_completions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id"), nullable=False
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id"), nullable=False
    )
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    student = relationship("Student", back_populates="note_completions")
    note = relationship("Note", back_populates="completions")
