import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { videoUrl } from '../lib/video'

export interface EvidencePlayerHandle {
  seek: (sec: number, endSec?: number) => void
}

/** Video player that can jump to a finding's timestamp. Shows a placeholder if the video is missing. */
export const EvidencePlayer = forwardRef<EvidencePlayerHandle, { path?: string | null; className?: string; label?: string }>(
  function EvidencePlayer({ path, className = '', label }, ref) {
    const video = useRef<HTMLVideoElement>(null)
    const [src, setSrc] = useState<string | null>(null)
    const [failed, setFailed] = useState(false)
    const stopAt = useRef<number | null>(null)

    useEffect(() => {
      setFailed(false)
      let alive = true
      videoUrl(path).then((u) => alive && (setSrc(u), setFailed(!u)))
      return () => {
        alive = false
      }
    }, [path])

    useImperativeHandle(ref, () => ({
      seek(sec, endSec) {
        const v = video.current
        if (!v) return
        stopAt.current = endSec ?? null
        v.currentTime = sec
        v.play().catch(() => {})
        v.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      },
    }))

    if (failed || !src) {
      return (
        <div className={`flex aspect-video items-center justify-center rounded-xl bg-slate-800 p-4 text-center text-sm text-slate-300 ${className}`}>
          {path ? 'Video not available here (raw videos are kept private and deleted after 90 days).' : 'No video'}
        </div>
      )
    }
    return (
      <div className={className}>
        <video
          ref={video}
          src={src}
          controls
          playsInline
          muted
          preload="metadata"
          onError={() => setFailed(true)}
          onLoadedMetadata={(e) => fixDuration(e.currentTarget)}
          onTimeUpdate={(e) => {
            if (stopAt.current != null && e.currentTarget.currentTime >= stopAt.current) {
              e.currentTarget.pause()
              stopAt.current = null
            }
          }}
          className="aspect-video w-full rounded-xl bg-black object-contain"
        />
        {label && <div className="mt-1 text-xs text-slate-500">{label}</div>}
      </div>
    )
  },
)

/**
 * Videos recorded with MediaRecorder (webm) have no duration in their header, so Chrome reports
 * Infinity and the scrubber does not work. Seeking far past the end makes the browser compute it.
 */
function fixDuration(v: HTMLVideoElement) {
  if (v.duration !== Infinity) return
  const restore = () => {
    v.removeEventListener('durationchange', restore)
    v.currentTime = 0
  }
  v.addEventListener('durationchange', restore)
  v.currentTime = 1e101
}

/** A short public clip (3–5 s) that loops between start and end. */
export function ClipPlayer({ path, startSec, endSec, caption }: { path?: string; startSec: number; endSec: number; caption: string }) {
  const [src, setSrc] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    videoUrl(path).then((u) => (u ? setSrc(`${u}#t=${startSec},${endSec}`) : setFailed(true)))
  }, [path, startSec, endSec])
  return (
    <figure className="overflow-hidden rounded-xl bg-slate-900">
      {src && !failed ? (
        <video
          src={src}
          muted
          playsInline
          autoPlay
          preload="metadata"
          onError={() => setFailed(true)}
          onTimeUpdate={(e) => {
            if (e.currentTarget.currentTime >= endSec || e.currentTarget.currentTime < startSec - 0.5) e.currentTarget.currentTime = startSec
          }}
          className="aspect-video w-full object-cover"
        />
      ) : (
        <div className="flex h-20 items-center justify-center p-2 text-center text-xs text-slate-400">Clip preview unavailable</div>
      )}
      <figcaption className="px-2 py-1.5 text-xs font-medium text-slate-100">✓ {caption}</figcaption>
    </figure>
  )
}
