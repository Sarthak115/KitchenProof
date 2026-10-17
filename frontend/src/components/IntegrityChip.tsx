const STYLES = {
  clean: { label: 'Integrity: clean', cls: 'bg-emerald-50 text-emerald-800 ring-emerald-200', icon: '✓' },
  suspicious: { label: 'Integrity: under review', cls: 'bg-amber-50 text-amber-800 ring-amber-200', icon: '?' },
  failed: { label: 'Failed verification', cls: 'bg-red-50 text-red-800 ring-red-200', icon: '✕' },
} as const

export function IntegrityChip({ verdict }: { verdict?: keyof typeof STYLES }) {
  if (!verdict) return null
  const s = STYLES[verdict]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${s.cls}`}>
      <span aria-hidden>{s.icon}</span>
      {s.label}
    </span>
  )
}
