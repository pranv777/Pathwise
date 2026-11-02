import {
  LayoutGrid,
  Search,
  Target,
  BookOpen,
  MessagesSquare,
  History,
  LogOut,
  ClipboardList,
  CalendarDays,
} from 'lucide-react'

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  {
    id: 'jobs',
    label: 'Job Search',
    icon: Search,
    requires: 'profile',
    hint: 'Upload your resume first',
  },
  { id: 'calendar', label: 'Placement Calendar', icon: CalendarDays },
  { id: 'tracker', label: 'Application Tracker', icon: ClipboardList },
  {
    id: 'match',
    label: 'Match & Skill Gap',
    icon: Target,
    requires: 'job',
    hint: 'Select a job first',
  },
  {
    id: 'learning',
    label: 'Learning Roadmap',
    icon: BookOpen,
    requires: 'match',
    hint: 'Run a match analysis first',
  },
  {
    id: 'interview',
    label: 'Interview Prep',
    icon: MessagesSquare,
    requires: 'profile',
    hint: 'Upload your resume first',
  },
  { id: 'history', label: 'History', icon: History },
]

function Avatar({ user }) {
  if (user.picture) {
    return <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full shrink-0" />
  }
  const initials = (user.name || user.email || '?').charAt(0).toUpperCase()
  return (
    <div className="w-8 h-8 rounded-full bg-cobalt-light text-cobalt-dark flex items-center justify-center text-xs font-semibold shrink-0">
      {initials}
    </div>
  )
}

export default function Sidebar({ active, onChange, user, onLogout, ready = {} }) {
  return (
    <aside className="w-60 shrink-0 border-r border-hairline bg-panel flex flex-col">
      <div className="px-5 py-6 border-b border-hairline border-t-[3px] border-t-cobalt">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-ink flex items-center justify-center">
            <span className="text-white font-display font-semibold text-sm">W</span>
          </div>
          <span className="font-display font-semibold text-[15px] tracking-tight">Wayfind</span>
        </div>
        <p className="eyebrow mt-2">Placement &amp; Career Assistant</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          const locked = item.requires && !ready[item.requires]
          return (
            <button
              key={item.id}
              onClick={() => !locked && onChange(item.id)}
              disabled={locked}
              title={locked ? item.hint : undefined}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors
                ${
                  locked
                    ? 'text-muted/50 cursor-not-allowed'
                    : isActive
                      ? 'bg-cobalt-light text-cobalt-dark'
                      : 'text-muted hover:bg-paper hover:text-ink'
                }`}
            >
              <Icon size={16} strokeWidth={2} />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="px-4 py-4 border-t border-hairline flex items-center gap-2.5">
        <Avatar user={user} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate leading-tight">{user.name}</p>
          <p className="text-xs text-muted truncate">{user.email}</p>
        </div>
        <button
          onClick={onLogout}
          className="text-muted hover:text-signal-red shrink-0"
          title="Log out"
        >
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  )
}
