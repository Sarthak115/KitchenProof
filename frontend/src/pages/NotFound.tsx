import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page text-center">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <Link to="/" className="btn-primary mt-4">
        Go home
      </Link>
    </div>
  )
}
