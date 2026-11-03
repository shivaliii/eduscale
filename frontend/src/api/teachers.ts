import api from './client';
import type {
  TeacherDashboard, ClassInfo, StudentDetail,
  Course, AssignmentCreate,
} from '@/types';

export async function getDashboard(classId?: string): Promise<TeacherDashboard> {
  const params = classId ? `?class_id=${classId}` : '';
  const { data } = await api.get(`/teachers/me/dashboard${params}`);
  return data;
}

export async function getClasses(): Promise<ClassInfo[]> {
  const { data } = await api.get('/teachers/me/classes');
  return data;
}

export async function getStudentDetail(studentId: string): Promise<StudentDetail> {
  const { data } = await api.get(`/teachers/students/${studentId}`);
  return data;
}

export async function createAssignment(assignment: AssignmentCreate): Promise<any> {
  const { data } = await api.post('/teachers/assignments', assignment);
  return data;
}

export async function getCourses(): Promise<Course[]> {
  const { data } = await api.get('/teachers/courses');
  return data;
}

