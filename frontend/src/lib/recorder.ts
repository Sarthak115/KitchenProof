/** Continuous in-app recording (getUserMedia + MediaRecorder). No gallery uploads. */

export function pickMimeType(): string {
  const candidates = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4;codecs=avc1', 'video/mp4']
  for (const type of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

export async function openCamera(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
    audio: true,
  })
}

export class Recorder {
  private chunks: Blob[] = []
  private recorder: MediaRecorder
  private startedAt = 0
  readonly mimeType: string

  constructor(stream: MediaStream) {
    const mime = pickMimeType()
    this.recorder = new MediaRecorder(stream, {
      ...(mime ? { mimeType: mime } : {}),
      videoBitsPerSecond: 2_000_000, // ~30 MB for 2 minutes of 720p
    })
    this.mimeType = (this.recorder.mimeType || mime || 'video/webm').split(';')[0]
    this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data)
  }

  start() {
    this.startedAt = performance.now()
    this.recorder.start(1000)
  }

  /** Seconds since recording started (used as the reveal offset of each instruction). */
  elapsed(): number {
    return this.startedAt ? (performance.now() - this.startedAt) / 1000 : 0
  }

  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      this.recorder.onstop = () => resolve(new Blob(this.chunks, { type: this.mimeType }))
      if (this.recorder.state !== 'inactive') this.recorder.stop()
      else resolve(new Blob(this.chunks, { type: this.mimeType }))
    })
  }
}

export function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((t) => t.stop())
}

export function getLocation(): Promise<{ lat: number; lng: number; accuracy: number } | undefined> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(undefined)
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: p.coords.accuracy }),
      () => resolve(undefined),
      { enableHighAccuracy: true, timeout: 8000 },
    )
  })
}
