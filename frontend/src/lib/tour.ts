export interface TourStep {
  title: string
  body: string
  route: string | null
}

export const TOUR: TourStep[] = [
  {
    title: 'Inspector sends a surprise check',
    body: 'Press “Trigger surprise audit” on Kalinga Biryani House.',
    route: '/inspector',
  },
  {
    title: 'The owner gets 10 minutes',
    body: 'Press “Start audit now”.',
    route: '/owner?r=r01',
  },
  {
    title: 'Live audit',
    body: 'Pick “Messy kitchen”. Gemini analyses the video.',
    route: null,
  },
  {
    title: 'AI report with evidence',
    body: 'Tap ▶ on a finding to see the moment in the video.',
    route: null,
  },
  {
    title: 'Customer checks during an order',
    body: 'Press “Order & request a kitchen check”, then “Respond as the kitchen” → “Clean kitchen”.',
    route: '/customer/restaurant/r01',
  },
  {
    title: 'Inspector review',
    body: 'Open the Review queue to see a staged “too perfect” kitchen.',
    route: '/inspector',
  },
]
