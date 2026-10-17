import type { Outcome } from '../lib/types'
import { fmtDate } from '../lib/time'

const DOT = { good: 'bg-emerald-500', warn: 'bg-amber-500', bad: 'bg-red-500', neutral: 'bg-slate-400' }
const TRIGGER = { surprise: 'Surprise check', customer: 'Customer check', practice: 'Practice' }

export function StatusTimeline({ items, onSelect }: { items: Outcome[]; onSelect?: (o: Outcome) => void }) {
  if (!items.length) return <p className="text-sm text-slate-500">No checks yet.</p>
  return (
    <ol className="relative space-y-3 border-l-2 border-slate-200 pl-5">
      {items.map((o) => (
        <li key={o.auditId} className="relative">
          <span className={`absolute -left-[27px] top-1.5 h-3 w-3 rounded-full ring-4 ring-white ${DOT[o.tone]}`} />
          <button
            type="button"
            disabled={!onSelect}
            onClick={() => onSelect?.(o)}
            className="text-left disabled:cursor-default"
          >
            <div className="text-sm font-semibold text-slate-900">{o.label}</div>
            <div className="text-xs text-slate-500">
              {TRIGGER[o.trigger]} · {fmtDate(o.at)}
            </div>
          </button>
        </li>
      ))}
    </ol>
  )
}
