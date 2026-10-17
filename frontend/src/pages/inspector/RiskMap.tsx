import { useEffect, useRef, useState } from 'react'
import type { Restaurant } from '../../lib/types'

const KEY = import.meta.env.VITE_MAPS_API_KEY

declare global {
  interface Window {
    google?: any // eslint-disable-line @typescript-eslint/no-explicit-any
    __kpMapsLoading?: Promise<void>
  }
}

function loadMaps(): Promise<void> {
  if (window.google?.maps) return Promise.resolve()
  if (!window.__kpMapsLoading) {
    window.__kpMapsLoading = new Promise((resolve, reject) => {
      const s = document.createElement('script')
      s.src = `https://maps.googleapis.com/maps/api/js?key=${KEY}&v=weekly`
      s.async = true
      s.onload = () => resolve()
      s.onerror = reject
      document.head.appendChild(s)
    })
  }
  return window.__kpMapsLoading
}

const color = (risk: number) => (risk >= 50 ? '#dc2626' : risk >= 25 ? '#f59e0b' : '#10b981')

/** Google Maps view of the ranking (SHOULD #13). Hidden when no Maps API key is configured. */
export function RiskMap({ restaurants }: { restaurants: Restaurant[] }) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<any>(null) // eslint-disable-line @typescript-eslint/no-explicit-any
  const markers = useRef<any[]>([]) // eslint-disable-line @typescript-eslint/no-explicit-any
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!KEY || !el.current || !restaurants.length) return
    loadMaps()
      .then(() => {
        const g = window.google
        if (!map.current) {
          map.current = new g.maps.Map(el.current, { center: { lat: 20.29, lng: 85.83 }, zoom: 12, disableDefaultUI: true, zoomControl: true })
        }
        markers.current.forEach((m) => m.setMap(null))
        markers.current = restaurants.map(
          (r) =>
            new g.maps.Marker({
              map: map.current,
              position: r.geo,
              title: `#${r.rank} ${r.name} — risk ${r.riskScore}`,
              label: { text: String(r.rank), color: 'white', fontWeight: '700' },
              icon: { path: g.maps.SymbolPath.CIRCLE, scale: 13, fillColor: color(r.riskScore), fillOpacity: 1, strokeColor: 'white', strokeWeight: 2 },
            }),
        )
      })
      .catch(() => setFailed(true))
  }, [restaurants])

  if (!KEY || failed) return null
  return <div ref={el} className="h-64 w-full overflow-hidden rounded-2xl border border-slate-200 sm:h-80" />
}
