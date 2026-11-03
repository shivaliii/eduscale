import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import * as studentApi from '@/api/students';
import type { Note } from '@/types';
import LoadingSpinner from '@/components/LoadingSpinner';
import { BookOpen, CheckCircle2, ChevronDown, ChevronRight, Code, AlertTriangle, Lightbulb, ListChecks, Play } from 'lucide-react';

export default function NotesPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  const topicFilter = searchParams.get('topic');

  useEffect(() => {
    studentApi.getNotes(undefined, topicFilter || undefined)
      .then(setNotes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [topicFilter]);

  const topics = [...new Set(notes.map((n) => n.topic_name).filter(Boolean))] as string[];
  const filtered = filter === 'all' ? notes : notes.filter((n) => n.topic_name === filter);

  const handleComplete = async (noteId: string) => {
    await studentApi.completeNote(noteId);
    setNotes((prev) => prev.map((n) => n.id === noteId ? { ...n, is_completed: true } : n));
    if (selectedNote?.id === noteId) setSelectedNote({ ...selectedNote, is_completed: true });
  };

  if (loading) return <LoadingSpinner size="lg" text="Loading notes..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BookOpen size={24} className="text-emerald-500" /> Important Notes
          </h1>
          <p className="text-gray-500 text-sm">Study materials for your topics</p>
        </div>
      </div>

      {/* Topic filter */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setFilter('all')} className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
          All Topics
        </button>
        {topics.map((t) => (
          <button key={t} onClick={() => setFilter(t)} className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${filter === t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {t}
          </button>
        ))}
      </div>

      {selectedNote ? (
        <NoteDetail note={selectedNote} onBack={() => setSelectedNote(null)} onComplete={handleComplete} navigate={navigate} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((n) => (
            <button key={n.id} onClick={() => setSelectedNote(n)} className="rounded-2xl bg-white p-5 shadow-sm border border-gray-100 text-left hover:shadow-md hover:border-blue-200 transition-all group">
              <div className="flex items-start justify-between mb-3">
                <span className="inline-flex items-center rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700">{n.topic_name}</span>
                {n.is_completed && <CheckCircle2 size={18} className="text-emerald-500" />}
              </div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{n.title}</h3>
              <p className="text-xs text-gray-500 line-clamp-2">{n.summary}</p>
              <div className="mt-3 flex items-center text-xs text-blue-500 font-medium group-hover:text-blue-700">
                Read more <ChevronRight size={14} className="ml-1" />
              </div>
            </button>
          ))}
          {filtered.length === 0 && <p className="col-span-full text-center py-12 text-gray-400">No notes found</p>}
        </div>
      )}
    </div>
  );
}

function NoteDetail({ note, onBack, onComplete, navigate }: { note: Note; onBack: () => void; onComplete: (id: string) => void; navigate: any }) {
  const c = note.content;
  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
        ← Back to Notes
      </button>

      <div className="rounded-2xl bg-white p-8 shadow-sm border border-gray-100">
        <div className="flex items-start justify-between mb-4">
          <div>
            <span className="inline-flex items-center rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700 mb-2">{note.topic_name}</span>
            <h1 className="text-xl font-bold text-gray-900">{note.title}</h1>
            <p className="text-sm text-gray-500 mt-1">{note.summary}</p>
          </div>
          {!note.is_completed && (
            <button onClick={() => onComplete(note.id)} className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600">
              <CheckCircle2 size={16} className="inline mr-1" /> Mark Complete
            </button>
          )}
          {note.is_completed && (
            <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700">
              <CheckCircle2 size={16} /> Completed
            </span>
          )}
        </div>

        {/* Definitions */}
        {c.definitions && c.definitions.length > 0 && (
          <Section icon={BookOpen} title="Key Definitions" color="blue">
            <ul className="space-y-2">
              {c.definitions.map((d, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                  {d}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Key Concepts */}
        {c.key_concepts && c.key_concepts.length > 0 && (
          <Section icon={Lightbulb} title="Key Concepts" color="amber">
            <ul className="space-y-2">
              {c.key_concepts.map((k, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                  {k}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Examples */}
        {c.examples && c.examples.length > 0 && (
          <Section icon={Code} title="Examples" color="emerald">
            {c.examples.map((ex, i) => (
              <div key={i} className="mb-4 rounded-xl border border-gray-200 overflow-hidden">
                <pre className="bg-gray-900 p-4 text-sm text-green-400 font-mono overflow-x-auto">{ex.code}</pre>
                {ex.output && (
                  <div className="bg-gray-800 px-4 py-2 text-xs text-gray-300 font-mono border-t border-gray-700">
                    Output: {ex.output}
                  </div>
                )}
                {ex.explanation && (
                  <div className="bg-white px-4 py-3 text-sm text-gray-600">{ex.explanation}</div>
                )}
              </div>
            ))}
          </Section>
        )}

        {/* Common Mistakes */}
        {c.common_mistakes && c.common_mistakes.length > 0 && (
          <Section icon={AlertTriangle} title="Common Mistakes" color="red">
            <ul className="space-y-2">
              {c.common_mistakes.map((m, i) => (
                <li key={i} className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800">
                  <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {m}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Revision Checklist */}
        {c.revision_checklist && c.revision_checklist.length > 0 && (
          <Section icon={ListChecks} title="Revision Checklist" color="violet">
            <ul className="space-y-2">
              {c.revision_checklist.map((r, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-violet-600" />
                  {r}
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      {/* Practice button */}
      <button
        onClick={() => navigate(`/student?practice_topic=${note.topic_id}`)}
        className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl"
      >
        <Play size={16} /> Practice This Topic
      </button>
    </div>
  );
}

function Section({ icon: Icon, title, color, children }: { icon: any; title: string; color: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  const colorMap: Record<string, string> = { blue: 'text-blue-600', amber: 'text-amber-600', emerald: 'text-emerald-600', red: 'text-red-600', violet: 'text-violet-600' };
  return (
    <div className="mt-6">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 text-left">
        <Icon size={18} className={colorMap[color] || 'text-gray-600'} />
        <h3 className="text-base font-semibold text-gray-900 flex-1">{title}</h3>
        {open ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
      </button>
      {open && <div className="mt-3 pl-7">{children}</div>}
    </div>
  );
}
