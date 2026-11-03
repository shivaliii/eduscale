import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as studentApi from '@/api/students';
import type { AttemptStart, Question } from '@/types';
import LoadingSpinner from '@/components/LoadingSpinner';
import { CheckCircle2, XCircle, Clock, ChevronRight, Send, AlertCircle } from 'lucide-react';

export default function QuizPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<AttemptStart | null>(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ correct: boolean; answer: string } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    if (!quizId) return;
    studentApi.startQuiz(quizId)
      .then((data) => { setAttempt(data); setLoading(false); })
      .catch((e) => { setError(e.response?.data?.detail || 'Failed to start quiz'); setLoading(false); });
  }, [quizId]);

  // Timer
  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  if (loading) return <LoadingSpinner size="lg" text="Preparing quiz..." />;
  if (error) return <div className="rounded-2xl bg-red-50 p-6 text-red-700"><AlertCircle className="inline mr-2" size={18}/>{error}</div>;
  if (!attempt) return null;

  const questions = attempt.questions;
  const question = questions[currentIdx];
  const totalQ = questions.length;
  const progress = ((currentIdx + (feedback ? 1 : 0)) / totalQ) * 100;
  const timeLimit = attempt.quiz.time_limit_minutes;
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;

  const handleSelect = async (key: string) => {
    if (feedback || submitting) return;
    setSelected(key);
    setSubmitting(true);
    try {
      const res = await studentApi.submitResponse(attempt.attempt_id, question.id, key, elapsed);
      setFeedback({ correct: res.is_correct, answer: key });
      setAnswers((prev) => ({ ...prev, [question.id]: key }));
    } catch {
      setError('Failed to submit answer');
    }
    setSubmitting(false);
  };

  const handleNext = async () => {
    if (currentIdx < totalQ - 1) {
      setCurrentIdx((i) => i + 1);
      setSelected(null);
      setFeedback(null);
    } else {
      // Submit attempt
      setSubmitting(true);
      try {
        const result = await studentApi.submitAttempt(attempt.attempt_id);
        navigate(`/student/results/${attempt.attempt_id}`, { replace: true });
      } catch {
        setError('Failed to submit quiz');
      }
      setSubmitting(false);
    }
  };

  const optionKeys = question.options ? Object.keys(question.options).sort() : [];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{attempt.quiz.title}</h1>
          <p className="text-sm text-gray-500">Question {currentIdx + 1} of {totalQ}</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Clock size={16} />
          <span className="font-mono">{mins.toString().padStart(2, '0')}:{secs.toString().padStart(2, '0')}</span>
          {timeLimit && <span className="text-gray-400">/ {timeLimit}m</span>}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>

      {/* Question card */}
      <div className="rounded-2xl bg-white p-8 shadow-sm border border-gray-100">
        <div className="mb-2 inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
          {question.difficulty} · {question.question_type.replace('_', ' ')}
        </div>
        <h2 className="text-lg font-semibold text-gray-900 mt-2 mb-6">{question.question_text}</h2>

        {question.code_snippet && (
          <pre className="mb-6 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-green-400 font-mono">{question.code_snippet}</pre>
        )}

        {/* Options */}
        <div className="space-y-3">
          {optionKeys.map((key) => {
            const isSelected = selected === key;
            const isCorrect = feedback && feedback.correct && feedback.answer === key;
            const isWrong = feedback && !feedback.correct && feedback.answer === key;
            let style = 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/50';
            if (isCorrect) style = 'border-emerald-500 bg-emerald-50 ring-2 ring-emerald-200';
            else if (isWrong) style = 'border-red-500 bg-red-50 ring-2 ring-red-200';
            else if (isSelected && !feedback) style = 'border-blue-500 bg-blue-50 ring-2 ring-blue-200';

            return (
              <button
                key={key}
                onClick={() => handleSelect(key)}
                disabled={!!feedback}
                className={`flex w-full items-center gap-4 rounded-xl border-2 p-4 text-left transition-all ${style}`}
              >
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
                  isCorrect ? 'bg-emerald-500 text-white' : isWrong ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-600'
                }`}>
                  {key}
                </span>
                <span className="text-sm text-gray-800">{question.options![key]}</span>
                {isCorrect && <CheckCircle2 size={20} className="ml-auto text-emerald-500" />}
                {isWrong && <XCircle size={20} className="ml-auto text-red-500" />}
              </button>
            );
          })}
        </div>

        {/* Feedback */}
        {feedback && (
          <div className={`mt-6 rounded-lg p-4 text-sm ${feedback.correct ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}>
            {feedback.correct ? '✅ Correct!' : '❌ Incorrect'}
          </div>
        )}
      </div>

      {/* Navigation */}
      {feedback && (
        <div className="flex justify-end">
          <button
            onClick={handleNext}
            disabled={submitting}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl transition-all disabled:opacity-60"
          >
            {submitting ? 'Submitting...' : currentIdx < totalQ - 1 ? (
              <>Next <ChevronRight size={16} /></>
            ) : (
              <>Submit Quiz <Send size={16} /></>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
