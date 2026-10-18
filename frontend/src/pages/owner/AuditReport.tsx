import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EvidencePlayer, type EvidencePlayerHandle } from '../../components/EvidencePlayer'
import { FindingRow } from '../../components/FindingRow'
import { IntegrityChip } from '../../components/IntegrityChip'
import { Disclaimer, ScoreNumber } from '../../components/ScoreBadge'
import { TierIcon } from '../../components/TierIcon'
import { watchAuditDoc } from '../../firebase'
import { api } from '../../lib/api'
import { FLAG_LABELS } from '../../lib/checks'
import { useLive } from '../../lib/hooks'
import { fmtDateTime } from '../../lib/time'
import type { Audit, Finding } from '../../lib/types'

const ORDER = { fail: 0, not_verified: 1, pass: 2 }
const SEV = { critical: 0, high: 1, medium: 2, low: 3 }

export function sortFindings(f: Finding[]) {
  return [...f].sort(
    (a, b) => ORDER[a.effectiveStatus ?? a.status] - ORDER[b.effectiveStatus ?? b.status] || SEV[a.severity] - SEV[b.severity],
  )
}

export function statusSummary(a: Audit): { title: string; text: string; tone: string } {
  if (a.voided) return { title: 'Voided', text: 'An inspector visit contradicted this audit.', tone: 'bg-red-50 text-red-900' }
  if (a.integrity?.verdict === 'failed')
    return { title: 'Failed verification', text: 'The integrity check failed (for example the liveness gesture or location). This counts as 0 and is shown publicly for 30 days.', tone: 'bg-red-50 text-red-900' }
  if (a.integrity?.verdict === 'suspicious')
    return { title: 'Under review', text: 'Possible staging was flagged. This audit is excluded from your public score until an inspector reviews it. Customers only see “under review”.', tone: 'bg-amber-50 text-amber-900' }
  if (a.outcome === 'inconclusive')
    return { title: 'Inconclusive', text: a.analysisError && !a.usedCachedResult ? `AI analysis was not available (${a.analysisError}).` : 'Fewer than 70% of the checks could be verified, so this audit does not count. Please do a quick re-audit.', tone: 'bg-slate-100 text-slate-800' }
  if (a.trigger === 'practice') return { title: 'Practice result', text: 'Practice audits never count toward your public score.', tone: 'bg-slate-100 text-slate-800' }
  if (a.status === 'under_review') return { title: 'Dispute under review', text: 'Disputed findings are hidden from your public score until an inspector decides.', tone: 'bg-sky-50 text-sky-900' }
  return { title: 'Counted publicly', text: 'This verified audit now counts toward your public Kitchen Score.', tone: 'bg-emerald-50 text-emerald-900' }
}

export default function AuditReport() {
  const { auditId = '' } = useParams()
  const navigate = useNavigate()
  const player = useRef<EvidencePlayerHandle>(null)
  const [lang, setLang] = useState<'en' | 'hi' | 'or'>('en')
  const { data: a, error, reload } = useLive(() => api.audit(auditId), [auditId], {
    intervalMs: 10000,
    watch: watchAuditDoc(auditId),
  })
  const rest = useLive(() => (a ? api.restaurant(a.restaurantId) : Promise.resolve(null)), [a?.restaurantId], { intervalMs: 0 })

  if (error) return <div className="page">Could not load the report: {error}</div>
  if (!a) return <div className="page">Loading report…</div>
  if (a.status === 'analyzing' || a.status === 'uploaded') {
    return <div className="page">Still analyzing… this page updates automatically.</div>
  }

  const summary = statusSummary(a)
  const findings = sortFindings(a.findings ?? [])
  const coach = a.coach?.[lang]?.length ? a.coach[lang] : a.coach?.en ?? []
  const flags = (a.integrity?.flags ?? []).filter((f) => f.code !== 'liveness_ok')

  return (
    <div className="page max-w-3xl space-y-5">
      <Link to={`/owner?r=${a.restaurantId}`} className="text-sm font-semibold text-brand-700">
        ← Dashboard
      </Link>

      <div className="card">
        <div className="flex items-start gap-4">
          <ScoreNumber score={a.integrity?.verdict === 'suspicious' ? null : a.score} size="lg" />
          <div className="min-w-0 flex-1">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
              {a.trigger} audit · {fmtDateTime(a.completedAt)}
            </div>
            <h1 className="text-xl font-extrabold sm:text-2xl">{a.restaurantName}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <IntegrityChip verdict={a.integrity?.verdict} />
              {rest.data && <TierIcon tier={rest.data.tier} />}
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                Coverage {Math.round((a.coverage ?? 0) * 100)}%
              </span>
              {a.issuesFound != null && (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                  {a.issuesFound} issue{a.issuesFound === 1 ? '' : 's'}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className={`mt-4 rounded-xl p-3 text-sm ${summary.tone}`}>
          <b>{summary.title}.</b> {summary.text}
        </div>
        {a.outcome === 'inconclusive' && a.trigger !== 'practice' && (
          <button
            type="button"
            className="btn-primary mt-3"
            onClick={async () => {
              try {
                const r = await api.reaudit(a.id)
                navigate(`/owner/audit/${r.auditId}`)
              } catch (e) {
                alert(e instanceof Error ? e.message : 'Failed')
              }
            }}
          >
            Re-audit now
          </button>
        )}
      </div>

      <div className="grid gap-5 md:grid-cols-5">
        <div className="md:col-span-2">
          <div className="md:sticky md:top-20">
            <EvidencePlayer ref={player} path={a.videoPath} label="Tap ▶ on a finding to jump to its evidence." />
          </div>
        </div>
        <section className="md:col-span-3">
          <h2 className="h-section">Findings</h2>
          <ul className="space-y-2">
            {findings.map((f) => (
              <FindingRow
                key={f.id}
                f={f}
                onSeek={(s) => player.current?.seek(Math.max(0, s - 1))}
                onDispute={async (reason) => {
                  await api.dispute(a.id, f.id, reason)
                  await reload()
                }}
              />
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            “Not verified” means the check was not shown clearly — it lowers coverage, never the score. Findings with low AI
            confidence go to a human and are never public.
          </p>
        </section>
      </div>

      {coach.length > 0 && (
        <section className="card">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="h-section mb-0">Fix list</h2>
            <div className="ml-auto flex rounded-lg bg-slate-100 p-0.5 text-sm">
              {(['en', 'hi', 'or'] as const).map((l) => (
                <button
                  key={l}
                  type="button"
                  disabled={!a.coach?.[l]?.length}
                  onClick={() => setLang(l)}
                  className={`rounded-md px-2.5 py-1 font-semibold disabled:opacity-40 ${lang === l ? 'bg-white shadow' : ''}`}
                >
                  {{ en: 'English', hi: 'हिन्दी', or: 'ଓଡ଼ିଆ' }[l]}
                </button>
              ))}
            </div>
          </div>
          <ol className="list-decimal space-y-1.5 pl-5 text-slate-800">
            {coach.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </section>
      )}

      <section className="card">
        <h2 className="h-section">Integrity check</h2>
        {a.liveness && (
          <div className="mb-3 rounded-xl bg-amber-50 p-3 text-sm">
            <div className="font-semibold">✋ Liveness: “{a.liveness.prompt}”</div>
            {a.liveness.observed && (
              <div className="text-slate-700">
                Seen at {a.liveness.observed.timestamp}: {a.liveness.observed.observed}{' '}
                <button type="button" className="font-semibold text-brand-700" onClick={() => player.current?.seek(Math.max(0, (a.liveness?.offsetSec ?? 0) - 1))}>
                  ▶ watch
                </button>
              </div>
            )}
          </div>
        )}
        {!a.integrity ? (
          <p className="text-sm text-slate-600">The integrity check did not run for this audit.</p>
        ) : flags.length === 0 ? (
          <p className="text-sm text-emerald-800">No signs of editing or staging were found.</p>
        ) : (
          <ul className="space-y-2">
            {flags.map((f) => (
              <li key={f.code} className="rounded-lg border border-slate-200 p-2 text-sm">
                <b>{FLAG_LABELS[f.code] ?? f.code}</b> — {f.detail}
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer className="space-y-1 text-xs text-slate-500">
        <div>
          Model {a.modelId} · prompt {a.promptVersion}
          {a.usedCachedResult && <span className="ml-1 rounded bg-slate-200 px-1.5 py-0.5 font-semibold">cached result</span>}
        </div>
        <Disclaimer />
      </footer>
    </div>
  )
}
