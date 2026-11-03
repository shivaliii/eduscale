import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/store/authStore';
import * as studentApi from '@/api/students';
import type { StudentDashboard as DashData, Recommendation } from '@/types';
import StatCard from '@/components/StatCard';
import MasteryBar from '@/components/MasteryBar';
import LoadingSpinner from '@/components/LoadingSpinner';
import {
  Trophy, Target, BookOpen, AlertTriangle, Bell, TrendingUp,
  ChevronRight, Lightbulb, ClipboardList, Play,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

export default function StudentDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<DashData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    studentApi.getDashboard()
      .then(setData)
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner size="lg" text="Loading dashboard..." />;
  if (error) return <div className="rounded-2xl bg-red-50 p-6 text-red-700">{error}</div>;
  if (!data) return null;

  const radarData = data.topic_mastery.map((t) => ({
    topic: t.topic_name.length > 12 ? t.topic_name.slice(0, 12) + '…' : t.topic_name,
    score: t.mastery_score,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.full_name?.split(' ')[0]}! 👋</h1>
          <p className="text-gray-500">Here's your learning progress</p>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-violet-600 text-lg font-bold text-white">
          {user?.full_name?.charAt(0)}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Trophy} label="Overall Score" value={`${data.overall_score.toFixed(1)}%`} color="blue" />
        <StatCard icon={Target} label="Quizzes Done" value={data.quizzes_completed} subtitle={`${data.total_questions_attempted} questions`} color="green" />
        <StatCard icon={BookOpen} label="Topics Mastered" value={`${data.topics_mastered}/${data.total_topics}`} color="purple" />
        <StatCard icon={AlertTriangle} label="Needs Attention" value={data.topics_needing_attention} color="orange" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Performance Trend */}
        <div className="lg:col-span-2 rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 flex items-center gap-2">
            <TrendingUp size={20} className="text-blue-500" /> Performance Trend
          </h2>
          {data.performance_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.performance_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="quiz" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: any) => [`${v}%`, 'Score']} />
                <Line type="monotone" dataKey="score" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4, fill: '#3b82f6' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-gray-400">No quiz data yet. Take a quiz to see trends!</p>
          )}
        </div>

        {/* Radar */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Topic Overview</h2>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={radarData} outerRadius={80}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="topic" tick={{ fontSize: 9 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar dataKey="score" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.25} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-gray-400">No mastery data yet</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Topic Mastery */}
        <div className="lg:col-span-2 rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Topic Mastery</h2>
            <span className="text-xs text-gray-400">{data.topics_mastered} mastered</span>
          </div>
          <div className="space-y-4">
            {data.topic_mastery.map((t) => (
              <div key={t.topic_id} className="group">
                <MasteryBar score={t.mastery_score} label={t.topic_name} status={t.status} />
                {t.recommended_action && (
                  <p className="mt-1 text-xs text-gray-400 group-hover:text-gray-600">💡 {t.recommended_action}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Recommendations */}
          <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Lightbulb size={18} className="text-amber-500" /> Recommendations
            </h2>
            {data.recommendations.length > 0 ? (
              <div className="space-y-3">
                {data.recommendations.slice(0, 4).map((r, i) => (
                  <RecCard key={i} rec={r} navigate={navigate} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">Great job! No recommendations right now.</p>
            )}
          </div>

          {/* Notifications */}
          <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Bell size={18} className="text-blue-500" /> Notifications
            </h2>
            {data.notifications.length > 0 ? (
              <div className="space-y-2">
                {data.notifications.slice(0, 5).map((n) => (
                  <div key={n.id} className={`rounded-lg p-3 text-sm ${n.is_read ? 'bg-gray-50' : 'bg-blue-50 border border-blue-100'}`}>
                    <p className="font-medium text-gray-800">{n.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{n.message}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No notifications</p>
            )}
          </div>
        </div>
      </div>

      {/* Quizzes */}
      <QuizSection navigate={navigate} />
    </div>
  );
}

function RecCard({ rec, navigate }: { rec: Recommendation; navigate: ReturnType<typeof useNavigate> }) {
  const colors: Record<string, string> = {
    revise_topic: 'border-l-amber-500 bg-amber-50',
    practice_test: 'border-l-blue-500 bg-blue-50',
    review_notes: 'border-l-emerald-500 bg-emerald-50',
    review_mistakes: 'border-l-red-500 bg-red-50',
  };
  const icons: Record<string, typeof Lightbulb> = {
    revise_topic: BookOpen, practice_test: Play, review_notes: Lightbulb, review_mistakes: AlertTriangle,
  };
  const Icon = icons[rec.type] || Lightbulb;
  return (
    <button
      onClick={() => rec.action_url && navigate(rec.action_url)}
      className={`w-full rounded-lg border-l-4 p-3 text-left hover:shadow-sm ${colors[rec.type] || 'bg-gray-50 border-l-gray-300'}`}
    >
      <div className="flex items-start gap-2">
        <Icon size={14} className="mt-0.5 shrink-0 text-gray-600" />
        <div>
          <p className="text-sm font-medium text-gray-800">{rec.title}</p>
          <p className="text-xs text-gray-500 mt-0.5">{rec.description}</p>
        </div>
      </div>
    </button>
  );
}

function QuizSection({ navigate }: { navigate: ReturnType<typeof useNavigate> }) {
  const [quizzes, setQuizzes] = useState<any[]>([]);
  useEffect(() => { studentApi.getQuizzes().then(setQuizzes).catch(() => {}); }, []);
  if (quizzes.length === 0) return null;
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 flex items-center gap-2">
        <ClipboardList size={18} className="text-violet-500" /> Available Quizzes
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {quizzes.slice(0, 6).map((q: any) => (
          <button key={q.id} onClick={() => navigate(`/student/quiz/${q.id}`)}
            className="flex items-center justify-between rounded-xl border border-gray-100 p-4 text-left hover:border-blue-200 hover:bg-blue-50/50 group">
            <div>
              <p className="font-medium text-gray-800 text-sm">{q.title}</p>
              <p className="text-xs text-gray-400 mt-0.5">{q.question_count} questions · {q.difficulty}</p>
            </div>
            <ChevronRight size={16} className="text-gray-300 group-hover:text-blue-500" />
          </button>
        ))}
      </div>
    </div>
  );
}
