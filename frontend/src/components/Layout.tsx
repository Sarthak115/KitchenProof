import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useConfig } from '../lib/config'
import { useStoredState } from '../lib/hooks'
import { TOUR } from '../lib/tour'

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-extrabold tracking-tight text-slate-900">
      <img src="/icons/icon.svg" alt="" className="h-8 w-8" />
      <span className="hidden min-[440px]:inline">KitchenProof</span>
    </Link>
  )
}

const NAV = [
  { to: '/owner', label: 'Owner' },
  { to: '/customer', label: 'FoodieGo' },
  { to: '/inspector', label: 'Inspector' },
]

export function Layout() {
  const { demo, config, setDemo } = useConfig()
  const loc = useLocation()
  const fullBleed = loc.pathname.startsWith('/owner/audit/')
  const [tourStep] = useTour()
  return (
    <div className="flex min-h-screen flex-col">
      {demo && (
        <div className="bg-amber-400 py-1 text-center text-[11px] font-bold uppercase tracking-widest text-amber-950">
          Demo data · fictional restaurants
        </div>
      )}
      {!fullBleed && (
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5">
            <Logo />
            <nav className="ml-auto flex items-center gap-1 text-sm">
              {NAV.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={({ isActive }) =>
                    `rounded-lg px-2.5 py-1.5 font-semibold ${isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-100'}`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>
      )}
      <main className={`flex-1 ${tourStep != null ? 'pb-64' : 'pb-10'}`}>
        <Outlet />
      </main>
      {!fullBleed && (
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-4 text-xs text-slate-500">
            <span>Built with Gemini on Google Cloud (Cloud Run, Firebase)</span>
            {config.demoMode && (
              <label className="ml-auto inline-flex items-center gap-2">
                <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
                Demo Mode (sample videos)
              </label>
            )}
          </div>
        </footer>
      )}
      <TourBar />
    </div>
  )
}

export function useTour() {
  return useStoredState<number | null>('kp_tour_step', null)
}

function TourBar() {
  const [step, setStep] = useTour()
  const [min, setMin] = useStoredState('kp_tour_min', false)
  const navigate = useNavigate()
  if (step == null || step < 0 || step >= TOUR.length) return null
  const s = TOUR[step]
  if (min) {
    return (
      <button
        type="button"
        onClick={() => setMin(false)}
        className="fixed bottom-3 right-3 z-50 rounded-full bg-slate-900 px-4 py-2.5 text-sm font-bold text-white shadow-2xl"
      >
        Tour {step + 1}/{TOUR.length} ▲
      </button>
    )
  }
  const go = (n: number) => {
    if (n >= TOUR.length) {
      setStep(null)
      navigate('/')
      return
    }
    setStep(n)
    if (TOUR[n].route) navigate(TOUR[n].route!)
  }
  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-3">
      <div className="mx-auto max-w-2xl rounded-2xl bg-slate-900 p-4 text-white shadow-2xl ring-1 ring-white/10">
        <div className="flex items-start gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-bold">{step + 1}</span>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-200">
              Demo tour · step {step + 1} of {TOUR.length}
            </div>
            <div className="font-bold">{s.title}</div>
            <p className="mt-0.5 text-sm text-slate-300">{s.body}</p>
          </div>
          <button type="button" onClick={() => setMin(true)} className="px-1 text-slate-400 hover:text-white" aria-label="Minimise tour">
            ▼
          </button>
          <button type="button" onClick={() => setStep(null)} className="px-1 text-slate-400 hover:text-white" aria-label="Close tour">
            ✕
          </button>
        </div>
        <div className="mt-3 flex justify-end gap-2">
          {step > 0 && (
            <button type="button" onClick={() => go(step - 1)} className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-300 hover:bg-white/10">
              Back
            </button>
          )}
          <button type="button" onClick={() => go(step + 1)} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600">
            {step + 1 === TOUR.length ? 'Finish' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}
