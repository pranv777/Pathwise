import { useEffect, useState } from 'react'
import {
  Activity,
  BookOpen,
  Briefcase,
  Cpu,
  LayoutDashboard,
  ScrollText,
  Plug,
  Users,
} from 'lucide-react'
import Overview from './pages/Overview'
import Students from './pages/Students'
import Drives from './pages/Drives'
import Agents from './pages/Agents'
import KnowledgeBase from './pages/KnowledgeBase'
import { Mcp, Audit } from './pages/McpAndAudit'

const NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, el: Overview },
  { id: 'students', label: 'Students', icon: Users, el: Students },
  { id: 'drives', label: 'Campus drives', icon: Briefcase, el: Drives },
  { id: 'agents', label: 'AI agents', icon: Cpu, el: Agents },
  { id: 'kb', label: 'Knowledge base', icon: BookOpen, el: KnowledgeBase },
  { id: 'mcp', label: 'MCP tools', icon: Plug, el: Mcp },
  { id: 'audit', label: 'Audit log', icon: ScrollText, el: Audit },
]

// Hash routes: #/admin, #/admin/students, ...
const current = () => {
  const m = window.location.hash.match(/^#\/admin\/?([\w-]*)/)
  return NAV.find((n) => n.id === (m?.[1] || 'overview')) || NAV[0]
}

export default function AdminApp() {
  const [page, setPage] = useState(current)
  useEffect(() => {
    const on = () => setPage(current())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const Page = page.el

  return (
    <div className="flex min-h-screen bg-paper text-ink">
      <nav
        aria-label="Admin"
        className="hidden w-56 shrink-0 border-r border-hairline bg-panel p-4 md:block"
      >
        <a href="#/" className="mb-6 flex items-center gap-2 font-display text-lg">
          <Activity size={18} className="text-cobalt" /> Pathwise
          <span className="chip ml-1">Admin</span>
        </a>
        <ul className="space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <a
                href={`#/admin/${id}`}
                aria-current={page.id === id ? 'page' : undefined}
                className={`flex items-center gap-2 rounded px-3 py-2 text-sm ${
                  page.id === id ? 'bg-paper font-medium text-cobalt' : 'text-muted hover:bg-paper'
                }`}
              >
                <Icon size={16} /> {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <main className="min-w-0 flex-1 p-4 md:p-8">
        <div className="mb-4 flex gap-1 overflow-x-auto md:hidden">
          {NAV.map((n) => (
            <a
              key={n.id}
              href={`#/admin/${n.id}`}
              className={`chip whitespace-nowrap ${page.id === n.id ? 'text-cobalt' : ''}`}
            >
              {n.label}
            </a>
          ))}
        </div>
        <Page />
      </main>
    </div>
  )
}
