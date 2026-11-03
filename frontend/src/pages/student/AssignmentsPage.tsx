import { useState, useEffect } from 'react';
import * as studentApi from '@/api/students';
import type { Assignment } from '@/types';
import LoadingSpinner from '@/components/LoadingSpinner';
import { ClipboardList, Calendar, BookOpen, AlertCircle } from 'lucide-react';

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    studentApi.getAssignments()
      .then(setAssignments)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner size="lg" text="Loading assignments..." />;

  const statusColors: Record<string, { bg: string; text: string }> = {
    pending: { bg: 'bg-amber-50', text: 'text-amber-700' },
    in_progress: { bg: 'bg-blue-50', text: 'text-blue-700' },
    completed: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
    overdue: { bg: 'bg-red-50', text: 'text-red-700' },
  };

  const diffColors: Record<string, string> = {
    beginner: 'bg-emerald-100 text-emerald-700',
    intermediate: 'bg-amber-100 text-amber-700',
    advanced: 'bg-red-100 text-red-700',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ClipboardList size={24} className="text-blue-500" /> Assignments
        </h1>
        <p className="text-gray-500 text-sm">Practice assignments from your teacher</p>
      </div>

      {assignments.length === 0 ? (
        <div className="rounded-2xl bg-white p-16 text-center shadow-sm border border-gray-100">
          <ClipboardList size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">No assignments yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {assignments.map((a) => {
            const sc = statusColors[a.status] || statusColors.pending;
            const dc = diffColors[a.difficulty] || diffColors.beginner;
            const due = a.due_date ? new Date(a.due_date) : null;
            const overdue = due && due < new Date() && a.status !== 'completed';

            return (
              <div key={a.id} className={`rounded-2xl bg-white p-6 shadow-sm border ${overdue ? 'border-red-200' : 'border-gray-100'} hover:shadow-md transition-shadow`}>
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">{a.title}</h3>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${sc.bg} ${sc.text}`}>
                    {a.status.replace('_', ' ')}
                  </span>
                </div>
                {a.description && <p className="text-sm text-gray-500 mb-3">{a.description}</p>}
                <div className="flex flex-wrap gap-2 text-xs">
                  {a.topic_name && (
                    <span className="flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-violet-700">
                      <BookOpen size={12} /> {a.topic_name}
                    </span>
                  )}
                  <span className={`rounded-full px-2.5 py-1 font-medium ${dc}`}>{a.difficulty}</span>
                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">{a.question_count} questions</span>
                  {due && (
                    <span className={`flex items-center gap-1 rounded-full px-2.5 py-1 ${overdue ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                      <Calendar size={12} />
                      {overdue && <AlertCircle size={12} />}
                      {due.toLocaleDateString()}
                    </span>
                  )}
                </div>
                {a.score !== null && a.score !== undefined && (
                  <div className="mt-3 text-sm font-medium text-emerald-600">Score: {a.score}%</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
