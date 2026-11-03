import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as studentApi from '@/api/students';
import type { AttemptResult } from '@/types';
import LoadingSpinner from '@/components/LoadingSpinner';
import { CheckCircle2, XCircle, ArrowLeft, RotateCcw, Trophy } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

export default function ResultsPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!attemptId) return;
    studentApi.getAttemptResults(attemptId)
      .then(setResult)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [attemptId]);

  if (loading) return <LoadingSpinner size="lg" text="Loading results..." />;
  if (!result) return <div className="text-center py-16 text-gray-500">Results not found</div>;

  const pct = result.score;
  const passed = pct >= 60;
  const pieData = [
    { name: 'Correct', value: result.correct_answers },
    { name: 'Incorrect', value: result.total_questions - result.correct_answers },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Score banner */}
      <div className={`rounded-2xl p-8 text-center ${passed ? 'bg-gradient-to-br from-emerald-500 to-teal-600' : 'bg-gradient-to-br from-orange-500 to-red-500'} text-white shadow-lg`}>
        <Trophy size={40} className="mx-auto mb-3 opacity-80" />
        <h1 className="text-4xl font-bold">{pct.toFixed(1)}%</h1>
        <p className="mt-1 text-lg font-medium opacity-90">{result.quiz_title}</p>
        <p className="mt-2 text-sm opacity-75">
          {result.correct_answers} correct out of {result.total_questions} questions
        </p>
        <div className="mt-4 inline-flex rounded-full bg-white/20 px-4 py-1.5 text-sm font-semibold">
          {passed ? '✅ Passed' : '📚 Keep Practicing'}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Pie chart */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Score Breakdown</h2>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={70} paddingAngle={4} dataKey="value">
                <Cell fill="#10b981" />
                <Cell fill="#ef4444" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 text-sm">
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-emerald-500" /> {result.correct_answers} Correct</span>
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-red-500" /> {result.total_questions - result.correct_answers} Wrong</span>
          </div>
        </div>

        {/* Recommendations */}
        <div className="lg:col-span-2 rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Recommendations</h2>
          {result.recommendations && result.recommendations.length > 0 ? (
            <ul className="space-y-2">
              {result.recommendations.map((r, i) => (
                <li key={i} className="flex items-start gap-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
                  <span className="mt-0.5">💡</span> {r}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No specific recommendations.</p>
          )}
        </div>
      </div>

      {/* Question review */}
      <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Question Review</h2>
        <div className="space-y-4">
          {result.responses.map((r, i) => (
            <div key={r.question_id} className={`rounded-xl border-2 p-5 ${r.is_correct ? 'border-emerald-200 bg-emerald-50/30' : 'border-red-200 bg-red-50/30'}`}>
              <div className="flex items-start gap-3">
                <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${r.is_correct ? 'bg-emerald-500' : 'bg-red-500'} text-white`}>
                  {r.is_correct ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800 text-sm">Q{i + 1}. {r.question_text}</p>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                    <span className={`rounded-full px-2.5 py-1 font-medium ${r.is_correct ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      Your answer: {r.submitted_answer}
                    </span>
                    {!r.is_correct && (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-medium text-emerald-700">
                        Correct: {r.correct_answer}
                      </span>
                    )}
                  </div>
                  {r.explanation && (
                    <p className="mt-2 rounded-lg bg-white p-3 text-xs text-gray-600 border border-gray-100">
                      💡 {r.explanation}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button onClick={() => navigate('/student')} className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50">
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl">
          <RotateCcw size={16} /> Try Again
        </button>
      </div>
    </div>
  );
}
