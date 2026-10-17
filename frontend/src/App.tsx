import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { ensureSignedIn } from './firebase'
import { AppRoutes } from './routes'

export default function App() {
  const { pathname } = useLocation()
  useEffect(() => {
    ensureSignedIn()
  }, [])
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return <AppRoutes />
}
