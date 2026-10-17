import { useNavigate } from 'react-router-dom'
import { useTour } from '../components/Layout'
import { api } from '../lib/api'
import { useConfig } from '../lib/config'
import { TOUR } from '../lib/tour'

export default function Tour() {
  const navigate = useNavigate()
  const [, setStep] = useTour()
  const { config } = useConfig()
  const start = (n: number) => {
    setStep(n)
    navigate(TOUR[n].route ?? '/inspector')
  }
  return (
    <div className="page max-w-2xl">
      <h1 className="text-2xl font-extrabold sm:text-3xl">The 2-minute demo tour</h1>
      <p className="mt-2 text-slate-600">
        Six steps through the whole story. A guide bar at the bottom of the screen tells you what to press. Everything runs
        on the deployed app — including a real Gemini analysis of a sample kitchen video
        {config.geminiAvailable ? '' : ' (cached result while Gemini is not configured)'}.
      </p>
      <ol className="mt-6 space-y-3">
        {TOUR.map((s, i) => (
          <li key={s.title} className="card flex gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-700 font-bold text-white">{i + 1}</span>
            <div>
              <div className="font-bold">{s.title}</div>
              <p className="text-sm text-slate-600">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" className="btn-primary text-lg" onClick={() => start(0)}>
          ▶ Start the tour
        </button>
        {config.demoResetOpen && (
          <button
            type="button"
            className="btn-secondary"
            onClick={async () => {
              if (confirm('Reset all demo data to the starting state?')) {
                await api.demoReset().catch((e) => alert(e.message))
                start(0)
              }
            }}
          >
            Reset demo data
          </button>
        )}
      </div>
    </div>
  )
}
