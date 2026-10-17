import type { Tier } from '../lib/types'

const TIERS: Record<Tier, { emoji: string; label: string; cls: string; hint: string }> = {
  bronze: { emoji: '🥉', label: 'Bronze', cls: 'bg-orange-50 text-orange-900 ring-orange-200', hint: 'Self or practice audits only' },
  silver: { emoji: '🥈', label: 'Silver', cls: 'bg-slate-100 text-slate-800 ring-slate-300', hint: '2+ surprise or customer checks passed in 30 days' },
  gold: { emoji: '🥇', label: 'Gold', cls: 'bg-yellow-50 text-yellow-900 ring-yellow-300', hint: 'Silver + confirmed by an inspector visit' },
}

export function TierIcon({ tier, showLabel = true }: { tier: Tier; showLabel?: boolean }) {
  const t = TIERS[tier] ?? TIERS.bronze
  return (
    <span title={t.hint} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${t.cls}`}>
      <span aria-hidden>{t.emoji}</span>
      {showLabel && t.label}
    </span>
  )
}

export const TIER_INFO = TIERS
