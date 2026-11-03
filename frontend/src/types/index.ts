/* ───────── Auth ───────── */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'student' | 'teacher';
  avatar_url: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

/* ───────── Student ───────── */

export interface StudentProfile {
  id: string;
  user_id: string;
  student_code: string;
  grade_level: number | null;
  user: User | null;
}

export interface TopicMastery {
  topic_id: string;
  topic_name: string;
  mastery_score: number;
  questions_attempted: number;
  questions_correct: number;
  status: 'mastered' | 'working_towards' | 'needs_attention' | 'not_started';
  recommended_action: string | null;
}

export interface Recommendation {
  type: 'revise_topic' | 'practice_test' | 'review_notes' | 'review_mistakes';
  title: string;
  description: string;
  topic_id: string | null;
  topic_name: string | null;
  priority: number;
  action_url: string | null;
}

export interface PerformanceTrend {
  date: string;
  score: number;
  quiz: string;
}

export interface RecentActivity {
  type: string;
  title: string;
  score: number;
  date: string;
}

export interface StudentDashboard {
  student: StudentProfile;
  overall_score: number;
  total_questions_attempted: number;
  total_correct: number;
  quizzes_completed: number;
  topics_mastered: number;
  topics_needing_attention: number;
  total_topics: number;
  recent_activity: RecentActivity[];
  performance_trend: PerformanceTrend[];
  topic_mastery: TopicMastery[];
  recommendations: Recommendation[];
  upcoming_assignments: Assignment[];
  notifications: Notification[];
}

export interface StudentPerformance {
  period_days: number;
  total_attempts: number;
  average_score: number;
  highest_score: number;
  lowest_score: number;
  trend: { date: string; score: number }[];
}

/* ───────── Teacher ───────── */

export interface TeacherProfile {
  id: string;
  user_id: string;
  teacher_code: string;
  department: string | null;
  user: User | null;
}

export interface ClassInfo {
  id: string;
  name: string;
  section: string | null;
  course_id: string;
  student_count: number;
  course_name?: string;
}

export interface StudentProficiency {
  student_id: string;
  student_name: string;
  avatar_url: string | null;
  questions_completed: number;
  average_score: number;
  needs_attention: number;
  working_towards: number;
  mastered: number;
}

export interface TopicDistribution {
  topic: string;
  topic_id: string;
  mastered: number;
  working_towards: number;
  needs_attention: number;
  not_started: number;
}

export interface TeacherAlert {
  student_id: string;
  student_name: string;
  avatar_url: string | null;
  topic: string;
  topic_id: string;
  mastery: number;
  reason: string;
  recommended_action: string;
}

export interface TeacherDashboard {
  teacher: TeacherProfile;
  classes: ClassInfo[];
  selected_class: ClassInfo | null;
  class_average_score: number;
  total_students: number;
  total_questions_completed: number;
  students_needing_attention: number;
  topics_mastered_count: number;
  student_proficiency: StudentProficiency[];
  class_performance: { date: string; average_score: number; count: number }[];
  topic_distribution: TopicDistribution[];
  alerts: TeacherAlert[];
}

export interface StudentDetail {
  student_id: string;
  student_name: string;
  avatar_url: string | null;
  email: string;
  overall_score: number;
  total_questions: number;
  total_correct: number;
  quizzes_completed: number;
  topic_mastery: { topic_id: string; topic_name: string; mastery_score: number; questions_attempted: number; questions_correct: number }[];
  quiz_history: { attempt_id: string; quiz_title: string; score: number; total_questions: number; correct_answers: number; date: string }[];
  assignments: { id: string; title: string; status: string; score: number | null; due_date: string | null }[];
}

/* ───────── Course / Topic ───────── */

export interface Course {
  id: string;
  name: string;
  code: string;
  description: string | null;
  topics?: { id: string; name: string }[];
}

export interface Topic {
  id: string;
  course_id: string;
  name: string;
  description: string | null;
  order_index: number;
}

/* ───────── Quiz ───────── */

export interface Quiz {
  id: string;
  title: string;
  description: string | null;
  course_id: string;
  topic_id: string | null;
  difficulty: string;
  question_count: number;
  time_limit_minutes: number | null;
  is_practice: boolean;
}

export interface Question {
  id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  code_snippet: string | null;
  options: Record<string, string> | null;
}

export interface AttemptStart {
  attempt_id: string;
  quiz: { id: string; title: string; time_limit_minutes: number | null };
  questions: Question[];
}

export interface ResponseResult {
  question_id: string;
  question_text: string;
  submitted_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string | null;
}

export interface AttemptResult {
  attempt_id: string;
  quiz_title: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  started_at?: string;
  completed_at?: string;
  responses: ResponseResult[];
  recommendations?: string[];
}

export interface PracticeTestResult {
  quiz_id: string;
  title: string;
  topic: string;
  difficulty: string;
  question_count: number;
}

/* ───────── Notes ───────── */

export interface NoteContent {
  definitions?: string[];
  key_concepts?: string[];
  syntax?: string[];
  examples?: { code: string; output: string; explanation: string }[];
  common_mistakes?: string[];
  revision_checklist?: string[];
}

export interface Note {
  id: string;
  course_id: string;
  topic_id: string;
  title: string;
  summary: string | null;
  content: NoteContent;
  is_ai_generated: boolean;
  topic_name: string | null;
  is_completed: boolean;
}

/* ───────── Assignment ───────── */

export interface Assignment {
  id: string;
  title: string;
  description: string | null;
  topic_name: string | null;
  difficulty: string;
  question_count: number;
  due_date: string | null;
  status: string;
  score: number | null;
  created_at: string;
}

export interface AssignmentCreate {
  student_id: string;
  topic_id: string;
  title: string;
  description?: string;
  difficulty?: string;
  question_count?: number;
  due_date?: string;
}

/* ───────── Notification ───────── */

export interface Notification {
  id: string;
  type: 'assignment' | 'recommendation' | 'achievement' | 'alert' | 'system';
  title: string;
  message: string;
  is_read: boolean;
  link: string | null;
  created_at: string;
}

/* ───────── Experiments ───────── */

export interface ExperimentConfig {
  name: string;
  scenario: 'normal' | 'increasing' | 'burst' | 'deadline' | 'low' | 'mixed';
  scaling_policy: 'reactive' | 'predictive';
  duration_seconds: number;
  base_request_rate: number;
  burst_multiplier: number;
  forecast_horizon_seconds: number;
  min_instances: number;
  max_instances: number;
  sla_latency_ms: number;
  scaling_cooldown_seconds: number;
  random_seed: number;
}

export interface ExperimentSummary {
  id: string;
  name: string;
  scenario: string;
  scaling_policy: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  results_summary: Record<string, any> | null;
  is_simulation: boolean;
  created_at?: string;
  configuration?: Record<string, any>;
}

export interface ExperimentMetrics {
  experiment_id: string;
  timestamps: string[];
  request_counts: number[];
  predicted_requests: number[];
  avg_latencies: number[];
  p95_latencies: number[];
  p99_latencies: number[];
  cpu_utilizations: number[];
  memory_utilizations: number[];
  active_instances: number[];
  scaling_actions: string[];
  sla_violations: boolean[];
  costs: number[];
}

export interface ExperimentComparison {
  reactive: { experiment: ExperimentSummary; metrics: ExperimentMetrics };
  predictive: { experiment: ExperimentSummary; metrics: ExperimentMetrics };
  comparison: {
    latency_improvement_pct: number;
    p95_improvement_pct: number;
    sla_violation_diff: number;
    cost_diff_usd: number;
    scaling_actions_diff: number;
  };
}

export interface CloudOverview {
  current_request_rate: number;
  predicted_request_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  cpu_utilization: number;
  memory_utilization: number;
  estimated_cost_usd: number;
  sla_status: string;
  active_experiments: number;
  total_experiments: number;
}

