export type Tier = 'bronze' | 'silver' | 'gold'
export type BadgeState = 'scored' | 'failed_verification' | 'not_recently_verified' | 'unverified'
export type FindingStatus = 'pass' | 'fail' | 'not_verified'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Trigger = 'surprise' | 'customer' | 'practice'

export interface Clip {
  auditId?: string
  checkId: string
  startSec: number
  endSec: number
  videoPath?: string
  verifiedAt?: string
}

export interface Outcome {
  auditId: string
  trigger: Trigger
  at: string
  label: string
  tone: 'good' | 'warn' | 'bad' | 'neutral'
}

export interface Restaurant {
  id: string
  name: string
  cuisine: string
  rating: number
  address: string
  area: string
  geo: { lat: number; lng: number }
  fssaiLicense: string
  ordersLastHour: number
  publicScore: number | null
  scoreDecayed?: boolean
  badgeState: BadgeState
  tier: Tier
  lastCountedAuditAt: string | null
  lastIssuesFound: number | null
  missedChecks30d: number
  openDisputes: number
  underReview: boolean
  riskScore: number
  riskReasons: string[]
  evidenceClips: Clip[]
  inspectorVisitAt: string | null
  failedVerificationUntil: string | null
  timeline?: Outcome[]
  activeOrder?: Order | null
  rank?: number
}

export interface Finding {
  id: string
  checkId: string
  status: FindingStatus
  effectiveStatus: FindingStatus
  severity: Severity
  reason: string
  timestamp: string
  confidence: number
  publicEligible: boolean
  needsReview: boolean
  disputed: boolean
  dispute: { reason: string; at: string } | null
  review: { decision: 'upheld' | 'overturned'; by: string; at: string } | null
}

export interface IntegrityFlag {
  code: string
  detail: string
  confidence: number
}

export interface Instruction {
  kind: 'check' | 'liveness'
  checkId?: string
  prompt: string
  severity?: Severity
  index: number
  checkNumber: number
  totalChecks: number
}

export interface Audit {
  id: string
  restaurantId: string
  restaurantName?: string
  trigger: Trigger
  orderId: string | null
  requestedBy: string
  status: string
  outcome?: string
  createdAt: string
  startDeadlineAt: string
  startedAt: string | null
  finishDeadlineAt: string | null
  completedAt: string | null
  requestedChecks: number
  revealedChecks: { checkId: string; prompt: string; offsetSec: number }[]
  liveness: { prompt: string; offsetSec: number; observed?: { observed: string; fingersCounted: number; nearObject: string; timestamp: string; confidence: number } } | null
  distanceFromRegisteredM?: number
  videoPath?: string
  videoMime?: string
  durationSec?: number
  score?: number
  coverage?: number
  counted?: boolean
  issuesFound?: number
  integrity?: { verdict: 'clean' | 'suspicious' | 'failed'; flags: IntegrityFlag[]; originalVerdict?: string; review?: { decision: string } }
  evidenceClips?: Clip[]
  observedItems?: { label: string; batchOrExpiry: string; state: string }[]
  coach?: { en: string[]; hi: string[]; or: string[] } | null
  modelId?: string
  promptVersion?: string
  usedCachedResult?: boolean
  analysisError?: string | null
  sample?: string
  voided?: boolean
  ordersLastHourAtAudit?: number
  findings?: Finding[]
  currentInstruction?: Instruction | null
  outcomeLabel?: Outcome
}

export interface Order {
  id: string
  restaurantId: string
  restaurantName?: string
  customerId: string
  items: string[]
  status: string
  createdAt: string
  spotCheckAuditId?: string
  spotCheck?: Outcome & { status: string; score?: number; startDeadlineAt: string; counted?: boolean }
}

export interface ReviewItem {
  id: string
  type: 'dispute' | 'integrity'
  auditId: string
  findingId?: string
  restaurantId: string
  restaurantName?: string
  detail: string
  createdAt: string
  status: 'open' | 'resolved'
  decision?: string
  audit: Partial<Audit>
  finding?: Finding
}

export interface AppConfig {
  demoMode: boolean
  model: string
  geminiAvailable: boolean
  promptVersion: string
  heroRestaurantId: string
  startWindowMin: number
  finishWindowMin: number
  customerChecksPerDay: number
  customerCooldownDays: number
  demoResetOpen?: boolean
}
