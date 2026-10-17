import { Link, useNavigate } from 'react-router-dom'
import { useTour } from '../components/Layout'
import { useConfig } from '../lib/config'

const ROLES = [
  {
    to: '/owner?r=r01',
    emoji: '👩‍🍳',
    title: 'Restaurant Owner',
    text: 'Answer surprise audit requests with a short live phone walk-through. Get a fix list and dispute wrong findings.',
  },
  {
    to: '/customer',
    emoji: '🛵',
    title: 'Customer (FoodieGo)',
    text: 'See a verified Kitchen Score before you order — and request a kitchen check while your food is being made.',
  },
  {
    to: '/inspector',
    emoji: '🕵️',
    title: 'Food Inspector',
    text: 'A ranked list of kitchens to visit first, with plain-language reasons and a review queue for disputes and staging flags.',
  },
]

const LAYERS = [
  ['⏱️', 'Unannounced', 'Random timing, 10 min to start, 4 min to finish'],
  ['🎲', 'One check at a time', 'Random checks revealed live by the server'],
  ['✋', 'Liveness challenge', '“Hold up 3 fingers in front of the stove”'],
  ['🍳', 'Real order on camera', 'Show order #4521 being made right now'],
  ['🔍', 'Integrity check', 'Gemini looks for cuts, a different kitchen, “too perfect”'],
  ['⚖️', 'Fair to owners', '“Not verified” ≠ fail; disputes go to a human'],
]

export default function Landing() {
  const navigate = useNavigate()
  const [, setTour] = useTour()
  const { config } = useConfig()
  return (
    <div>
      <section className="bg-gradient-to-b from-brand-900 to-brand-700 text-white">
        <div className="mx-auto max-w-5xl px-4 py-10 sm:py-16">
          <p className="text-sm font-semibold uppercase tracking-widest text-brand-200">Surprise kitchen audits · verified by Gemini</p>
          <h1 className="mt-3 max-w-3xl text-3xl font-extrabold leading-tight sm:text-5xl">
            See the kitchen before you order.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-brand-50 sm:text-lg">
            Customers never see where their food is cooked, and there will never be enough inspectors. KitchenProof turns any
            phone into an unannounced, AI-verified kitchen audit — making faking it every day, at random times, while real
            orders cook, harder than just keeping the kitchen clean.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setTour(0)
                navigate('/inspector')
              }}
              className="btn bg-white text-lg text-brand-900 hover:bg-brand-50"
            >
              ▶ Start the 2-minute demo tour
            </button>
            <Link to="/tour" className="btn text-white ring-1 ring-white/40 hover:bg-white/10">
              What the tour shows
            </Link>
          </div>
        </div>
      </section>

      <section className="page">
        <h2 className="h-section">Try it as</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {ROLES.map((r) => (
            <Link key={r.title} to={r.to} className="card group transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="text-4xl" aria-hidden>
                {r.emoji}
              </div>
              <h3 className="mt-3 text-lg font-bold group-hover:text-brand-700">{r.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{r.text}</p>
              <span className="mt-3 inline-block text-sm font-semibold text-brand-700">Open →</span>
            </Link>
          ))}
        </div>

        <h2 className="h-section mt-10">Why it is hard to fake</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {LAYERS.map(([icon, title, text]) => (
            <div key={title} className="rounded-xl bg-white p-3 ring-1 ring-slate-200">
              <div className="text-2xl" aria-hidden>
                {icon}
              </div>
              <div className="mt-1 font-semibold">{title}</div>
              <div className="text-xs text-slate-600">{text}</div>
            </div>
          ))}
        </div>

        <p className="mt-8 text-xs text-slate-500">
          FoodieGo is a made-up food delivery brand. All restaurants are fictional. Kitchen Scores are self-audits verified by
          AI — not an official FSSAI rating.
          {config.model && ` Model: ${config.model}.`}
        </p>
      </section>
    </div>
  )
}
