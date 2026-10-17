import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Fetch data and keep it fresh. With Firebase configured, `watch` subscribes to a Firestore
 * listener that triggers a refetch on every change; polling stays on as a slow safety net.
 */
export function useLive<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  opts: { intervalMs?: number; watch?: (onChange: () => void) => (() => void) | null } = {},
) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const reload = useCallback(async () => {
    try {
      const value = await fetcherRef.current()
      setData(value)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    setData(null)
    reload()
    const unsub = opts.watch?.(() => void reload()) ?? null
    const interval = opts.intervalMs ?? 4000
    const timer = interval > 0 ? window.setInterval(reload, unsub ? Math.max(interval, 15000) : interval) : 0
    return () => {
      unsub?.()
      if (timer) window.clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, error, reload, setData }
}

/** Re-render every `ms` (for countdowns). */
export function useTick(ms = 1000) {
  const [, setN] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => setN((n) => n + 1), ms)
    return () => window.clearInterval(t)
  }, [ms])
}

const memory = new Map<string, unknown>()

/** State persisted in localStorage and shared between every component using the same key. */
export function useStoredState<T>(key: string, initial: T): [T, (v: T) => void] {
  const read = useCallback((): T => {
    if (memory.has(key)) return memory.get(key) as T
    try {
      const raw = localStorage.getItem(key)
      return raw ? (JSON.parse(raw) as T) : initial
    } catch {
      return initial
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  const [value, setValue] = useState<T>(read)

  useEffect(() => {
    const onChange = (e: Event) => {
      if ((e as CustomEvent<string>).detail === key) setValue(read())
    }
    window.addEventListener('kp-storage', onChange)
    return () => window.removeEventListener('kp-storage', onChange)
  }, [key, read])

  const set = useCallback(
    (v: T) => {
      setValue(v)
      memory.set(key, v)
      try {
        localStorage.setItem(key, JSON.stringify(v))
      } catch {
        /* storage unavailable */
      }
      window.dispatchEvent(new CustomEvent('kp-storage', { detail: key }))
    },
    [key],
  )
  return [value, set]
}
