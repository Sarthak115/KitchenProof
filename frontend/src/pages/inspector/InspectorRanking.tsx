import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ScoreNumber } from '../../components/ScoreBadge'
import { TierIcon } from '../../components/TierIcon'
import { api } from '../../lib/api'
import { useLive } from '../../lib/hooks'
import type { Restaurant } from '../../lib/types'
import { RiskMap } from './RiskMap'

export function riskTone(risk: number) {
  if (risk >= 50) return 'bg-red-600 text-white'
  if (risk >= 25) return 'bg-amber-400 text-amber-950'
  return 'bg-emerald-100 text-emerald-900'
}

export default function InspectorRanking() {
  const { data, reload } = useLive(api.ranking, [], { intervalMs: 10000 })
  const queue = useLive(api.reviewQueue, [], { intervalMs: 10000 })
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const openItems = (queue.data ?? []).filter((q) => q.status === 'open').length

  const trigger = async (r?: Restaurant) => {
    setBusy(r?.id ?? 'random')
    try {
      const res = await api.surprise(r?.id)
      setMsg(`Surprise audit sent to ${res.restaurantName}. They have 10 minutes to start.`)
      reload()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-5 sm:py-8">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Food safety inspector · Bhubaneswar</div>
          <h1 className="text-2xl font-extrabold">Visit first this week</h1>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <Link to="/inspector/review" className="btn-secondary">
            Review queue
            {openItems > 0 && <span className="rounded-full bg-red-600 px-2 text-xs text-white">{openItems}</span>}
          </Link>
          <button type="button" className="btn-primary" disabled={!!busy} onClick={() => trigger()}>
            🎲 Surprise a random kitchen
          </button>
        </div>
      </div>
      {msg && <div className="rounded-xl bg-brand-50 p-3 text-sm font-semibold text-brand-900 ring-1 ring-brand-200">{msg} <Link className="underline" to="/owner">Open owner view →</Link></div>}

      <RiskMap restaurants={data ?? []} />

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="hidden grid-cols-[3rem_1fr_5rem_5rem_1.6fr_10rem] gap-3 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-slate-500 md:grid">
          <div>#</div>
          <div>Restaurant</div>
          <div>Score</div>
          <div>Risk</div>
          <div>Why</div>
          <div />
        </div>
        {!data && <p className="p-4 text-slate-500">Loading…</p>}
        <ul className="divide-y divide-slate-200">
          {(data ?? []).map((r) => (
            <li key={r.id} className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 px-4 py-3 md:grid-cols-[3rem_1fr_5rem_5rem_1.6fr_10rem]">
              <div className="text-lg font-extrabold text-slate-400">{r.rank}</div>
              <div className="min-w-0">
                <Link to={`/inspector/restaurant/${r.id}`} className="font-bold hover:text-brand-700 hover:underline">
                  {r.name}
                </Link>
                <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                  <TierIcon tier={r.tier} />
                  {r.area}
                  {r.badgeState === 'failed_verification' && <span className="rounded bg-red-100 px-1.5 font-bold text-red-800">failed verification</span>}
                  {r.underReview && <span className="rounded bg-amber-100 px-1.5 font-bold text-amber-800">under review</span>}
                </div>
                <ul className="mt-1 text-xs text-slate-600 md:hidden">
                  {r.riskReasons.slice(0, 2).map((x) => (
                    <li key={x}>• {x}</li>
                  ))}
                </ul>
              </div>
              <div className="hidden md:block">
                <ScoreNumber score={r.badgeState === 'scored' ? r.publicScore : null} size="sm" />
              </div>
              <div>
                <span className={`inline-flex min-w-[3rem] justify-center rounded-lg px-2 py-1 text-sm font-extrabold ${riskTone(r.riskScore)}`}>{r.riskScore}</span>
              </div>
              <ul className="hidden text-sm text-slate-700 md:block">
                {r.riskReasons.slice(0, 2).map((x) => (
                  <li key={x}>• {x}</li>
                ))}
                {r.riskReasons.length === 0 && <li className="text-slate-400">No concerns</li>}
              </ul>
              <div className="col-span-3 md:col-span-1">
                <button type="button" disabled={!!busy} onClick={() => trigger(r)} className="btn-secondary w-full text-sm">
                  {busy === r.id ? 'Sending…' : 'Trigger surprise audit'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
