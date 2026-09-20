import { useEffect, useState } from 'react'
import { getHealth, type HealthResponse } from '../services/api'

export default function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    getHealth()
      .then((data) => {
        setHealth(data)
        setError(false)
      })
      .catch(() => {
        setError(true)
      })
  }, [])

  const isHealthy =
    !error && health?.status === 'ok' && health.db === 'ok'

  return (
    <div
      className={`rounded-full px-3 py-1 text-sm font-medium ${
        isHealthy
          ? 'bg-green-100 text-green-700'
          : 'bg-red-100 text-red-700'
      }`}
    >
      {isHealthy ? 'API & Database: Healthy' : 'API & Database: Unavailable'}
    </div>
  )
}