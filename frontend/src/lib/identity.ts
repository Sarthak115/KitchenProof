import { ensureSignedIn } from '../firebase'

/** Customer identity: the anonymous Firebase uid, or a random id kept in this browser. */
export async function customerId(): Promise<string> {
  const uid = await ensureSignedIn()
  if (uid) return uid
  try {
    let id = localStorage.getItem('kp_customer_id')
    if (!id) {
      id = `cust-${Math.random().toString(36).slice(2, 10)}`
      localStorage.setItem('kp_customer_id', id)
    }
    return id
  } catch {
    return `cust-${Math.random().toString(36).slice(2, 10)}`
  }
}
