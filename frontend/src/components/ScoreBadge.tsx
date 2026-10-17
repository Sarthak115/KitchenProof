import type { Restaurant } from '../lib/types'
import { ago } from '../lib/time'
import { TierIcon } from './TierIcon'

export function scoreTone(score: number | null | undefined) {
  if (score == null) return 'text-slate-500 bg-slate-100 ring-slate-200'
  if (score >= 75) return 'text-emerald-800 bg-emerald-50 ring-emerald-200'
  if (score >= 50) return 'text-amber-800 bg-amber-50 ring-amber-200'
  return 'text-red-800 bg-red-50 ring-red-200'
}

export function ScoreNumber({ score, size = 'md' }: { score: number | null | undefined; size?: 'sm' | 'md' | 'lg' }) {
  const dims = size === 'lg' ? 'h-24 w-24 text-4xl' : size === 'sm' ? 'h-10 w-10 text-base' : 'h-14 w-14 text-2xl'
  return (
    <div className={`flex ${dims} shrink-0 items-center justify-center rounded-2xl font-extrabold ring-2 ${scoreTone(score)}`}>
      {score ?? '—'}
    </div>
  )
}

/** Public Kitchen Score badge (customer-facing wording, §5.2 #7). */
export function ScoreBadge({ r, compact = false }: { r: Restaurant; compact?: boolean }) {
  if (r.badgeState === 'failed_verification') {
    return (
      <div className="flex items-center gap-3">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-red-600 text-2xl text-white">!</div>
        <div>
          <div className="font-bold text-red-700">Failed verification</div>
          <div className="text-xs text-slate-500">Last kitchen check could not be verified</div>
        </div>
      </div>
    )
  }
  const notRecent = r.badgeState === 'not_recently_verified'
  const unverified = r.badgeState === 'unverified'
  return (
    <div className="flex items-center gap-3">
      <ScoreNumber score={notRecent || unverified ? null : r.publicScore} size={compact ? 'sm' : 'md'} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-bold text-slate-900">{notRecent ? 'Not recently verified' : unverified ? 'Not verified yet' : 'Kitchen Score'}</span>
          <TierIcon tier={r.tier} />
        </div>
        <div className="text-xs text-slate-500">
          {r.lastCountedAuditAt ? `verified ${ago(r.lastCountedAuditAt)}` : 'no surprise checks yet'}
          {r.lastIssuesFound ? ` · ${r.lastIssuesFound} issue${r.lastIssuesFound > 1 ? 's' : ''} found` : ''}
          {r.missedChecks30d > 0 && <span className="font-semibold text-red-700"> · {r.missedChecks30d} missed check{r.missedChecks30d > 1 ? 's' : ''}</span>}
          {r.underReview && <span> · under review</span>}
        </div>
      </div>
    </div>
  )
}

export function Disclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-[11px] leading-snug text-slate-500 ${className}`}>
      Self-audit verified by AI — not an official FSSAI rating.
    </p>
  )
}
