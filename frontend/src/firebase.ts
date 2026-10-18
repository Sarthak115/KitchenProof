/**
 * Firebase (Auth, Firestore, Cloud Storage). Enabled when VITE_FIREBASE_* env vars are set
 * (frontend/.env.production). Without them the app still works for local development:
 * realtime updates fall back to polling and uploads go through the API.
 */
import { initializeApp, type FirebaseApp } from 'firebase/app'
import { connectAuthEmulator, getAuth, signInAnonymously, type Auth } from 'firebase/auth'
import {
  collection,
  connectFirestoreEmulator,
  doc,
  getFirestore,
  onSnapshot,
  query,
  where,
  type DocumentReference,
  type Firestore,
  type Query,
} from 'firebase/firestore'
import { connectStorageEmulator, getDownloadURL, getStorage, ref, uploadBytesResumable, type FirebaseStorage } from 'firebase/storage'

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
  // Local Firebase emulators (firebase emulators:start), for testing without a cloud project
  if (import.meta.env.VITE_USE_EMULATORS === 'true') {
    const host = location.hostname
    connectAuthEmulator(auth, `http://${host}:9099`, { disableWarnings: true })
    connectFirestoreEmulator(db, host, 8085)
    connectStorageEmulator(storage, host, 9199)
  }
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

type Target = DocumentReference | Query
export type Watcher = (onChange: () => void, onError: () => void) => (() => void) | null

/**
 * Subscribe to a Firestore document or query after anonymous sign-in has finished (the rules
 * only let signed-in users read audits). Returns an unsubscribe fn, or null without Firebase.
 */
function listen(target: () => Target, onChange: () => void, onError: () => void): (() => void) | null {
  if (!db) return null
  let unsub: (() => void) | null = null
  let cancelled = false
  ensureSignedIn().then((uid) => {
    if (cancelled) return
    if (!uid) return onError()
    unsub = onSnapshot(target() as never, onChange, (err: unknown) => {
      console.warn('Firestore listener failed', err)
      onError()
    })
  })
  return () => {
    cancelled = true
    unsub?.()
  }
}

export const watchAuditDoc = (auditId: string): Watcher => (onChange, onError) =>
  listen(() => doc(db!, 'audits', auditId), onChange, onError)

export const watchRestaurantAudits = (restaurantId: string): Watcher => (onChange, onError) =>
  listen(() => query(collection(db!, 'audits'), where('restaurantId', '==', restaurantId)), onChange, onError)

export const watchRestaurantDoc = (restaurantId: string): Watcher => (onChange, onError) =>
  listen(() => doc(db!, 'restaurants', restaurantId), onChange, onError)

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
