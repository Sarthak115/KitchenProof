import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import type { AppConfig } from './types'

const DEFAULT: AppConfig = {
  demoMode: true,
  model: '',
  geminiAvailable: false,
  promptVersion: '',
  heroRestaurantId: 'r01',
  startWindowMin: 10,
  finishWindowMin: 4,
  customerChecksPerDay: 3,
  customerCooldownDays: 7,
}

interface Ctx {
  config: AppConfig
  /** Demo Mode as the viewer sees it: server must allow it, the viewer can switch it off. */
  demo: boolean
  setDemo: (on: boolean) => void
}

const ConfigContext = createContext<Ctx>({ config: DEFAULT, demo: true, setDemo: () => {} })

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState(DEFAULT)
  const [demoPref, setDemoPref] = useState<boolean>(() => {
    try {
      return localStorage.getItem('kp_demo') !== 'off'
    } catch {
      return true
    }
  })
  useEffect(() => {
    api.config().then(setConfig).catch(() => {})
  }, [])
  const setDemo = (on: boolean) => {
    setDemoPref(on)
    try {
      localStorage.setItem('kp_demo', on ? 'on' : 'off')
    } catch {
      /* ignore */
    }
  }
  return (
    <ConfigContext.Provider value={{ config, demo: config.demoMode && demoPref, setDemo }}>{children}</ConfigContext.Provider>
  )
}

export const useConfig = () => useContext(ConfigContext)
