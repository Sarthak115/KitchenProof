import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EvidencePlayer, type EvidencePlayerHandle } from '../../components/EvidencePlayer'
import { FindingRow } from '../../components/FindingRow'
import { IntegrityChip } from '../../components/IntegrityChip'
import { ScoreBadge } from '../../components/ScoreBadge'
import { api } from '../../lib/api'
import { FLAG_LABELS } from '../../lib/checks'
import { useLive } from '../../lib/hooks'
import { fmtDateTime } from '../../lib/time'
import { sortFindings } from '../owner/AuditReport'
import { riskTone } from './InspectorRanking'

const TONE = { good: 'text-emerald-700', warn: 'text-amber-700', bad: 'text-red-700', neutral: 'text-slate-600' }

export default function InspectorRestaurant() {
  const { id = '' } = useParams()
  const rest = useLive(() => api.restaurant(id), [id], { intervalMs: 10000 })
  const audits = useLive(() => api.restaurantAudits(id), [id], { intervalMs: 10000 })
  const [selected, setSelected] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const player = useRef<EvidencePlayerHandle>(null)

  useEffect(() => {
    if (!selected && audits.data?.length) {
      const first = audits.data.find((a) => a.findings !== undefined || a.score != null)
      setSelected(first?.id ?? null)
    }
  }, [audits.data, selected])

  const audit = useLive(() => (selected ? api.audit(selected) : Promise.resolve(null)), [selected], { intervalMs: 0 })
  const r = rest.data

  const act = async (fn: () => Promise<unknown>, text: string) => {
    try {
      await fn()
      setMsg(text)
      rest.reload()
      audits.reload()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-5 sm:py-8">
      <Link to="/inspector" className="text-sm font-semibold text-brand-700">
        ← Ranking
      </Link>
      {r && (
        <div className="card flex flex-col gap-4 md:flex-row md:items-center">
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-extrabold">{r.name}</h1>
            <p className="text-sm text-slate-500">
              {r.address} · FSSAI {r.fssaiLicense} · {r.ordersLastHour} orders in the last hour
            </p>
            <div className="mt-3">
              <ScoreBadge r={r} />
            </div>
          </div>
          <div className="md:w-72">
            <div className="flex items-center gap-2">
              <span className={`rounded-lg px-2 py-1 text-lg font-extrabold ${riskTone(r.riskScore)}`}>{r.riskScore}</span>
              <span className="text-sm font-semibold text-slate-600">risk</span>
            </div>
            <ul className="mt-1 text-sm text-slate-700">
              {r.riskReasons.map((x) => (
                <li key={x}>• {x}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary" onClick={() => act(() => api.surprise(id), 'Surprise audit sent. The kitchen has 10 minutes to start.')}>
          Trigger surprise audit
        </button>
        <button type="button" className="btn-secondary" onClick={() => act(() => api.inspectorVisit(id, 'confirmed'), 'Visit recorded: latest audit confirmed (counts 1.5×, enables Gold).')}>
          Record visit: confirms audit
        </button>
        <button
          type="button"
          className="btn-secondary text-red-700"
          onClick={() =>
            confirm('Void the latest audit and show “Failed verification” for 30 days?') &&
            act(() => api.inspectorVisit(id, 'contradicts'), 'Visit recorded: latest audit voided, badge shows Failed verification for 30 days.')
          }
        >
          Record visit: contradicts audit
        </button>
      </div>
      {msg && <div className="rounded-xl bg-brand-50 p-3 text-sm font-semibold text-brand-900 ring-1 ring-brand-200">{msg}</div>}

      <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
        <section>
          <h2 className="h-section">Audit history</h2>
          <ul className="space-y-1.5">
            {(audits.data ?? []).map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => a.status !== 'expired' && setSelected(a.id)}
                  className={`w-full rounded-xl p-2.5 text-left ring-1 ${selected === a.id ? 'bg-brand-50 ring-brand-300' : 'bg-white ring-slate-200 hover:ring-slate-300'}`}
                >
                  <div className={`text-sm font-semibold ${TONE[a.outcomeLabel?.tone ?? 'neutral']}`}>
                    {a.trigger === 'practice' ? `Practice${a.score != null ? ` · ${a.score}` : ''}` : a.outcomeLabel?.label}
                  </div>
                  <div className="text-xs text-slate-500">
                    {a.trigger} · {fmtDateTime(a.createdAt)}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section>
          {audit.data ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-bold">
                  {audit.data.trigger} audit · {fmtDateTime(audit.data.completedAt ?? audit.data.createdAt)}
                </h2>
                <IntegrityChip verdict={audit.data.integrity?.verdict} />
                {audit.data.distanceFromRegisteredM != null && (
                  <span className="text-xs text-slate-500">📍 {audit.data.distanceFromRegisteredM} m from address</span>
                )}
              </div>
              <EvidencePlayer ref={player} path={audit.data.videoPath} className="max-w-xl" />
              {(audit.data.integrity?.flags ?? []).length > 0 && (
                <ul className="space-y-1 text-sm">
                  {audit.data.integrity!.flags.map((f) => (
                    <li key={f.code} className="rounded-lg bg-white p-2 ring-1 ring-slate-200">
                      <b>{FLAG_LABELS[f.code] ?? f.code}</b> ({Math.round(f.confidence * 100)}%) — {f.detail}
                    </li>
                  ))}
                </ul>
              )}
              <ul className="space-y-2">
                {sortFindings(audit.data.findings ?? []).map((f) => (
                  <FindingRow key={f.id} f={f} onSeek={(s) => player.current?.seek(Math.max(0, s - 1))} />
                ))}
              </ul>
              <p className="text-xs text-slate-500">
                Model {audit.data.modelId} · prompt {audit.data.promptVersion}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Select an audit.</p>
          )}
        </section>
      </div>
    </div>
  )
}
