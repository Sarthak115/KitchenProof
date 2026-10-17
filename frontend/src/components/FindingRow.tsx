import { useState } from 'react'
import { checkLabel, SEVERITY_STYLE } from '../lib/checks'
import type { Finding } from '../lib/types'
import { parseMmss } from '../lib/time'

const STATUS = {
  pass: { label: 'Pass', cls: 'bg-emerald-600 text-white', icon: '✓' },
  fail: { label: 'Issue', cls: 'bg-red-600 text-white', icon: '✕' },
  not_verified: { label: 'Not verified', cls: 'bg-slate-400 text-white', icon: '?' },
}

export function FindingRow({
  f,
  onSeek,
  onDispute,
}: {
  f: Finding
  onSeek?: (sec: number) => void
  onDispute?: (reason: string) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const status = STATUS[f.effectiveStatus ?? f.status]
  const sec = parseMmss(f.timestamp)

  return (
    <li className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${status.cls}`} aria-label={status.label}>
          {status.icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-semibold text-slate-900">{checkLabel(f.checkId)}</span>
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ring-1 ${SEVERITY_STYLE[f.severity]}`}>{f.severity}</span>
            {f.needsReview && <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-violet-800">needs review · not public</span>}
            {f.disputed && !f.review && <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-sky-800">disputed · hidden from score</span>}
            {f.review && (
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold uppercase text-white">
                inspector {f.review.decision}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-slate-700">{f.reason}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            {onSeek && f.status !== 'not_verified' && (
              <button type="button" onClick={() => onSeek(sec)} className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-2 py-1 font-semibold text-white hover:bg-slate-700">
                ▶ {f.timestamp}
              </button>
            )}
            <span>AI confidence {Math.round(f.confidence * 100)}%</span>
            {onDispute && f.status !== 'pass' && !f.disputed && (
              <button type="button" onClick={() => setOpen((o) => !o)} className="font-semibold text-brand-700 underline-offset-2 hover:underline">
                Dispute
              </button>
            )}
          </div>
          {f.dispute && <p className="mt-1 text-xs italic text-slate-500">Owner: “{f.dispute.reason}”</p>}
          {open && (
            <form
              className="mt-2 space-y-2"
              onSubmit={async (e) => {
                e.preventDefault()
                setBusy(true)
                setErr(null)
                try {
                  await onDispute!(reason)
                  setOpen(false)
                } catch (ex) {
                  setErr(ex instanceof Error ? ex.message : 'Failed')
                } finally {
                  setBusy(false)
                }
              }}
            >
              <textarea
                required
                minLength={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why is this finding wrong? An inspector will review it."
                className="w-full rounded-lg border border-slate-300 p-2 text-sm"
                rows={2}
              />
              {err && <p className="text-xs text-red-700">{err}</p>}
              <button disabled={busy} className="btn-primary text-sm">
                {busy ? 'Sending…' : 'Send to inspector'}
              </button>
            </form>
          )}
        </div>
      </div>
    </li>
  )
}
