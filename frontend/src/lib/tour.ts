export interface TourStep {
  title: string
  body: string
  route: string | null
}

export const TOUR: TourStep[] = [
  {
    title: 'Inspector triggers a surprise audit',
    body: 'You are a food safety inspector. Press “Trigger surprise audit” on Kalinga Biryani House. The owner does not know when this will happen.',
    route: '/inspector',
  },
  {
    title: 'The owner sees a countdown',
    body: 'The kitchen must start within 10 minutes and finish within 4, or it becomes a public missed check. Press “Start audit now”.',
    route: '/owner?r=r01',
  },
  {
    title: 'Live audit, one random check at a time',
    body: 'Checks are revealed one by one, with a random finger-count liveness challenge. For the demo, pick “Messy kitchen” under “Use a sample video” — Gemini analyses it for real.',
    route: null,
  },
  {
    title: 'Report with timestamped evidence',
    body: 'Every finding has a timestamp: tap ▶ to jump to the moment in the video. “Not verified” lowers coverage, never the score. Try “Dispute” on a finding.',
    route: null,
  },
  {
    title: 'Customer badge + spot check during an order',
    body: 'On FoodieGo the badge updated. Press “Order & request a kitchen check”, then “Respond as the kitchen” and pick “Clean kitchen”. Two passed checks → Silver.',
    route: '/customer/restaurant/r01',
  },
  {
    title: 'Inspector ranking + review queue',
    body: 'Kitchens are ranked with plain-language reasons. Open the Review queue: Dalma Junction’s spotless, empty kitchen during a busy hour was flagged as possibly staged.',
    route: '/inspector',
  },
]
