import { useEffect, useState } from 'react'
import { createSensor, fetchSensors, type SensorDto } from '../../services/api'

export function SensorList() {
  const [sensors, setSensors] = useState<SensorDto[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [displayName, setDisplayName] = useState<string>('')

  const loadSensors = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSensors()
      setSensors(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sensors')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSensors()
  }, [])

  const handleAddSensor = async (type: 'moisture' | 'light') => {
    setSubmitting(true)
    setError(null)
    try {
      const trimmedName = displayName.trim() ? displayName.trim() : null
      await createSensor(type, trimmedName)
      setDisplayName('')
      await loadSensors()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create sensor')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Optional display name..."
          className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-emerald-600 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => handleAddSensor('moisture')}
          disabled={submitting}
          className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          + Add Moisture
        </button>
        <button
          type="button"
          onClick={() => handleAddSensor('light')}
          disabled={submitting}
          className="rounded bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
        >
          + Add Light
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading sensors...</p>
      ) : sensors.length === 0 ? (
        <p className="text-sm text-slate-500">
          No sensors registered yet. Add a moisture or light sensor above.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
          {sensors.map((sensor) => (
            <li key={sensor.id} className="p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-800 text-sm">
                  {sensor.display_name}
                </span>
                <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-mono text-slate-700">
                  {sensor.device_type}
                </span>
              </div>
              <pre className="mt-2 overflow-x-auto rounded bg-white p-2 text-xs text-slate-600 border border-slate-100">
                {JSON.stringify(sensor.default_config, null, 2)}
              </pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}