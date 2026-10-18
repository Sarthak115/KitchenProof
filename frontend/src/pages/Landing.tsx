import { Link, useNavigate } from 'react-router-dom'
import { useTour } from '../components/Layout'

const ROLES = [
  { to: '/owner?r=r01', emoji: '👩‍🍳', title: 'Restaurant Owner', text: 'Answer a surprise kitchen check' },
  { to: '/customer', emoji: '🛵', title: 'Customer', text: 'See the kitchen before you order' },
  { to: '/inspector', emoji: '🕵️', title: 'Food Inspector', text: 'Know which kitchen to visit first' },
]

export default function Landing() {
  const navigate = useNavigate()
  const [, setTour] = useTour()
  return (
    <div>
      <section className="bg-gradient-to-b from-brand-900 to-brand-700 text-white">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:py-20">
          <h1 className="max-w-3xl text-3xl font-extrabold leading-tight sm:text-5xl">See the kitchen before you order.</h1>
          <p className="mt-3 text-lg text-brand-50">Surprise phone audits, verified by Gemini.</p>
          <button
            type="button"
            onClick={() => {
              setTour(0)
              navigate('/inspector')
            }}
            className="btn mt-7 bg-white text-lg text-brand-900 hover:bg-brand-50"
          >
            ▶ Start the 2-minute demo
          </button>
        </div>
      </section>

      <section className="page">
        <div className="grid gap-4 sm:grid-cols-3">
          {ROLES.map((r) => (
            <Link key={r.title} to={r.to} className="card group text-center transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="text-5xl" aria-hidden>
                {r.emoji}
              </div>
              <h2 className="mt-3 text-lg font-bold group-hover:text-brand-700">{r.title}</h2>
              <p className="mt-1 text-sm text-slate-600">{r.text}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
