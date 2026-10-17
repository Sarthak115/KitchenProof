import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Countdown } from '../../components/Countdown'
import { Disclaimer } from '../../components/ScoreBadge'
import { api } from '../../lib/api'
import { useConfig } from '../../lib/config'
import { useLive } from '../../lib/hooks'
import { customerId } from '../../lib/identity'
import { FoodieGoHeader } from './FoodieGoHeader'

const STEPS = ['Order placed', 'Preparing', 'Out for delivery', 'Delivered']

export default function CustomerOrder() {
  const { orderId = '' } = useParams()
  const { demo, config } = useConfig()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const { data: o, reload } = useLive(() => api.order(orderId), [orderId], { intervalMs: 3000 })

  if (!o) return <div className="page">Loading order…</div>
  const check = o.spotCheck
  const pending = check && ['requested', 'in_progress', 'uploaded', 'analyzing'].includes(check.status)

  const request = async () => {
    setBusy(true)
    setErr(null)
    try {
      await api.createAudit({ restaurantId: o.restaurantId, trigger: 'customer', orderId: o.id, customerId: await customerId() })
      await reload()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <FoodieGoHeader subtitle={`Order #${o.id}`} />
      <div className="mx-auto max-w-md space-y-4 px-4 py-5">
        <div className="card">
          <div className="text-sm text-slate-500">Your order from</div>
          <Link to={`/customer/restaurant/${o.restaurantId}`} className="text-xl font-extrabold hover:underline">
            {o.restaurantName}
          </Link>
          <div className="text-sm text-slate-600">{o.items.join(' · ')}</div>
          <ol className="mt-4 flex items-center gap-1">
            {STEPS.map((s, i) => (
              <li key={s} className="flex-1">
                <div className={`h-1.5 rounded-full ${i <= 1 ? 'bg-rose-500' : 'bg-slate-200'}`} />
                <div className={`mt-1 text-[11px] ${i === 1 ? 'font-bold text-rose-700' : 'text-slate-500'}`}>{s}</div>
              </li>
            ))}
          </ol>
        </div>

        <div className="card">
          <h2 className="text-lg font-bold">🔍 See the kitchen making your food</h2>
          {!check && (
            <>
              <p className="mt-1 text-sm text-slate-600">
                Ask the kitchen for a live, AI-verified walk-through while your order is being prepared. You will see the result,
                not the raw video.
              </p>
              <button type="button" disabled={busy || o.status !== 'preparing'} onClick={request} className="btn mt-3 w-full bg-rose-600 text-white hover:bg-rose-700">
                {busy ? 'Requesting…' : 'Request a kitchen check'}
              </button>
              {err && <p className="mt-2 rounded-lg bg-red-50 p-2 text-sm text-red-700">{err}</p>}
              <p className="mt-2 text-xs text-slate-500">
                Limits: 1 request per restaurant every {config.customerCooldownDays} days; up to {config.customerChecksPerDay}{' '}
                customer checks per kitchen per day.
              </p>
            </>
          )}
          {check && pending && (
            <div className="mt-2 rounded-xl bg-amber-50 p-3">
              {check.status === 'requested' ? (
                <>
                  <div className="font-semibold text-amber-900">
                    Kitchen has <Countdown until={check.startDeadlineAt} className="font-bold" /> to respond
                  </div>
                  <p className="text-sm text-amber-900">They must show your order being prepared, live.</p>
                </>
              ) : (
                <div className="font-semibold text-amber-900">
                  {check.status === 'in_progress' ? 'The kitchen is showing you around right now…' : 'Gemini is checking the video…'}
                </div>
              )}
              {demo && check.status !== 'analyzing' && check.status !== 'uploaded' && (
                <Link to={`/owner/audit/${check.auditId}`} className="btn-secondary mt-3 w-full text-sm">
                  Demo: respond as the kitchen →
                </Link>
              )}
            </div>
          )}
          {check && !pending && (
            <div
              className={`mt-2 rounded-xl p-4 ${check.tone === 'good' ? 'bg-emerald-50 text-emerald-900' : check.tone === 'bad' ? 'bg-red-50 text-red-900' : 'bg-amber-50 text-amber-900'}`}
            >
              {check.status === 'expired' ? (
                <div className="font-bold">⚠️ Kitchen didn’t respond in time (recorded as a missed check)</div>
              ) : check.counted ? (
                <div className="text-lg font-bold">
                  {check.tone === 'good' ? '✅' : '⚠️'} Verified during your order · Score {check.score}
                </div>
              ) : (
                <div className="font-bold">{check.label}</div>
              )}
              <div className="mt-1 text-sm">{check.status === 'expired' ? '' : check.label}</div>
              <Link to={`/customer/restaurant/${o.restaurantId}`} className="mt-2 inline-block text-sm font-semibold underline">
                See the kitchen badge
              </Link>
            </div>
          )}
          <Disclaimer className="mt-3" />
        </div>
      </div>
    </div>
  )
}
