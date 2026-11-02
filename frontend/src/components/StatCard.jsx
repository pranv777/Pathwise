export default function StatCard({ icon: Icon, label, value, tone = 'cobalt', onClick }) {
  const toneStyles = {
    cobalt: 'bg-cobalt-light text-cobalt-dark',
    green: 'bg-signal-green/10 text-signal-green',
    amber: 'bg-signal-amber/10 text-signal-amber',
    red: 'bg-signal-red/10 text-signal-red',
  }
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`panel p-5 text-left ${onClick ? 'hover:border-ink transition-colors cursor-pointer' : 'cursor-default'}`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${toneStyles[tone]}`}>
        <Icon size={17} strokeWidth={2} />
      </div>
      <p className="font-display text-2xl font-semibold mt-3 leading-none">{value}</p>
      <p className="text-xs text-muted mt-1">{label}</p>
    </button>
  )
}
