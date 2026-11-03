import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/store/authStore';
import * as teacherApi from '@/api/teachers';
import type { TeacherDashboard as TDash, StudentProficiency, TeacherAlert } from '@/types';
import StatCard from '@/components/StatCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import {
  Users, Trophy, BookOpen, AlertTriangle, ChevronRight, UserCircle,
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

export default function TeacherDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<TDash | null>(null);
  const [selectedClassId, setSelectedClassId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const fetchData = (classId?: string) => {
    setLoading(true);
    teacherApi.getDashboard(classId)
      .then((d) => { setData(d); if (!classId && d.selected_class) setSelectedClassId(d.selected_class.id); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleClassChange = (cid: string) => { setSelectedClassId(cid); fetchData(cid); };

  if (loading && !data) return <LoadingSpinner size="lg" text="Loading dashboard..." />;
  if (!data) return <div className="text-center py-16 text-gray-500">No data available</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hello, {user?.full_name?.split(' ')[0]}! 👨‍🏫</h1>
          <p className="text-gray-500">Class overview and student analytics</p>
        </div>
        {data.classes.length > 0 && (
          <select
            value={selectedClassId}
            onChange={(e) => handleClassChange(e.target.value)}
            className="rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            {data.classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.student_count} students)</option>
            ))}
          </select>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Trophy} label="Class Average" value={`${data.class_average_score}%`} color="blue" />
        <StatCard icon={Users} label="Total Students" value={data.total_students} color="green" />
        <StatCard icon={BookOpen} label="Questions Done" value={data.total_questions_completed} color="purple" />
        <StatCard icon={AlertTriangle} label="Need Attention" value={data.students_needing_attention} color="orange" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Performance over time */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Class Performance</h2>
          {data.class_performance.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.class_performance}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="average_score" name="Avg Score" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-gray-400">No performance data yet</p>
          )}
        </div>

        {/* Topic distribution */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Topic Mastery Distribution</h2>
          {data.topic_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.topic_distribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="topic" type="category" width={90} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="mastered" stackId="a" fill="#10b981" name="Mastered" />
                <Bar dataKey="working_towards" stackId="a" fill="#fbbf24" name="Working" />
                <Bar dataKey="needs_attention" stackId="a" fill="#ef4444" name="Needs Attn" />
                <Bar dataKey="not_started" stackId="a" fill="#d1d5db" name="Not Started" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-gray-400">No topic data yet</p>
          )}
        </div>
      </div>

      {/* Student Proficiency Table */}
      <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Student Proficiency</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-gray-500">
                <th className="pb-3 font-medium">Student</th>
                <th className="pb-3 font-medium">Questions</th>
                <th className="pb-3 font-medium">Avg Score</th>
                <th className="pb-3 font-medium">Mastered</th>
                <th className="pb-3 font-medium">Working</th>
                <th className="pb-3 font-medium">Attention</th>
                <th className="pb-3" />
              </tr>
            </thead>
            <tbody>
              {data.student_proficiency.map((s) => (
                <tr key={s.student_id} onClick={() => navigate(`/teacher/student/${s.student_id}`)}
                  className="border-b border-gray-50 cursor-pointer hover:bg-blue-50/50 transition-colors">
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-xs font-bold text-white">
                        {s.student_name.charAt(0)}
                      </div>
                      <span className="font-medium text-gray-800">{s.student_name}</span>
                    </div>
                  </td>
                  <td className="py-3 text-gray-600">{s.questions_completed}</td>
                  <td className="py-3">
                    <span className={`font-semibold ${s.average_score >= 70 ? 'text-emerald-600' : s.average_score >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                      {s.average_score}%
                    </span>
                  </td>
                  <td className="py-3"><span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">{s.mastered}</span></td>
                  <td className="py-3"><span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">{s.working_towards}</span></td>
                  <td className="py-3"><span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{s.needs_attention}</span></td>
                  <td className="py-3"><ChevronRight size={16} className="text-gray-300" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alerts */}
      {data.alerts.length > 0 && (
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-500" /> Learning Gap Alerts
          </h2>
          <div className="space-y-3">
            {data.alerts.map((a, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl border border-red-100 bg-red-50/50 p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-red-500 text-xs font-bold text-white">
                    {a.student_name.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{a.student_name}</p>
                    <p className="text-xs text-gray-500">{a.reason}</p>
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/teacher/student/${a.student_id}`)}
                  className="rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50"
                >
                  View & Assign
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
