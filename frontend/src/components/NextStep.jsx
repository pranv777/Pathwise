import { ArrowRight, CheckCircle2 } from 'lucide-react'

export default function NextStep({ done, next, onClick }) {
  return (
    <div className="panel mt-6 px-5 py-4 flex items-center justify-between gap-4">
      <span className="flex items-center gap-2 text-sm">
        <CheckCircle2 size={16} className="text-signal-green shrink-0" />
        {done}
      </span>
      <button
        onClick={onClick}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-cobalt text-white text-sm font-medium hover:opacity-90"
      >
        {next}
        <ArrowRight size={14} />
      </button>
    </div>
  )
}
