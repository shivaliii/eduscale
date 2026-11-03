import api from './client';
import type {
  StudentDashboard, StudentPerformance, TopicMastery,
  Quiz, AttemptStart, AttemptResult, PracticeTestResult,
  Note, Assignment, Notification,
} from '@/types';

export async function getDashboard(): Promise<StudentDashboard> {
  const { data } = await api.get('/students/me/dashboard');
  return data;
}

export async function getPerformance(days = 30): Promise<StudentPerformance> {
  const { data } = await api.get(`/students/me/performance?days=${days}`);
  return data;
}

export async function getMastery(): Promise<TopicMastery[]> {
  const { data } = await api.get('/students/me/mastery');
  return data;
}

export async function getQuizzes(courseId?: string, topicId?: string): Promise<Quiz[]> {
  const params = new URLSearchParams();
  if (courseId) params.set('course_id', courseId);
  if (topicId) params.set('topic_id', topicId);
  const { data } = await api.get(`/students/me/quizzes?${params}`);
  return data;
}

export async function startQuiz(quizId: string): Promise<AttemptStart> {
  const { data } = await api.post(`/students/me/quizzes/${quizId}/start`);
  return data;
}

export async function submitResponse(
  attemptId: string,
  questionId: string,
  answer: string,
  timeSpent?: number,
): Promise<{ is_correct: boolean; question_id: string }> {
  const { data } = await api.post(`/students/me/attempts/${attemptId}/respond`, {
    question_id: questionId,
    submitted_answer: answer,
    time_spent_seconds: timeSpent,
  });
  return data;
}

export async function submitAttempt(attemptId: string): Promise<AttemptResult> {
  const { data } = await api.post(`/students/me/attempts/${attemptId}/submit`);
  return data;
}

export async function getAttemptResults(attemptId: string): Promise<AttemptResult> {
  const { data } = await api.get(`/students/me/attempts/${attemptId}/results`);
  return data;
}

export async function generatePractice(
  topicId: string,
  difficulty = 'beginner',
  count = 5,
): Promise<PracticeTestResult> {
  const { data } = await api.post(
    `/students/me/practice/generate?topic_id=${topicId}&difficulty=${difficulty}&count=${count}`,
  );
  return data;
}

export async function getNotes(courseId?: string, topicId?: string): Promise<Note[]> {
  const params = new URLSearchParams();
  if (courseId) params.set('course_id', courseId);
  if (topicId) params.set('topic_id', topicId);
  const { data } = await api.get(`/students/me/notes?${params}`);
  return data;
}

export async function getNote(noteId: string): Promise<Note> {
  const { data } = await api.get(`/students/me/notes/${noteId}`);
  return data;
}

export async function completeNote(noteId: string): Promise<void> {
  await api.post(`/students/me/notes/${noteId}/complete`);
}

export async function getAssignments(): Promise<Assignment[]> {
  const { data } = await api.get('/students/me/assignments');
  return data;
}

export async function getNotifications(): Promise<Notification[]> {
  const { data } = await api.get('/students/me/notifications');
  return data;
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  await api.post(`/students/me/notifications/${notificationId}/read`);
}

