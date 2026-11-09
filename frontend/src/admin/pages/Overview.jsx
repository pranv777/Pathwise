import { adminApi } from '../adminApi'
import { BarList, ErrorNote, Kpi, LineChart, PageHeader, useLoad } from '../ui'

export default function Overview() {
  const { data, error, loading } = useLoad(() => adminApi.overview(14))
  const s = data?.stats
  return (
    <>
      <PageHeader title="Overview" sub="Platform health at a glance (last 14 days for charts)." />
      <ErrorNote error={error} />
      {loading && !data && <div className="text-sm text-muted">Loading…</div>}
      {s && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="Students" value={s.students} hint={`${s.active_students} active in 30d`} />
            <Kpi label="Resumes parsed" value={s.resumes} />
            <Kpi label="Active drives" value={s.active_drives} />
            <Kpi label="Saved jobs" value={s.saved_jobs} />
            <Kpi label="AI interactions" value={s.ai_interactions} />
            <Kpi
              label="Agent success rate"
              value={s.agent_success_rate == null ? '—' : `${s.agent_success_rate}%`}
              tone={s.agent_success_rate != null && s.agent_success_rate < 90 ? 'bad' : 'good'}
            />
            <Kpi
              label="Agent failures"
              value={s.agent_failures}
              tone={s.agent_failures ? 'bad' : undefined}
            />
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <section className="panel p-4">
              <div className="eyebrow mb-2">Student registrations</div>
              <LineChart data={data.registrations} />
            </section>
            <section className="panel p-4">
              <div className="eyebrow mb-2">AI agent activity</div>
              <LineChart data={data.activity} />
            </section>
            <section className="panel p-4">
              <div className="eyebrow mb-3">Most used agents</div>
              <BarList data={data.agent_usage.map((a) => ({ label: a.name, value: a.count }))} />
            </section>
            <section className="panel p-4">
              <div className="eyebrow mb-3">Placement progress (saved jobs by stage)</div>
              <BarList
                data={data.placement_pipeline.map((a) => ({ label: a.status, value: a.count }))}
              />
            </section>
          </div>
        </>
      )}
    </>
  )
}
