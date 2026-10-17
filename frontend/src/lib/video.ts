import { firebaseEnabled, storageUrl } from '../firebase'

const SAMPLE_FILES: Record<string, string> = {
  messy: '/demo/messy_kitchen.mp4',
  clean: '/demo/clean_kitchen.mp4',
  too_perfect: '/demo/too_perfect_kitchen.mp4',
}

/** Map a stored videoPath to a playable URL. */
export async function videoUrl(path?: string | null): Promise<string | null> {
  if (!path) return null
  if (path.startsWith('demo:')) return SAMPLE_FILES[path.slice(5)] ?? null
  if (path.startsWith('local:')) return `/api/media/${path.slice(6)}`
  if (firebaseEnabled) {
    try {
      return await storageUrl(path)
    } catch {
      return null
    }
  }
  return null
}
