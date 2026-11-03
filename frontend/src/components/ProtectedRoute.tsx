import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/store/authStore';
import LoadingSpinner from './LoadingSpinner';

interface Props {
  role?: 'student' | 'teacher';
}

export default function ProtectedRoute({ role }: Props) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role && user?.role !== role) {
    return <Navigate to={user?.role === 'teacher' ? '/teacher' : '/student'} replace />;
  }

  return <Outlet />;
}

