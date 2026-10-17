const IST = 'Asia/Kolkata'

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', { timeZone: IST, day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { timeZone: IST, day: 'numeric', month: 'short', year: 'numeric' })
}

export function ago(iso?: string | null): string {
  if (!iso) return 'never'
  const sec = (Date.now() - new Date(iso).getTime()) / 1000
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)} h ago`
  const d = Math.floor(sec / 86400)
  return d === 1 ? '1 day ago' : `${d} days ago`
}

export function mmss(totalSec: number): string {
  const s = Math.max(0, Math.round(totalSec))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export function parseMmss(value?: string | null): number {
  if (!value) return 0
  return value.split(':').reduce((acc, p) => acc * 60 + (parseFloat(p) || 0), 0)
}

export function secondsUntil(iso?: string | null): number {
  if (!iso) return 0
  return Math.max(0, (new Date(iso).getTime() - Date.now()) / 1000)
}
