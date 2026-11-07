import { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FileText,
  Github,
  Menu,
  MessagesSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  XCircle,
} from 'lucide-react'

const BRAND = 'Pathwise'
const REPO_URL = 'https://github.com/pranavh-57/Placement-and-Career-Assistant'
const DOCS_URL = `${REPO_URL}#readme`
const SIGN_IN = '#/signin'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'About', href: '#about' },
  { label: 'Documentation', href: DOCS_URL, external: true },
]

const FEATURES = [
  {
    icon: FileText,
    title: 'Resume analysis',
    text: 'Upload a PDF, DOCX or TXT. Skills, education, projects and experience are extracted into a profile you can edit.',
  },
  {
    icon: Search,
    title: 'Job search',
    text: 'Search live web listings when configured, or a built-in list, filtered by internship or full-time.',
  },
  {
    icon: Target,
    title: 'Match score & skill gaps',
    text: 'A 0–100 match score for any role, with matched and missing skills ranked by priority.',
  },
  {
    icon: BookOpen,
    title: 'Learning roadmap',
    text: 'A study plan for your gaps, grounded in a curated knowledge base of real resources.',
  },
  {
    icon: MessagesSquare,
    title: 'Interview prep',
    text: 'Role-specific questions with model answers, tailored to your skills and projects.',
  },
  {
    icon: ClipboardList,
    title: 'Application tracker',
    text: 'Save jobs and move them from Saved to Applied, Interview and Offer, with notes.',
  },
  {
    icon: CalendarDays,
    title: 'Placement calendar',
    text: 'Campus drives filtered by branch, CGPA, type and location, with eligibility checks and calendar export.',
  },
  {
    icon: Github,
    title: 'GitHub profile card',
    text: 'Turn your public repositories into skill evidence and add them to your profile.',
  },
  {
    icon: Sparkles,
    title: 'AI chat assistant',
    text: 'Ask in plain language. The assistant routes your question to the right agent or tool.',
  },
]

const STEPS = [
  {
    title: 'Upload your resume',
    text: 'The Resume Agent builds an editable profile from your file.',
  },
  { title: 'Pick a role', text: 'Search jobs, or choose a campus drive from the calendar.' },
  {
    title: 'See your match',
    text: 'Get a score, your matched skills and what is missing, in priority order.',
  },
  {
    title: 'Close the gaps',
    text: 'Follow a learning roadmap, then practise with role-specific interview questions.',
  },
]

const AGENTS = [
  ['Resume Agent', 'Extracts a structured profile from your resume.'],
  ['Job Matching Agent', 'Scores your profile against a job description.'],
  ['Skill Gap Agent', 'Ranks the skills you are missing by impact.'],
  ['Learning Agent', 'Builds a roadmap from retrieved learning resources.'],
  ['Interview Agent', 'Writes questions and model answers for a role.'],
  ['Orchestrator', 'Routes chat messages to the right agent or tool.'],
]

/** CSS custom properties aren't in React's CSSProperties type, so cast once here. */
const delay = (ms) => /** @type {import('react').CSSProperties} */ ({ '--d': `${ms}ms` })

/* ------------------------------------------------------------------ hooks */

function useInView(threshold = 0.2) {
  const ref = useRef(/** @type {HTMLDivElement | null} */ (null))
  // No IntersectionObserver (old browsers, test env): show everything immediately.
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === 'undefined')
  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setSeen(true)
          io.disconnect()
        }
      },
      { threshold },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [threshold])
  return { ref, seen }
}

function useCountUp(target, run, duration = 1400) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!run) return
    let raf
    const t0 = performance.now()
    const tick = (now) => {
      const p = Math.min((now - t0) / duration, 1)
      setValue(Math.round(target * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, run, duration])
  return value
}

function Reveal({ children, delay = 0, className = '' }) {
  const { ref, seen } = useInView()
  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`reveal ${seen ? 'reveal--in' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

/* ----------------------------------------------------------------- navbar */

function Logo() {
  return (
    <a href="#top" className="flex items-center gap-2">
      <span className="w-8 h-8 rounded-md bg-ink flex items-center justify-center">
        <span className="text-white font-display font-semibold text-sm">P</span>
      </span>
      <span className="font-display font-semibold text-[17px] tracking-tight">{BRAND}</span>
    </a>
  )
}

function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const linkProps = (l) =>
    l.external ? { target: '_blank', rel: 'noreferrer' } : { onClick: () => setOpen(false) }

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled || open
          ? 'bg-paper/80 backdrop-blur-md border-b border-hairline'
          : 'border-b border-transparent'
      }`}
    >
      <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Logo />

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              {...linkProps(l)}
              className="text-sm font-medium text-muted hover:text-ink transition-colors"
            >
              {l.label}
            </a>
          ))}
          <a href={SIGN_IN} className="btn-primary !px-4 !py-2">
            Sign in
          </a>
        </div>

        <button
          type="button"
          className="md:hidden p-2 -mr-2 text-ink"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      {open && (
        <div className="md:hidden px-6 pb-5 pt-1 flex flex-col gap-1">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              {...linkProps(l)}
              className="py-2.5 text-sm font-medium text-ink"
            >
              {l.label}
            </a>
          ))}
          <a href={SIGN_IN} className="btn-primary mt-2">
            Sign in
          </a>
        </div>
      )}
    </header>
  )
}

/* ------------------------------------------------------------ hero preview */

function Ring({ score, run }) {
  const r = 46
  const c = 2 * Math.PI * r
  const shown = useCountUp(score, run)
  return (
    <svg width="104" height="104" viewBox="0 0 120 120" aria-hidden="true">
      <circle cx="60" cy="60" r={r} fill="none" stroke="#E3E5E0" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={r}
        fill="none"
        stroke="#15803D"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={run ? c - (score / 100) * c : c}
        transform="rotate(-90 60 60)"
        style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(.2,.7,.2,1)' }}
      />
      <text
        x="60"
        y="67"
        textAnchor="middle"
        fontSize="28"
        fontWeight="600"
        fontFamily="Space Grotesk"
        fill="#161A1F"
      >
        {shown}
      </text>
    </svg>
  )
}

const LOG = [
  ['Orchestrator', 'Routed to: job_search'],
  ['Job Search (MCP)', 'Called search_jobs tool'],
  ['Job Matching Agent', 'Scored resume against job'],
  ['Skill Gap Agent', '2 gaps identified'],
]

function HeroPreview() {
  const { ref, seen } = useInView(0.25)
  return (
    <div ref={ref} className="relative animate-float">
      <div className="panel p-5 md:p-6 shadow-[0_24px_60px_-20px_rgba(36,81,184,0.25)]">
        <div className="flex items-center justify-between mb-4">
          <p className="eyebrow">Example · Backend Intern</p>
          <span className="flex items-center gap-1.5 text-[11px] font-mono text-muted">
            <span className="status-dot status-dot--active bg-signal-green" /> analyzing
          </span>
        </div>

        <div className="flex items-center gap-5">
          <Ring score={82} run={seen} />
          <div>
            <p className="eyebrow mb-1">Job Matching Agent</p>
            <p className="text-sm leading-relaxed">
              Strong overlap on the core stack. Containers and CI/CD are the main gaps.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-5">
          <div className="rounded-lg border border-hairline p-3">
            <p className="eyebrow mb-2 flex items-center gap-1.5">
              <CheckCircle2 size={12} className="text-signal-green" /> Matched
            </p>
            <div className="flex flex-wrap gap-1.5">
              {['Python', 'FastAPI', 'SQL'].map((s) => (
                <span
                  key={s}
                  className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-signal-green/10 text-signal-green border border-signal-green/20"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-hairline p-3">
            <p className="eyebrow mb-2 flex items-center gap-1.5">
              <XCircle size={12} className="text-signal-red" /> Missing
            </p>
            <div className="flex flex-wrap gap-1.5">
              {['Docker', 'CI/CD'].map((s) => (
                <span
                  key={s}
                  className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-signal-red/10 text-signal-red border border-signal-red/20"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5 pt-4 border-t border-hairline space-y-2">
          <p className="eyebrow">Agent activity</p>
          {LOG.map(([agent, action], i) => (
            <div
              key={agent}
              style={delay(700 + i * 450)}
              className={`flex items-center gap-2 text-xs ${seen ? 'hero-in' : 'opacity-0'}`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cobalt shrink-0" />
              <span className="font-medium">{agent}</span>
              <span className="text-muted truncate">{action}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11px] text-muted text-center mt-3">Illustrative example</p>
    </div>
  )
}

/* ---------------------------------------------------------------- sections */

function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pt-32 pb-20 md:pt-40 md:pb-28">
      <div className="absolute inset-0 -z-10 bg-grid" />
      <div className="absolute -z-10 -top-24 -left-24 w-[420px] h-[420px] rounded-full bg-cobalt/20 blur-3xl animate-drift" />
      <div className="absolute -z-10 top-40 -right-24 w-[380px] h-[380px] rounded-full bg-signal-green/10 blur-3xl animate-drift-slow" />

      <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-2 gap-14 items-center">
        <div>
          <p
            style={delay(0)}
            className="hero-in inline-flex items-center gap-2 chip bg-cobalt-light text-cobalt-dark"
          >
            <Sparkles size={13} /> Placement &amp; Career Assistant
          </p>
          <h1
            style={delay(100)}
            className="hero-in font-display text-4xl md:text-6xl font-semibold tracking-tight leading-[1.05] mt-5"
          >
            Walk into placement season with a <span className="text-shimmer">clear plan.</span>
          </h1>
          <p
            style={delay(220)}
            className="hero-in text-base md:text-lg text-muted leading-relaxed mt-6 max-w-lg"
          >
            Upload your resume, find roles, see exactly how well you match and which skills to learn
            first, then practise the interview. All in one place.
          </p>
          <div style={delay(340)} className="hero-in flex flex-wrap gap-3 mt-8">
            <a href={SIGN_IN} className="btn-primary !px-6 !py-3 group">
              Get started
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </a>
            <a href="#how-it-works" className="btn-secondary !px-6 !py-3">
              See how it works
            </a>
          </div>
        </div>

        <div style={delay(300)} className="hero-in">
          <HeroPreview />
        </div>
      </div>
    </section>
  )
}

function SectionHead({ eyebrow, title, text = '' }) {
  return (
    <Reveal className="max-w-2xl mb-12">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mt-2">
        {title}
      </h2>
      {text && <p className="text-muted leading-relaxed mt-4">{text}</p>}
    </Reveal>
  )
}

function FeatureCard({ icon: Icon, title, text }) {
  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--mx', `${e.clientX - rect.left}px`)
    e.currentTarget.style.setProperty('--my', `${e.clientY - rect.top}px`)
  }
  return (
    <div
      onMouseMove={onMove}
      className="spotlight panel p-6 h-full transition-all duration-300 hover:-translate-y-1 hover:border-cobalt/40"
    >
      <div className="relative">
        <div className="w-10 h-10 rounded-lg bg-cobalt-light text-cobalt-dark flex items-center justify-center">
          <Icon size={19} strokeWidth={2} />
        </div>
        <h3 className="font-display font-semibold text-lg mt-4">{title}</h3>
        <p className="text-sm text-muted leading-relaxed mt-2">{text}</p>
      </div>
    </div>
  )
}

function Features() {
  return (
    <section id="features" className="scroll-mt-20 py-20 md:py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHead
          eyebrow="Features"
          title="Everything between your resume and the offer."
          text={`${BRAND} covers the whole placement workflow, so you are not juggling spreadsheets, job boards and prep notes.`}
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 80}>
              <FeatureCard {...f} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="scroll-mt-20 py-20 md:py-24 bg-panel border-y border-hairline"
    >
      <div className="max-w-6xl mx-auto px-6">
        <SectionHead eyebrow="How it works" title="Four steps, in order." />
        <div className="grid md:grid-cols-4 gap-4">
          {STEPS.map((s, i) => (
            <Reveal key={s.title} delay={i * 110}>
              <div className="relative h-full rounded-lg border border-hairline bg-paper p-6 transition-transform duration-300 hover:-translate-y-1">
                <span className="font-display text-5xl font-semibold text-cobalt/20 leading-none">
                  {i + 1}
                </span>
                <h3 className="font-display font-semibold text-lg mt-3">{s.title}</h3>
                <p className="text-sm text-muted leading-relaxed mt-2">{s.text}</p>
                {i < STEPS.length - 1 && (
                  <ArrowRight
                    size={18}
                    className="hidden md:block absolute -right-[19px] top-1/2 -translate-y-1/2 text-cobalt z-10 bg-panel rounded-full"
                  />
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function About() {
  return (
    <section id="about" className="scroll-mt-20 py-20 md:py-24">
      <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-2 gap-12">
        <Reveal>
          <p className="eyebrow">About</p>
          <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mt-2">
            Built from cooperating AI agents.
          </h2>
          <p className="text-muted leading-relaxed mt-4">
            {BRAND} is made for college students preparing for placements. Instead of one
            general-purpose chatbot, each step is handled by a focused agent. Answers are grounded
            in a curated knowledge base (RAG), and external lookups such as job search and GitHub
            analysis run as separate MCP tool servers.
          </p>

          <div className="panel p-5 mt-8 flex gap-4">
            <div className="w-10 h-10 rounded-lg bg-signal-green/10 text-signal-green flex items-center justify-center shrink-0">
              <ShieldCheck size={19} />
            </div>
            <div>
              <h3 className="font-display font-semibold">Your data stays yours</h3>
              <p className="text-sm text-muted leading-relaxed mt-1">
                Accounts are verified with a one-time email code, your resume data is private to
                your account, and one click deletes your resume data and history.
              </p>
            </div>
          </div>
        </Reveal>

        <div className="grid sm:grid-cols-2 gap-3 content-start">
          {AGENTS.map(([name, text], i) => (
            <Reveal key={name} delay={i * 70}>
              <div className="panel p-4 h-full transition-colors hover:border-ink">
                <p className="font-mono text-xs text-cobalt-dark">{name}</p>
                <p className="text-sm text-muted leading-snug mt-1.5">{text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="px-6 pb-20 md:pb-24">
      <Reveal>
        <div className="relative max-w-6xl mx-auto overflow-hidden rounded-2xl bg-ink text-white px-8 py-14 md:py-16 text-center">
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[520px] h-[260px] rounded-full bg-cobalt/50 blur-3xl animate-drift" />
          <div className="relative">
            <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight">
              Start mapping your path.
            </h2>
            <p className="text-white/70 mt-3 max-w-md mx-auto">
              Create an account, upload your resume and get your first match score in minutes.
            </p>
            <a
              href={SIGN_IN}
              className="inline-flex items-center gap-2 mt-8 rounded-md bg-white text-ink text-sm font-medium px-6 py-3 hover:bg-cobalt-light transition-colors group"
            >
              Get started
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </a>
          </div>
        </div>
      </Reveal>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-hairline">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <Logo />
        <div className="flex items-center gap-6 text-sm text-muted">
          <a href={DOCS_URL} target="_blank" rel="noreferrer" className="hover:text-ink">
            Documentation
          </a>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-ink">
            GitHub
          </a>
          <a href={SIGN_IN} className="hover:text-ink">
            Sign in
          </a>
        </div>
        <p className="text-xs text-muted">
          © {new Date().getFullYear()} {BRAND}
        </p>
      </div>
    </footer>
  )
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <About />
        <FinalCta />
      </main>
      <Footer />
    </div>
  )
}
