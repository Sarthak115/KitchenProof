import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ClipPlayer } from '../../components/EvidencePlayer'
import { Disclaimer, ScoreBadge } from '../../components/ScoreBadge'
import { StatusTimeline } from '../../components/StatusTimeline'
import { TIER_INFO } from '../../components/TierIcon'
import { watchRestaurantDoc } from '../../firebase'
import { api } from '../../lib/api'
import { checkLabel } from '../../lib/checks'
import { useConfig } from '../../lib/config'
import { useLive } from '../../lib/hooks'
import { customerId } from '../../lib/identity'
import { FoodieGoHeader } from './FoodieGoHeader'

export default function CustomerRestaurant() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { demo } = useConfig()
  const [busy, setBusy] = useState(false)
  const { data: r, error } = useLive(() => api.restaurant(id), [id], { intervalMs: 6000, watch: (cb) => watchRestaurantDoc(id, cb) })

  if (error) return <div className="page">Could not load: {error}</div>
  if (!r) return <div className="page">Loading…</div>

  const order = async () => {
    setBusy(true)
    try {
      const cid = await customerId()
      const { orderId } = await api.demoOrder(r.id, cid)
      navigate(`/customer/order/${orderId}`)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <FoodieGoHeader />
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-5">
        <Link to="/customer" className="text-sm font-semibold text-rose-700">
          ← All restaurants
        </Link>
        <div className="card">
          <h1 className="text-2xl font-extrabold">{r.name}</h1>
          <p className="text-sm text-slate-500">
            {r.cuisine} · {r.address} · ★ {r.rating.toFixed(1)}
          </p>
          <div className="mt-4 rounded-2xl bg-slate-50 p-3">
            <ScoreBadge r={r} />
          </div>
          {r.underReview && (
            <p className="mt-2 text-xs text-slate-500">A recent check is under review by a food safety inspector.</p>
          )}
          <button type="button" disabled={busy || !demo} onClick={order} className="btn mt-4 w-full bg-rose-600 text-white hover:bg-rose-700">
            {busy ? 'Placing order…' : 'Order & request a kitchen check'}
          </button>
          {!demo && <p className="mt-1 text-center text-xs text-slate-500">Ordering is only simulated in Demo Mode.</p>}
        </div>

        {r.evidenceClips?.length > 0 && (
          <section className="card">
            <h2 className="h-section">From the latest verified check</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {r.evidenceClips.map((c) => (
                <ClipPlayer key={`${c.auditId}-${c.checkId}`} path={c.videoPath} startSec={c.startSec} endSec={c.endSec} caption={checkLabel(c.checkId)} />
              ))}
            </div>
          </section>
        )}

        <section className="card">
          <h2 className="h-section">Recent kitchen checks</h2>
          <StatusTimeline items={r.timeline ?? []} />
        </section>

        <section className="card">
          <h2 className="h-section">What the tiers mean</h2>
          <ul className="space-y-1.5 text-sm">
            {Object.entries(TIER_INFO).map(([k, t]) => (
              <li key={k}>
                <span aria-hidden>{t.emoji}</span> <b>{t.label}</b> — {t.hint}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-slate-600">
            Checks are unannounced live phone walk-throughs analysed by Google Gemini, with a liveness challenge and an
            integrity check. Customers see results and short clips, never the raw video.
          </p>
          <Disclaimer className="mt-3" />
        </section>
      </div>
    </div>
  )
}
