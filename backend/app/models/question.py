"""Question model for quizzes and practice tests."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
import enum

from app.database import Base


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    OUTPUT_PREDICTION = "output_prediction"
    CODE_BASED = "code_based"


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType), default=QuestionType.MULTIPLE_CHOICE
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SAEnum(DifficultyLevel), default=DifficultyLevel.BEGINNER
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=True)
    options: Mapped[dict] = mapped_column(JSON, nullable=True)  # {"A": "...", "B": "...", ...}
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="questions")
    topic = relationship("Topic", back_populates="questions")
    responses = relationship("StudentResponse", back_populates="question")
