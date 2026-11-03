"""Models package — import all models for SQLAlchemy discovery."""
from app.models.user import User, UserRole
from app.models.student import Student, Enrollment
from app.models.teacher import Teacher, Class
from app.models.course import Course, Topic
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.quiz import Quiz, QuizQuestion, QuizAttempt, StudentResponse
from app.models.mastery import Mastery
from app.models.note import Note, NoteCompletion
from app.models.assignment import Assignment, AssignmentStatus, Notification, NotificationType
from app.models.cloud_metrics import (
    WorkloadObservation, WorkloadForecast,
    CloudExperiment, ExperimentStatus,
    CloudMetric, InferenceLog,
)

__all__ = [
    "User", "UserRole",
    "Student", "Enrollment",
    "Teacher", "Class",
    "Course", "Topic",
    "Question", "QuestionType", "DifficultyLevel",
    "Quiz", "QuizQuestion", "QuizAttempt", "StudentResponse",
    "Mastery",
    "Note", "NoteCompletion",
    "Assignment", "AssignmentStatus", "Notification", "NotificationType",
    "WorkloadObservation", "WorkloadForecast",
    "CloudExperiment", "ExperimentStatus",
    "CloudMetric", "InferenceLog",
]
