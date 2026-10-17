/**
 * Firebase (Auth, Firestore, Cloud Storage). Enabled when VITE_FIREBASE_* env vars are set
 * (frontend/.env.production). Without them the app still works for local development:
 * realtime updates fall back to polling and uploads go through the API.
 */
import { initializeApp, type FirebaseApp } from 'firebase/app'
import { getAuth, signInAnonymously, type Auth } from 'firebase/auth'
import { collection, doc, getFirestore, onSnapshot, query, where, type Firestore } from 'firebase/firestore'
import { getDownloadURL, getStorage, ref, uploadBytesResumable, type FirebaseStorage } from 'firebase/storage'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const firebaseEnabled = Boolean(config.apiKey && config.projectId)

let app: FirebaseApp | null = null
let auth: Auth | null = null
let db: Firestore | null = null
let storage: FirebaseStorage | null = null

if (firebaseEnabled) {
  app = initializeApp(config)
  auth = getAuth(app)
  db = getFirestore(app)
  storage = getStorage(app)
}

let signInPromise: Promise<string | null> | null = null

/** Anonymous sign-in: no login for judges, but Storage/Firestore rules still see a uid. */
export function ensureSignedIn(): Promise<string | null> {
  if (!auth) return Promise.resolve(null)
  if (!signInPromise) {
    signInPromise = signInAnonymously(auth)
      .then((cred) => cred.user.uid)
      .catch((err) => {
        console.warn('Anonymous sign-in failed', err)
        signInPromise = null
        return null
      })
  }
  return signInPromise
}

/** Calls `onChange` whenever the audit document changes. Returns an unsubscribe fn, or null without Firebase. */
export function watchAuditDoc(auditId: string, onChange: () => void): (() => void) | null {
  if (!db) return null
  return onSnapshot(doc(db, 'audits', auditId), onChange, (err) => console.warn('listener', err))
}

export function watchRestaurantAudits(restaurantId: string, onChange: () => void): (() => void) | null {
  if (!db) return null
  return onSnapshot(
    query(collection(db, 'audits'), where('restaurantId', '==', restaurantId)),
    onChange,
    (err) => console.warn('listener', err),
  )
}

export function watchRestaurantDoc(restaurantId: string, onChange: () => void): (() => void) | null {
  if (!db) return null
  return onSnapshot(doc(db, 'restaurants', restaurantId), onChange, (err) => console.warn('listener', err))
}

/** Resumable upload to audits/{auditId}/recording.{ext}. Returns the storage path. */
export async function uploadRecording(auditId: string, blob: Blob, onProgress: (pct: number) => void): Promise<string> {
  if (!storage) throw new Error('Storage not configured')
  await ensureSignedIn()
  const ext = blob.type.includes('mp4') ? 'mp4' : 'webm'
  const path = `audits/${auditId}/recording.${ext}`
  const task = uploadBytesResumable(ref(storage, path), blob, { contentType: blob.type || `video/${ext}` })
  await new Promise<void>((resolve, reject) => {
    task.on(
      'state_changed',
      (snap) => onProgress(Math.round((snap.bytesTransferred / snap.totalBytes) * 100)),
      reject,
      () => resolve(),
    )
  })
  return path
}

export async function storageUrl(path: string): Promise<string> {
  if (!storage) throw new Error('Storage not configured')
  await ensureSignedIn()
  return getDownloadURL(ref(storage, path))
}
