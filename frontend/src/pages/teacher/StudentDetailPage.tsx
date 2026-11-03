import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as teacherApi from '@/api/teachers';
import type { StudentDetail, Course, AssignmentCreate } from '@/types';
import StatCard from '@/components/StatCard';
import MasteryBar from '@/components/MasteryBar';
import LoadingSpinner from '@/components/LoadingSpinner';
import { ArrowLeft, Trophy, CheckCircle2, BookOpen, ClipboardList, Plus, X, Send } from 'lucide-react';

export default function StudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<StudentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (!studentId) return;
    teacherApi.getStudentDetail(studentId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <LoadingSpinner size="lg" text="Loading student data..." />;
  if (!data) return <div className="text-center py-16 text-gray-500">Student not found</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <button onClick={() => navigate('/teacher')} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
        <ArrowLeft size={16} /> Back to Dashboard
      </button>

      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 text-2xl font-bold text-white">
          {data.student_name.charAt(0)}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{data.student_name}</h1>
          <p className="text-sm text-gray-500">{data.email}</p>
        </div>
        <div className="ml-auto">
          <button onClick={() => setShowForm(true)} className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:shadow-xl">
            <Plus size={16} /> Create Assignment
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Trophy} label="Overall Score" value={`${data.overall_score}%`} color="blue" />
        <StatCard icon={BookOpen} label="Questions" value={data.total_questions} color="green" />
        <StatCard icon={CheckCircle2} label="Correct" value={data.total_correct} color="purple" />
        <StatCard icon={ClipboardList} label="Quizzes" value={data.quizzes_completed} color="cyan" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Topic Mastery */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Topic Mastery</h2>
          <div className="space-y-4">
            {data.topic_mastery.map((t) => {
              const status = t.mastery_score >= 80 ? 'mastered' : t.mastery_score >= 50 ? 'working_towards' : t.questions_attempted > 0 ? 'needs_attention' : 'not_started';
              return <MasteryBar key={t.topic_id} score={t.mastery_score} label={t.topic_name} status={status} />;
            })}
          </div>
        </div>

        {/* Quiz History */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Recent Quiz History</h2>
          {data.quiz_history.length > 0 ? (
            <div className="space-y-2">
              {data.quiz_history.slice(0, 10).map((q) => (
                <div key={q.attempt_id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{q.quiz_title}</p>
                    <p className="text-xs text-gray-400">{new Date(q.date).toLocaleDateString()}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-bold ${q.score >= 70 ? 'text-emerald-600' : q.score >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                      {q.score}%
                    </span>
                    <p className="text-xs text-gray-400">{q.correct_answers}/{q.total_questions}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-gray-400">No quiz history</p>
          )}
        </div>
      </div>

      {/* Assignments */}
      {data.assignments.length > 0 && (
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Assignments</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {data.assignments.map((a) => (
              <div key={a.id} className="rounded-xl border border-gray-100 p-4">
                <div className="flex items-start justify-between">
                  <p className="text-sm font-medium text-gray-800">{a.title}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    a.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : a.status === 'overdue' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                  }`}>{a.status}</span>
                </div>
                {a.due_date && <p className="text-xs text-gray-400 mt-1">Due: {new Date(a.due_date).toLocaleDateString()}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assignment Form Modal */}
      {showForm && studentId && (
        <AssignmentModal studentId={studentId} onClose={() => setShowForm(false)} onCreated={() => { setShowForm(false); teacherApi.getStudentDetail(studentId).then(setData); }} />
      )}
    </div>
  );
}

function AssignmentModal({ studentId, onClose, onCreated }: { studentId: string; onClose: () => void; onCreated: () => void }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [topicId, setTopicId] = useState('');
  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState('beginner');
  const [count, setCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { teacherApi.getCourses().then(setCourses).catch(() => {}); }, []);

  const allTopics = courses.flatMap((c) => c.topics || []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topicId) return;
    setSubmitting(true);
    const topic = allTopics.find((t) => t.id === topicId);
    try {
      await teacherApi.createAssignment({
        student_id: studentId,
        topic_id: topicId,
        title: title || `Practice: ${topic?.name || 'Topic'}`,
        difficulty,
        question_count: count,
      });
      onCreated();
    } catch {
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">Create Assignment</h2>
          <button onClick={onClose} className="rounded-lg p-1 hover:bg-gray-100"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Topic</label>
            <select value={topicId} onChange={(e) => setTopicId(e.target.value)} required
              className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none">
              <option value="">Select a topic</option>
              {allTopics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Auto-generated if empty"
              className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none">
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Questions</label>
              <input type="number" value={count} onChange={(e) => setCount(+e.target.value)} min={1} max={20}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
          </div>
          <button type="submit" disabled={submitting || !topicId}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-3 text-sm font-semibold text-white shadow-lg disabled:opacity-60">
            <Send size={16} /> {submitting ? 'Creating...' : 'Create Assignment'}
          </button>
        </form>
      </div>
    </div>
  );
}
