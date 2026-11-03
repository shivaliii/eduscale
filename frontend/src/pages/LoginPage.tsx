import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/store/authStore';
import { GraduationCap, Mail, Lock, AlertCircle, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (role: 'teacher' | 'student') => {
    setError('');
    setLoading(true);
    try {
      await login(
        role === 'teacher' ? 'teacher@eduscale.demo' : 'alex@eduscale.demo',
        role === 'teacher' ? 'teacher123' : 'student123',
      );
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center bg-gradient-to-br from-blue-600 via-violet-600 to-purple-700 px-12 text-white">
        <div className="flex items-center gap-4 mb-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
            <GraduationCap size={30} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">EduScale</h1>
            <p className="text-sm text-blue-200">AI-Powered Learning Platform</p>
          </div>
        </div>
        <h2 className="text-4xl font-bold leading-tight mb-4">
          Personalized Learning.<br />Predictive Cloud Scaling.
        </h2>
        <p className="text-lg text-blue-100 max-w-md">
          Adaptive quizzes, knowledge tracing, personalized study notes, and cloud-native resource optimization — all in one platform.
        </p>
        <div className="mt-10 grid grid-cols-3 gap-4">
          {[
            { n: '50+', l: 'Questions' },
            { n: '10', l: 'Topics' },
            { n: '6', l: 'Workload Scenarios' },
          ].map(({ n, l }) => (
            <div key={l} className="rounded-xl bg-white/10 backdrop-blur-sm p-4 text-center">
              <p className="text-2xl font-bold">{n}</p>
              <p className="text-xs text-blue-200">{l}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right — form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center px-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 text-white">
              <GraduationCap size={22} />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">EduScale</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-1">Welcome back</h2>
          <p className="text-gray-500 mb-8">Sign in to continue learning</p>

          {error && (
            <div className="mb-6 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-gray-200 bg-gray-50 py-3 pl-10 pr-4 text-sm focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-gray-200 bg-gray-50 py-3 pl-10 pr-4 text-sm focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all disabled:opacity-60"
            >
              {loading ? <Loader2 className="mx-auto h-5 w-5 animate-spin" /> : 'Sign In'}
            </button>
          </form>

          {/* Quick login */}
          <div className="mt-8">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-xs text-gray-400">
                <span className="bg-white px-3">Demo Accounts</span>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <button
                onClick={() => quickLogin('student')}
                disabled={loading}
                className="rounded-xl border border-gray-200 bg-white py-2.5 text-sm font-medium text-gray-700 hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-700 transition-all"
              >
                🎓 Student
              </button>
              <button
                onClick={() => quickLogin('teacher')}
                disabled={loading}
                className="rounded-xl border border-gray-200 bg-white py-2.5 text-sm font-medium text-gray-700 hover:bg-violet-50 hover:border-violet-200 hover:text-violet-700 transition-all"
              >
                👨‍🏫 Teacher
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

