import { useState } from 'react'
import { Link } from 'react-router-dom'
import { EvidencePlayer } from '../../components/EvidencePlayer'
import { FindingRow } from '../../components/FindingRow'
import { api } from '../../lib/api'
import { FLAG_LABELS } from '../../lib/checks'
import { useLive } from '../../lib/hooks'
import { fmtDateTime } from '../../lib/time'
import type { ReviewItem } from '../../lib/types'

export default function InspectorReview() {
  const { data, reload } = useLive(api.reviewQueue, [], { intervalMs: 8000 })
  const [showResolved, setShowResolved] = useState(false)
  const items = (data ?? []).filter((q) => showResolved || q.status === 'open')

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5 px-4 py-5 sm:py-8">
      <Link to="/inspector" className="text-sm font-semibold text-brand-700">
        ← Ranking
      </Link>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">Review queue</h1>
          <p className="text-sm text-slate-600">Disputed findings and possible staging. Nothing here is public until you decide.</p>
        </div>
        <label className="ml-auto inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} /> Show resolved
        </label>
      </div>
      {!data && <p className="text-slate-500">Loading…</p>}
      {data && items.length === 0 && <p className="card text-slate-600">Nothing to review. 🎉</p>}
      <ul className="space-y-4">
        {items.map((q) => (
          <ReviewCard key={q.id} q={q} onDone={reload} />
        ))}
      </ul>
    </div>
  )
}

function ReviewCard({ q, onDone }: { q: ReviewItem; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const [video, setVideo] = useState(false)
  const decide = async (decision: string) => {
    setBusy(true)
    try {
      await api.resolveReview(q.id, decision)
      onDone()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }
  const integrity = q.type === 'integrity'
  const flags = (q.audit.integrity?.flags ?? []).filter((f) => f.code !== 'liveness_ok')
  return (
    <li className={`card ${q.status === 'resolved' ? 'opacity-60' : ''}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${integrity ? 'bg-amber-100 text-amber-900' : 'bg-sky-100 text-sky-900'}`}>
          {integrity ? 'Possible staging' : 'Dispute'}
        </span>
        <Link to={`/inspector/restaurant/${q.restaurantId}`} className="font-bold hover:underline">
          {q.restaurantName}
        </Link>
        <span className="text-xs text-slate-500">
          {q.audit.trigger} audit · {fmtDateTime(q.createdAt)}
        </span>
        {q.status === 'resolved' && <span className="ml-auto text-xs font-bold uppercase text-slate-500">resolved: {q.decision}</span>}
      </div>

      {integrity ? (
        <div className="mt-3 space-y-1.5 text-sm">
          {q.audit.ordersLastHourAtAudit != null && <p className="text-slate-600">{q.audit.ordersLastHourAtAudit} orders in the hour of the audit.</p>}
          {flags.map((f) => (
            <div key={f.code} className="rounded-lg bg-amber-50 p-2">
              <b>{FLAG_LABELS[f.code] ?? f.code}</b> ({Math.round(f.confidence * 100)}%) — {f.detail}
            </div>
          ))}
        </div>
      ) : (
        q.finding && (
          <ul className="mt-3">
            <FindingRow f={q.finding} />
          </ul>
        )
      )}

      <button type="button" onClick={() => setVideo((v) => !v)} className="mt-3 text-sm font-semibold text-brand-700">
        {video ? 'Hide video' : '▶ Watch the recording'}
      </button>
      {video && <EvidencePlayer path={q.audit.videoPath} className="mt-2 max-w-lg" />}

      {q.status === 'open' && (
        <div className="mt-4 flex flex-wrap gap-2">
          {integrity ? (
            <>
              <button type="button" disabled={busy} onClick={() => decide('clear')} className="btn-secondary">
                Clear integrity flag
              </button>
              <button type="button" disabled={busy} onClick={() => decide('confirm_failed')} className="btn-danger">
                Confirm failed verification
              </button>
            </>
          ) : (
            <>
              <button type="button" disabled={busy} onClick={() => decide('upheld')} className="btn-secondary">
                Uphold finding
              </button>
              <button type="button" disabled={busy} onClick={() => decide('overturned')} className="btn-primary">
                Overturn finding
              </button>
            </>
          )}
        </div>
      )}
    </li>
  )
}
