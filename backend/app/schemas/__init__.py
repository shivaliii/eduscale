"""Pydantic schemas for request/response validation."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ──────────────────────── Auth ────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut




# ──────────────────────── Student ────────────────────────

class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    student_code: str
    grade_level: Optional[int] = None
    user: Optional[UserOut] = None

class StudentDashboard(BaseModel):
    student: StudentOut
    overall_score: float
    total_questions_attempted: int
    total_correct: int
    quizzes_completed: int
    topics_mastered: int
    topics_needing_attention: int
    total_topics: int
    recent_activity: list[dict[str, Any]] = []
    performance_trend: list[dict[str, Any]] = []
    topic_mastery: list[TopicMasteryOut] = []
    recommendations: list[RecommendationOut] = []
    upcoming_assignments: list[AssignmentOut] = []
    notifications: list[NotificationOut] = []


# ──────────────────────── Teacher ────────────────────────

class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    teacher_code: str
    department: Optional[str] = None
    user: Optional[UserOut] = None

class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    section: Optional[str] = None
    course_id: uuid.UUID
    student_count: int = 0

class TeacherDashboard(BaseModel):
    teacher: TeacherOut
    classes: list[ClassOut] = []
    selected_class: Optional[ClassOut] = None
    class_average_score: float = 0
    total_students: int = 0
    total_questions_completed: int = 0
    students_needing_attention: int = 0
    topics_mastered_count: int = 0
    student_proficiency: list[StudentProficiency] = []
    class_performance: list[dict[str, Any]] = []
    topic_distribution: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []


class StudentProficiency(BaseModel):
    student_id: uuid.UUID
    student_name: str
    avatar_url: Optional[str] = None
    questions_completed: int = 0
    average_score: float = 0
    needs_attention: int = 0
    working_towards: int = 0
    mastered: int = 0


# ──────────────────────── Course / Topic ────────────────────────

class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    topic_count: int = 0

class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    description: Optional[str] = None
    order_index: int = 0

class TopicMasteryOut(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    mastery_score: float
    questions_attempted: int = 0
    questions_correct: int = 0
    status: str = "not_started"  # not_started, needs_attention, working_towards, mastered
    recommended_action: Optional[str] = None


# ──────────────────────── Question ────────────────────────

class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question_text: str
    question_type: str
    difficulty: str
    code_snippet: Optional[str] = None
    options: Optional[dict] = None
    # correct_answer excluded from student-facing responses

class QuestionWithAnswer(QuestionOut):
    correct_answer: str
    explanation: Optional[str] = None


# ──────────────────────── Quiz / Attempt ────────────────────────

class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    course_id: uuid.UUID
    topic_id: Optional[uuid.UUID] = None
    difficulty: str = "beginner"
    question_count: int
    time_limit_minutes: Optional[int] = None
    is_practice: bool = False

class AttemptCreate(BaseModel):
    quiz_id: uuid.UUID

class ResponseSubmit(BaseModel):
    question_id: uuid.UUID
    submitted_answer: str
    time_spent_seconds: Optional[int] = None

class AttemptResult(BaseModel):
    attempt_id: uuid.UUID
    quiz_title: str
    score: float
    total_questions: int
    correct_answers: int
    time_taken_seconds: Optional[int] = None
    responses: list[ResponseResult] = []
    recommendations: list[str] = []

class ResponseResult(BaseModel):
    question_id: uuid.UUID
    question_text: str
    submitted_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None


# ──────────────────────── Notes ────────────────────────

class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    topic_id: uuid.UUID
    title: str
    summary: Optional[str] = None
    content: dict
    is_ai_generated: bool = False
    topic_name: Optional[str] = None
    is_completed: bool = False


# ──────────────────────── Assignment ────────────────────────

class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    topic_name: Optional[str] = None
    difficulty: str = "beginner"
    question_count: int = 10
    due_date: Optional[datetime] = None
    status: str = "pending"
    score: Optional[int] = None
    created_at: datetime

class AssignmentCreate(BaseModel):
    student_id: uuid.UUID
    topic_id: uuid.UUID
    title: str
    description: Optional[str] = None
    difficulty: str = "beginner"
    question_count: int = 10
    due_date: Optional[datetime] = None


# ──────────────────────── Notification ────────────────────────

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool = False
    link: Optional[str] = None
    created_at: datetime


# ──────────────────────── Recommendation ────────────────────────

class RecommendationOut(BaseModel):
    type: str  # revise_topic, practice_test, review_notes, review_mistakes
    title: str
    description: str
    topic_id: Optional[uuid.UUID] = None
    topic_name: Optional[str] = None
    priority: int = 0
    action_url: Optional[str] = None


# ──────────────────────── Cloud / Experiments ────────────────────────

class ExperimentConfig(BaseModel):
    name: str = "Experiment"
    scenario: str = "normal"  # normal, increasing, burst, deadline, low, mixed
    scaling_policy: str = "reactive"  # reactive, predictive
    duration_seconds: int = 300
    base_request_rate: float = 10.0
    burst_multiplier: float = 3.0
    forecast_horizon_seconds: int = 60
    min_instances: int = 1
    max_instances: int = 10
    sla_latency_ms: float = 500.0
    scaling_cooldown_seconds: int = 30
    random_seed: int = 42

class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    scenario: str
    scaling_policy: str
    configuration: dict
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    results_summary: Optional[dict] = None
    is_simulation: bool = True

class ExperimentMetrics(BaseModel):
    experiment_id: uuid.UUID
    timestamps: list[str] = []
    request_counts: list[int] = []
    predicted_requests: list[float] = []
    avg_latencies: list[float] = []
    p95_latencies: list[float] = []
    p99_latencies: list[float] = []
    cpu_utilizations: list[float] = []
    memory_utilizations: list[float] = []
    active_instances: list[int] = []
    scaling_actions: list[str] = []
    sla_violations: list[bool] = []
    costs: list[float] = []

class ExperimentComparison(BaseModel):
    reactive: ExperimentOut
    predictive: ExperimentOut
    reactive_metrics: ExperimentMetrics
    predictive_metrics: ExperimentMetrics
    summary: dict[str, Any] = {}

class WorkloadPredictionOut(BaseModel):
    timestamp: str
    predicted_requests: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_version: str = "baseline"

class CloudOverview(BaseModel):
    current_request_rate: float = 0
    predicted_request_rate: float = 0
    avg_latency_ms: float = 0
    p95_latency_ms: float = 0
    cpu_utilization: float = 0
    memory_utilization: float = 0
    estimated_cost_usd: float = 0
    sla_status: str = "healthy"
    active_experiments: int = 0
    total_experiments: int = 0


# ──────────────────────── Generic ────────────────────────

class HealthCheck(BaseModel):
    status: str = "healthy"
    database: str = "connected"
    model_status: str = "unavailable"
    demo_mode: bool = True
    version: str = "1.0.0"

class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


# Rebuild models that have forward references
StudentDashboard.model_rebuild()
TeacherDashboard.model_rebuild()
AttemptResult.model_rebuild()
ExperimentComparison.model_rebuild()
