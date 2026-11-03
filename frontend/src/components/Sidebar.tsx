import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/store/authStore';
import {
  LayoutDashboard, BookOpen, FileText, ClipboardList,
  Users, Cloud, LogOut, GraduationCap, FlaskConical,
} from 'lucide-react';

const studentLinks = [
  { to: '/student', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/student/notes', icon: BookOpen, label: 'Notes' },
  { to: '/student/assignments', icon: ClipboardList, label: 'Assignments' },
  { to: '/experiments', icon: Cloud, label: 'Cloud Lab' },
];

const teacherLinks = [
  { to: '/teacher', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/experiments', icon: FlaskConical, label: 'Experiments' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = user?.role === 'teacher' ? teacherLinks : studentLinks;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="flex w-64 flex-col bg-slate-900 text-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600">
          <GraduationCap size={22} />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">EduScale</h1>
          <p className="text-[11px] text-slate-400 leading-none">AI Learning Platform</p>
        </div>
      </div>

      {/* User */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-700/50">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-sm font-bold">
          {user?.full_name?.charAt(0) ?? '?'}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{user?.full_name}</p>
          <p className="truncate text-xs text-slate-400 capitalize">{user?.role}</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/student' || to === '/teacher'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="border-t border-slate-700 p-3">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-all"
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}

