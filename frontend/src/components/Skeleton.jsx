const DEFAULT_NOTE =
  'Still working… if the server was idle, the first request can take up to a minute.'

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded bg-hairline/70 ${className}`} />
}

export function PanelSkeleton({ lines = 4, note = DEFAULT_NOTE }) {
  return (
    <div className="panel p-6 space-y-3" role="status" aria-live="polite">
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={`h-4 ${i % 2 ? 'w-5/6' : 'w-full'}`} />
      ))}
      <p className="text-xs text-muted pt-2">{note}</p>
    </div>
  )
}
