import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Countdown } from '../../components/Countdown'
import { ScoreBadge } from '../../components/ScoreBadge'
import { watchRestaurantAudits } from '../../firebase'
import { api } from '../../lib/api'
import { useLive, useStoredState } from '../../lib/hooks'
import { fmtDateTime } from '../../lib/time'
import type { Audit, Restaurant } from '../../lib/types'

const TRIGGER_TEXT = {
  surprise: 'Surprise audit from the platform',
  customer: 'A customer asked to see your kitchen during their order',
  practice: 'Practice audit (never counts publicly)',
}

const TONE = { good: 'text-emerald-700', warn: 'text-amber-700', bad: 'text-red-700', neutral: 'text-slate-600' }

export default function OwnerDashboard() {
  const [params, setParams] = useSearchParams()
  const [stored, setStored] = useStoredState('kp_owner_restaurant', 'r01')
  const rid = params.get('r') || stored
  const navigate = useNavigate()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.restaurants().then(setRestaurants).catch(() => {})
  }, [])
  useEffect(() => {
    if (rid !== stored) setStored(rid)
  }, [rid, stored, setStored])

  const rest = useLive(() => api.restaurant(rid), [rid], { intervalMs: 8000 })
  const audits = useLive(
    async () => {
      await api.expire().catch(() => {})
      return api.restaurantAudits(rid)
    },
    [rid],
    { intervalMs: 4000, watch: (cb) => watchRestaurantAudits(rid, cb) },
  )

  const open = (audits.data ?? []).filter((a) => a.status === 'requested' || a.status === 'in_progress')
  const history = (audits.data ?? []).filter((a) => !open.includes(a))

  return (
    <div className="page max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-extrabold sm:text-2xl">Owner dashboard</h1>
        <select
          value={rid}
          onChange={(e) => setParams({ r: e.target.value })}
          className="ml-auto max-w-[60%] rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
          aria-label="Your restaurant"
        >
          {restaurants.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      {open.map((a) => (
        <RequestBanner key={a.id} audit={a} onStart={() => navigate(`/owner/audit/${a.id}`)} />
      ))}

      {rest.data && (
        <div className="card">
          <div className="text-lg font-bold">{rest.data.name}</div>
          <div className="mb-4 text-sm text-slate-500">
            {rest.data.cuisine} · {rest.data.address}
          </div>
          <ScoreBadge r={rest.data} />
          {rest.data.tier === 'bronze' && rest.data.badgeState === 'scored' && (
            <p className="mt-3 rounded-lg bg-slate-50 p-2 text-xs text-slate-600">
              Pass two surprise or customer checks within 30 days to reach 🥈 Silver.
            </p>
          )}
        </div>
      )}

      <div className="card">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1">
            <div className="font-bold">Practice audit</div>
            <p className="text-sm text-slate-600">Try the walk-through any time. Practice audits never count toward your public score.</p>
          </div>
          <button
            type="button"
            disabled={busy}
            className="btn-secondary"
            onClick={async () => {
              setBusy(true)
              try {
                const { auditId } = await api.createAudit({ restaurantId: rid, trigger: 'practice' })
                navigate(`/owner/audit/${auditId}`)
              } catch (e) {
                alert(e instanceof Error ? e.message : 'Failed')
              } finally {
                setBusy(false)
              }
            }}
          >
            Start practice
          </button>
        </div>
      </div>

      <section>
        <h2 className="h-section">Audit history</h2>
        {!audits.data && <p className="text-sm text-slate-500">Loading…</p>}
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          {history.map((a) => (
            <li key={a.id}>
              <Link to={a.status === 'expired' ? '#' : `/owner/report/${a.id}`} className="flex items-center gap-3 p-3 hover:bg-slate-50">
                <div className="min-w-0 flex-1">
                  <div className={`font-semibold ${TONE[a.outcomeLabel?.tone ?? 'neutral']}`}>
                    {a.trigger === 'practice' && a.score != null ? `Practice · score ${a.score}` : a.outcomeLabel?.label}
                  </div>
                  <div className="text-xs text-slate-500">
                    {a.trigger} · {fmtDateTime(a.createdAt)}
                  </div>
                </div>
                {a.status !== 'expired' && <span className="text-slate-400">›</span>}
              </Link>
            </li>
          ))}
          {audits.data && history.length === 0 && <li className="p-3 text-sm text-slate-500">No audits yet.</li>}
        </ul>
      </section>
    </div>
  )
}

function RequestBanner({ audit, onStart }: { audit: Audit; onStart: () => void }) {
  const inProgress = audit.status === 'in_progress'
  const practice = audit.trigger === 'practice'
  return (
    <div className={`rounded-2xl p-4 text-white shadow-lg sm:p-5 ${practice ? 'bg-slate-700' : 'bg-gradient-to-r from-red-600 to-orange-500'}`}>
      <div className="flex items-start gap-3">
        <span className="relative mt-1 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
        </span>
        <div className="flex-1">
          <div className="text-xs font-bold uppercase tracking-wider text-white/80">{inProgress ? 'Audit in progress' : 'Kitchen check requested'}</div>
          <div className="text-lg font-bold">{TRIGGER_TEXT[audit.trigger]}</div>
          {audit.orderId && <div className="text-sm text-white/90">Live order #{audit.orderId}</div>}
          <div className="mt-2 text-sm">
            {inProgress ? 'Finish within ' : 'Start within '}
            <Countdown
              until={inProgress ? audit.finishDeadlineAt : audit.startDeadlineAt}
              className="rounded bg-black/20 px-1.5 py-0.5 text-lg font-bold text-white"
            />
            {!practice && <span className="block text-xs text-white/80">Missing the window is shown publicly as a missed check.</span>}
          </div>
        </div>
      </div>
      <button type="button" onClick={onStart} className="btn mt-4 w-full bg-white text-lg text-red-700 hover:bg-red-50">
        {inProgress ? 'Resume audit' : 'Start audit now'}
      </button>
    </div>
  )
}
