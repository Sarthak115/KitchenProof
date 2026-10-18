import type { AppConfig, Audit, Instruction, Order, Restaurant, ReviewItem } from './types'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function call<T>(method: string, path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body instanceof FormData ? headers : { 'Content-Type': 'application/json', ...headers },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let msg = res.statusText
    try {
      const data = await res.json()
      msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg)
  }
  return res.json() as Promise<T>
}

const get = <T,>(p: string) => call<T>('GET', p)

/** Demo shows a short list: each restaurant illustrates one part of the story. */
export const FEATURED = ['r01', 'r03', 'r07', 'r11', 'r05']
const featured = (id: string) => FEATURED.includes(id)
const post = <T,>(p: string, b?: unknown) => call<T>('POST', p, b ?? {})

export const api = {
  config: () => get<AppConfig>('/config'),
  restaurants: () =>
    get<{ restaurants: Restaurant[] }>('/restaurants').then((r) => r.restaurants.filter((x) => featured(x.id))),
  restaurant: (id: string) => get<Restaurant>(`/restaurants/${id}`),
  restaurantAudits: (id: string) => get<{ audits: Audit[] }>(`/restaurants/${id}/audits`).then((r) => r.audits),
  audit: (id: string) => get<Audit>(`/audits/${id}`),
  createAudit: (body: { restaurantId: string; trigger: 'practice' | 'customer'; orderId?: string; customerId?: string }) =>
    post<{ auditId: string; startDeadlineAt: string }>('/audits', body),
  start: (id: string, gps?: { lat: number; lng: number; accuracy?: number }) =>
    post<{ instruction: Instruction; finishDeadlineAt: string }>(`/audits/${id}/start`, { gps }),
  advance: (id: string, offsetSec: number, fromIndex: number) =>
    post<{ done: boolean; instruction?: Instruction }>(`/audits/${id}/advance`, { offsetSec, fromIndex }),
  complete: (id: string, videoPath: string, videoMime: string, durationSec: number) =>
    post<{ status: string }>(`/audits/${id}/complete`, { videoPath, videoMime, durationSec }),
  demoSample: (id: string, sample: 'messy' | 'clean' | 'too_perfect') => post(`/audits/${id}/demo-sample`, { sample }),
  uploadLocal: (id: string, blob: Blob) => {
    const fd = new FormData()
    fd.append('file', blob, `recording.${blob.type.includes('mp4') ? 'mp4' : 'webm'}`)
    return call<{ videoPath: string }>('POST', `/audits/${id}/upload`, fd)
  },
  dispute: (auditId: string, findingId: string, reason: string) =>
    post<Audit>(`/findings/${auditId}/${findingId}/dispute`, { reason }),
  reviewQueue: () => get<{ items: ReviewItem[] }>('/review').then((r) => r.items.filter((q) => featured(q.restaurantId))),
  resolveReview: (itemId: string, decision: string) => post<Audit>(`/review/${itemId}`, { decision }),
  surprise: (restaurantId?: string) =>
    post<{ auditId: string; restaurantId: string; restaurantName: string }>('/inspector/surprise', {
      restaurantId: restaurantId ?? FEATURED[Math.floor(Math.random() * FEATURED.length)],
    }),
  inspectorVisit: (restaurantId: string, outcome: 'confirmed' | 'contradicts') =>
    post<Restaurant>('/inspector/visit', { restaurantId, outcome }),
  ranking: () =>
    get<{ restaurants: Restaurant[] }>('/risk/ranking').then((r) =>
      r.restaurants.filter((x) => featured(x.id)).map((x, i) => ({ ...x, rank: i + 1 })),
    ),
  expire: () => post<{ expired: string[] }>('/maintenance/expire'),
  order: (id: string) => get<Order>(`/orders/${id}`),
  demoOrder: (restaurantId: string, customerId: string) => post<{ orderId: string }>('/demo/order', { restaurantId, customerId }),
  demoReset: () => post('/demo/reset'),
  reaudit: (id: string) => post<{ auditId: string }>(`/audits/${id}/reaudit`),
}
