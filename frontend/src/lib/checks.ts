// Mirrors backend/app/checks.py (labels for the UI).
import type { Severity } from './types'

export const CHECKS: Record<string, { label: string; severity: Severity }> = {
  pests: { label: 'No pests', severity: 'critical' },
  fridge_segregation: { label: 'Fridge: raw below cooked', severity: 'critical' },
  fridge_temp: { label: 'Fridge at 5 °C or colder', severity: 'high' },
  handwash: { label: 'Handwash sink with soap', severity: 'high' },
  handler_hygiene: { label: 'Cook hygiene (cap, gloves, apron)', severity: 'high' },
  order_prep: { label: 'Live order being prepared', severity: 'high' },
  dustbins: { label: 'Dustbins lidded', severity: 'medium' },
  surfaces: { label: 'Clean boards & counter', severity: 'medium' },
  drains: { label: 'Floor drain clean', severity: 'medium' },
  dry_storage: { label: 'Dry storage off the floor', severity: 'medium' },
  labels_expiry: { label: 'Ingredients in date', severity: 'medium' },
  oil_condition: { label: 'Frying oil condition', severity: 'medium' },
  walls_ceiling: { label: 'Walls & ceiling', severity: 'low' },
  fssai_board: { label: 'FSSAI licence displayed', severity: 'low' },
  pest_control_record: { label: 'Pest control record', severity: 'low' },
  water_source: { label: 'Drinking-water source', severity: 'low' },
}

export const checkLabel = (id: string) => CHECKS[id]?.label ?? id

export const SEVERITY_STYLE: Record<Severity, string> = {
  critical: 'bg-red-100 text-red-800 ring-red-200',
  high: 'bg-orange-100 text-orange-800 ring-orange-200',
  medium: 'bg-amber-50 text-amber-800 ring-amber-200',
  low: 'bg-slate-100 text-slate-700 ring-slate-200',
}

export const FLAG_LABELS: Record<string, string> = {
  liveness_ok: 'Liveness gesture matched',
  liveness_unclear: 'Liveness gesture unclear',
  liveness_failed: 'Liveness challenge failed',
  wrong_location: 'Recorded away from the kitchen',
  edited_video: 'Video looks edited',
  possible_cut: 'Possible cut in video',
  different_kitchen: 'Looks like a different kitchen',
  too_perfect: 'Too perfect for a busy hour',
  props_suspected: 'Items look placed for the camera',
  repeated_props: 'Same props in 3+ audits',
  too_fast: 'Finished suspiciously fast',
}
