import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './store/authStore';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import LoadingSpinner from './components/LoadingSpinner';
import LoginPage from './pages/LoginPage';
import StudentDashboard from './pages/student/Dashboard';
import QuizPage from './pages/student/QuizPage';
import ResultsPage from './pages/student/ResultsPage';
import NotesPage from './pages/student/NotesPage';
import AssignmentsPage from './pages/student/AssignmentsPage';
import TeacherDashboard from './pages/teacher/Dashboard';
import StudentDetailPage from './pages/teacher/StudentDetailPage';
import CloudDashboard from './pages/experiments/CloudDashboard';

export default function App() {
  const { isLoading, isAuthenticated, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />

      {/* Student routes */}
      <Route element={<ProtectedRoute role="student" />}>
        <Route element={<Layout />}>
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/student/quiz/:quizId" element={<QuizPage />} />
          <Route path="/student/results/:attemptId" element={<ResultsPage />} />
          <Route path="/student/notes" element={<NotesPage />} />
          <Route path="/student/assignments" element={<AssignmentsPage />} />
        </Route>
      </Route>

      {/* Teacher routes */}
      <Route element={<ProtectedRoute role="teacher" />}>
        <Route element={<Layout />}>
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/teacher/student/:studentId" element={<StudentDetailPage />} />
        </Route>
      </Route>

      {/* Cloud experiments (accessible by all authenticated users) */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/experiments" element={<CloudDashboard />} />
        </Route>
      </Route>

      {/* Default redirect */}
      <Route
        path="*"
        element={
          isAuthenticated ? (
            <Navigate to={user?.role === 'teacher' ? '/teacher' : '/student'} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

