import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Countdown } from '../../components/Countdown'
import { firebaseEnabled, uploadRecording, watchAuditDoc } from '../../firebase'
import { api, ApiError } from '../../lib/api'
import { useConfig } from '../../lib/config'
import { hindiPrompt } from '../../lib/hindi'
import { useStoredState } from '../../lib/hooks'
import { getLocation, openCamera, Recorder, stopStream } from '../../lib/recorder'
import type { Audit, Instruction } from '../../lib/types'

type Phase = 'intro' | 'starting' | 'recording' | 'uploading' | 'analyzing' | 'error'

const SAMPLES = [
  { id: 'messy', label: 'Messy kitchen', hint: 'Raw meat above cooked food, open dustbin, dirty counter' },
  { id: 'clean', label: 'Clean kitchen', hint: 'Same kitchen after fixing the problems' },
  { id: 'too_perfect', label: 'Too-perfect kitchen', hint: 'Spotless and inactive during a busy hour' },
] as const

const FINAL = ['scored', 'inconclusive', 'flagged', 'under_review', 'resolved']

export default function LiveAudit() {
  const { auditId = '' } = useParams()
  const navigate = useNavigate()
  const { demo } = useConfig()
  const [audit, setAudit] = useState<Audit | null>(null)
  const [phase, setPhase] = useState<Phase>('intro')
  const [error, setError] = useState<string | null>(null)
  const [instruction, setInstruction] = useState<Instruction | null>(null)
  const [deadline, setDeadline] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [busy, setBusy] = useState(false)
  const [voice, setVoice] = useStoredState<'off' | 'en' | 'hi'>('kp_voice', 'en')

  const videoEl = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const recorder = useRef<Recorder | null>(null)

  // load audit; leave if it's already done
  useEffect(() => {
    api
      .audit(auditId)
      .then((a) => {
        setAudit(a)
        if (FINAL.includes(a.status)) navigate(`/owner/report/${auditId}`, { replace: true })
        else if (a.status === 'uploaded' || a.status === 'analyzing') setPhase('analyzing')
        else if (a.status === 'expired') {
          setError('This audit expired: it was not started or finished in time, so it was recorded as a missed check.')
          setPhase('error')
        }
      })
      .catch((e) => {
        setError(e.message)
        setPhase('error')
      })
    return () => stopStream(stream.current)
  }, [auditId, navigate])

  // wait for analysis, then open the report
  useEffect(() => {
    if (phase !== 'analyzing') return
    const check = () =>
      api.audit(auditId).then((a) => {
        setAudit(a)
        if (FINAL.includes(a.status)) navigate(`/owner/report/${auditId}`, { replace: true })
      })
    const unsub = watchAuditDoc(auditId, () => void check())
    const t = window.setInterval(check, 2500)
    return () => {
      unsub?.()
      window.clearInterval(t)
    }
  }, [phase, auditId, navigate])

  // read the instruction aloud in English or Hindi (SHOULD #12)
  useEffect(() => {
    if (!instruction || voice === 'off' || !('speechSynthesis' in window)) return
    const hi = voice === 'hi' ? hindiPrompt(instruction) : null
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(hi ?? instruction.prompt)
    u.lang = hi ? 'hi-IN' : 'en-IN'
    const match = window.speechSynthesis.getVoices().find((v) => v.lang.replace('_', '-').startsWith(u.lang.slice(0, 2)))
    if (match) u.voice = match
    window.speechSynthesis.speak(u)
  }, [instruction, voice])

  async function startCamera() {
    setPhase('starting')
    setError(null)
    try {
      const s = await openCamera()
      stream.current = s
      const gps = await getLocation()
      const res = await api.start(auditId, gps)
      recorder.current = new Recorder(s)
      recorder.current.start()
      setInstruction(res.instruction)
      setDeadline(res.finishDeadlineAt)
      setPhase('recording')
      requestAnimationFrame(() => {
        if (videoEl.current) {
          videoEl.current.srcObject = s
          videoEl.current.play().catch(() => {})
        }
      })
    } catch (e) {
      stopStream(stream.current)
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof DOMException && e.name === 'NotAllowedError'
            ? 'Camera permission was denied. Allow camera and microphone access in your browser settings and try again.'
            : `Could not open the camera: ${e instanceof Error ? e.message : e}`
      setError(msg)
      setPhase(e instanceof ApiError && e.status === 410 ? 'error' : 'intro')
    }
  }

  async function next() {
    if (!instruction || !recorder.current || busy) return
    setBusy(true)
    try {
      const res = await api.advance(auditId, recorder.current.elapsed(), instruction.index)
      if (res.done) await finish()
      else setInstruction(res.instruction!)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
      if (e instanceof ApiError && e.status === 410) {
        stopStream(stream.current)
        setPhase('error')
      }
    } finally {
      setBusy(false)
    }
  }

  async function finish() {
    const rec = recorder.current!
    const duration = rec.elapsed()
    const blob = await rec.stop()
    stopStream(stream.current)
    window.speechSynthesis?.cancel()
    setPhase('uploading')
    try {
      const path = firebaseEnabled
        ? await uploadRecording(auditId, blob, setProgress)
        : (await api.uploadLocal(auditId, blob)).videoPath
      setProgress(100)
      await api.complete(auditId, path, rec.mimeType, duration)
      setPhase('analyzing')
    } catch (e) {
      setError(`Upload failed: ${e instanceof Error ? e.message : e}`)
      setPhase('error')
    }
  }

  async function pickSample(sample: (typeof SAMPLES)[number]['id']) {
    setBusy(true)
    setError(null)
    try {
      await api.demoSample(auditId, sample)
      setPhase('analyzing')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  if (phase === 'recording' || phase === 'starting') {
    const live = instruction?.kind === 'liveness'
    return (
      <div className="fixed inset-0 z-[60] flex flex-col bg-black text-white">
        <video ref={videoEl} muted playsInline className="absolute inset-0 h-full w-full object-cover" />
        <div className="relative z-10 p-3 pt-[max(env(safe-area-inset-top),12px)]">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-600 px-2.5 py-1">
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" /> REC
            </span>
            {instruction && (
              <span className="rounded-full bg-black/60 px-2.5 py-1">
                Check {instruction.checkNumber} of {instruction.totalChecks}
              </span>
            )}
            <span className="ml-auto rounded-full bg-black/60 px-2.5 py-1">
              ⏱ <Countdown until={deadline} warnAt={45} />
            </span>
          </div>
          {instruction && (
            <div
              key={instruction.index}
              className={`mt-3 rounded-2xl p-4 shadow-xl ${live ? 'bg-amber-400 text-amber-950' : 'bg-black/75 text-white backdrop-blur'}`}
            >
              <div className="text-xs font-bold uppercase tracking-wider opacity-80">
                {live ? '✋ Liveness challenge — do this now' : 'Show this now'}
              </div>
              <div className="mt-1 text-xl font-bold leading-snug sm:text-2xl">{instruction.prompt}</div>
              {voice === 'hi' && hindiPrompt(instruction) && (
                <div lang="hi" className="mt-1 text-lg font-semibold leading-snug opacity-90">
                  {hindiPrompt(instruction)}
                </div>
              )}
            </div>
          )}
          {phase === 'starting' && <div className="mt-3 rounded-xl bg-black/70 p-3 text-center">Opening camera…</div>}
          {error && <div className="mt-3 rounded-xl bg-red-600 p-3 text-sm">{error}</div>}
        </div>
        <div className="relative z-10 mt-auto space-y-2 p-3 pb-[max(env(safe-area-inset-bottom),16px)]">
          <p className="text-center text-xs text-white/80">Keep faces out of frame · keep recording continuously</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setVoice(voice === 'off' ? 'en' : voice === 'en' ? 'hi' : 'off')}
              className="btn min-w-[4.5rem] bg-black/60 text-sm text-white"
              aria-label={`Spoken prompts: ${{ off: 'off', en: 'English', hi: 'Hindi' }[voice]}. Tap to change.`}
            >
              {{ off: '🔇', en: '🔊 EN', hi: '🔊 हि' }[voice]}
            </button>
            <button type="button" onClick={next} disabled={busy || !instruction} className="btn flex-1 bg-white text-xl text-slate-900">
              {busy ? '…' : 'Done — next'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (phase === 'uploading' || phase === 'analyzing') {
    return (
      <div className="page max-w-md text-center">
        <div className="card">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-brand-200 border-t-brand-700" />
          {phase === 'uploading' ? (
            <>
              <h1 className="mt-4 text-xl font-bold">Uploading your recording…</h1>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-2 text-sm text-slate-500">{progress}%</p>
            </>
          ) : (
            <>
              <h1 className="mt-4 text-xl font-bold">Analyzing… (about a minute)</h1>
              <ul className="mx-auto mt-4 max-w-xs space-y-2 text-left text-sm">
                <li>✓ Recording received {audit?.sample && `(sample: ${audit.sample.replace('_', '-')})`}</li>
                <li className="animate-pulse">◌ Gemini auditor checks each instruction with timestamps</li>
                <li className="animate-pulse">◌ Integrity check: liveness, continuous take, same kitchen</li>
                <li className="text-slate-400">◌ Score, evidence tier and fix list</li>
              </ul>
            </>
          )}
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="page max-w-md">
        <div className="card text-center">
          <div className="text-4xl">⚠️</div>
          <p className="mt-2 font-semibold">{error}</p>
          <Link to="/owner" className="btn-primary mt-4">
            Back to dashboard
          </Link>
        </div>
      </div>
    )
  }

  // intro / permissions
  return (
    <div className="page max-w-md space-y-4">
      <Link to="/owner" className="text-sm font-semibold text-brand-700">
        ← Dashboard
      </Link>
      <div className="card">
        <div className="text-xs font-bold uppercase tracking-wider text-red-600">
          {audit?.trigger === 'practice' ? 'Practice audit' : audit?.trigger === 'customer' ? 'Customer check' : 'Surprise audit'}
        </div>
        <h1 className="mt-1 text-2xl font-extrabold">Live kitchen walk-through</h1>
        {audit?.status === 'requested' && (
          <p className="mt-1 text-sm text-slate-600">
            Start within <Countdown until={audit.startDeadlineAt} className="font-bold" />. You will then have 4 minutes.
          </p>
        )}
        <ul className="mt-4 space-y-2 text-sm text-slate-700">
          <li>📷 We need your <b>camera</b>, <b>microphone</b> and <b>location</b>.</li>
          <li>🎲 Checks appear <b>one at a time</b>. Show each one, then tap “Done — next”.</li>
          <li>✋ At some point you will get a quick gesture challenge.</li>
          <li>🙈 Please <b>keep faces out of frame</b>. We only look at hygiene items.</li>
          <li>🔒 The video is private, used only for this audit and review, and deleted after 90 days.</li>
        </ul>
        {error && <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <button type="button" onClick={startCamera} disabled={!audit} className="btn-primary mt-5 w-full text-lg">
          Allow camera & start
        </button>
      </div>

      {demo && (
        <div className="card border-amber-300 bg-amber-50">
          <div className="text-xs font-bold uppercase tracking-wider text-amber-800">Demo Mode</div>
          <h2 className="font-bold">Use a sample video instead of the camera</h2>
          <p className="text-sm text-amber-900">Recorded by the team following a fixed instruction timeline. Gemini analyses it for real.</p>
          <div className="mt-3 grid gap-2">
            {SAMPLES.map((s) => (
              <button
                key={s.id}
                type="button"
                disabled={busy || !audit}
                onClick={() => pickSample(s.id)}
                className="rounded-xl bg-white p-3 text-left ring-1 ring-amber-200 hover:ring-amber-400 disabled:opacity-50"
              >
                <div className="font-semibold">{s.label}</div>
                <div className="text-xs text-slate-600">{s.hint}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
