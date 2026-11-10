import { friendlyError } from '../utils/errors.js'

/** @param {{ title: string, sub?: string, children?: import('react').ReactNode }} props */
export function PageHeader({ title, sub, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <div className="eyebrow">Admin</div>
        <h1 className="font-display text-2xl text-ink">{title}</h1>
        {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
      </div>
      <div className="flex gap-2">{children}</div>
    </div>
  )
}

/** @param {{ label: string, value?: any, hint?: string, tone?: string }} props */
export function Kpi({ label, value, hint, tone }) {
  const color = tone === 'bad' ? 'text-red-700' : tone === 'good' ? 'text-green-700' : 'text-ink'
  return (
    <div className="panel p-4">
      <div className="eyebrow">{label}</div>
      <div className={`mt-2 font-display text-3xl ${color}`}>{value ?? '—'}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  )
}

const PILL = {
  active: 'bg-green-100 text-green-800',
  success: 'bg-green-100 text-green-800',
  healthy: 'bg-green-100 text-green-800',
  suspended: 'bg-amber-100 text-amber-800',
  degraded: 'bg-amber-100 text-amber-800',
  deactivated: 'bg-gray-200 text-gray-700',
  closed: 'bg-gray-200 text-gray-700',
  expired: 'bg-gray-200 text-gray-700',
  unknown: 'bg-gray-200 text-gray-700',
  failed: 'bg-red-100 text-red-800',
}
export const Pill = ({ value }) => (
  <span className={`rounded px-2 py-0.5 text-xs font-medium ${PILL[value] || PILL.unknown}`}>
    {value ?? 'n/a'}
  </span>
)

function Empty({ children = 'Nothing here yet.' }) {
  return <div className="p-8 text-center text-sm text-muted">{children}</div>
}

export function ErrorNote({ error }) {
  if (!error) return null
  return (
    <div role="alert" className="panel mb-4 border-red-300 p-3 text-sm text-red-800">
      {friendlyError(error)}
    </div>
  )
}

/** Dependency-free SVG line chart. data: [{date, count}] */
export function LineChart({ data, height = 140 }) {
  if (!data?.length) return <Empty>No data</Empty>
  const w = 600
  const max = Math.max(1, ...data.map((d) => d.count))
  const x = (i) => (i / Math.max(1, data.length - 1)) * (w - 20) + 10
  const y = (v) => height - 20 - (v / max) * (height - 40)
  const pts = data.map((d, i) => `${x(i)},${y(d.count)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" role="img" aria-label="Trend over time">
      <line x1="10" x2={w - 10} y1={height - 20} y2={height - 20} stroke="#D9DCD5" />
      <polyline fill="none" stroke="#2451B8" strokeWidth="2" points={pts} />
      {data.map((d, i) => (
        <circle key={d.date} cx={x(i)} cy={y(d.count)} r="2.5" fill="#2451B8">
          <title>{`${d.date}: ${d.count}`}</title>
        </circle>
      ))}
      <text x="10" y={height - 4} fontSize="10" fill="#6B7280">
        {data[0].date}
      </text>
      <text x={w - 10} y={height - 4} fontSize="10" fill="#6B7280" textAnchor="end">
        {data[data.length - 1].date}
      </text>
      <text x="10" y="12" fontSize="10" fill="#6B7280">
        max {max}
      </text>
    </svg>
  )
}

/** Horizontal bars. data: [{label, value}] */
export function BarList({ data }) {
  if (!data?.length) return <Empty>No data</Empty>
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <ul className="space-y-2">
      {data.map((d) => (
        <li key={d.label} className="text-sm">
          <div className="flex justify-between">
            <span className="text-ink">{d.label}</span>
            <span className="font-mono text-muted">{d.value}</span>
          </div>
          <div className="mt-1 h-2 rounded bg-hairline">
            <div className="h-2 rounded bg-cobalt" style={{ width: `${(d.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

/** @param {{ cols: any[], rows?: any[], empty?: string, onRow?: (row: any) => void }} props */
export function Table({ cols, rows, empty, onRow }) {
  if (!rows?.length) return <Empty>{empty}</Empty>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-hairline">
            {cols.map((c) => (
              <th key={c.key} className="eyebrow px-3 py-2 font-normal">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.id ?? i}
              onClick={onRow ? () => onRow(r) : undefined}
              className={`border-b border-hairline ${onRow ? 'cursor-pointer hover:bg-paper' : ''}`}
            >
              {cols.map((c) => (
                <td key={c.key} className="px-3 py-2 align-top">
                  {c.render ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
