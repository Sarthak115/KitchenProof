import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Disclaimer, ScoreBadge } from '../../components/ScoreBadge'
import { api } from '../../lib/api'
import { useLive } from '../../lib/hooks'
import { FoodieGoHeader } from './FoodieGoHeader'

export default function CustomerList() {
  const { data } = useLive(api.restaurants, [], { intervalMs: 10000 })
  const [verifiedOnly, setVerifiedOnly] = useState(false)
  const list = (data ?? [])
    .filter((r) => !verifiedOnly || (r.badgeState === 'scored' && r.tier !== 'bronze'))
    .sort((a, b) => (b.publicScore ?? -1) - (a.publicScore ?? -1))

  return (
    <div>
      <FoodieGoHeader subtitle="Delivering in Bhubaneswar" />
      <div className="mx-auto max-w-3xl px-4 py-5">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-extrabold">Restaurants near you</h1>
          <label className="ml-auto inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-sm font-semibold ring-1 ring-slate-200">
            <input type="checkbox" checked={verifiedOnly} onChange={(e) => setVerifiedOnly(e.target.checked)} />
            🥈 Silver & 🥇 Gold kitchens only
          </label>
        </div>
        {!data && <p className="text-slate-500">Loading…</p>}
        <ul className="space-y-3">
          {list.map((r) => (
            <li key={r.id}>
              <Link to={`/customer/restaurant/${r.id}`} className="card flex flex-col gap-3 hover:shadow-md sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="text-lg font-bold">{r.name}</div>
                  <div className="text-sm text-slate-500">
                    {r.cuisine} · {r.area} · ★ {r.rating.toFixed(1)}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 p-2 sm:w-72">
                  <ScoreBadge r={r} compact />
                </div>
              </Link>
            </li>
          ))}
        </ul>
        <Disclaimer className="mt-4" />
      </div>
    </div>
  )
}
