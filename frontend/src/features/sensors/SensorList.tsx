import { useEffect, useState } from 'react'
import {
  createSensor,
  fetchSensorReadings,
  fetchSensors,
  triggerSensorRead,
  updateDeviceSampling,
  type ReadingDto,
  type SensorDto,
} from '../../services/api'
import {
  subscribeRealtime,
  subscribeRealtimeStatus,
  type RealtimeStatus,
} from '../../services/realtime'

export function SensorList() {
  const [sensors, setSensors] = useState<SensorDto[]>([])
  const [latestReadings, setLatestReadings] = useState<
    Record<string, ReadingDto | undefined>
  >({})
  const [intervalDrafts, setIntervalDrafts] = useState<Record<string, string>>(
    {},
  )
  const [type, setType] = useState<'moisture' | 'light'>('moisture')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [readingSensorId, setReadingSensorId] = useState<string | null>(null)
  const [savingConfigId, setSavingConfigId] = useState<string | null>(null)
  const [wsStatus, setWsStatus] = useState<RealtimeStatus>('connecting')
  const [error, setError] = useState<string | null>(null)

  const refreshAllLatestReadings = async (sensorList: SensorDto[]) => {
    const entries = await Promise.all(
      sensorList.map(async (s) => {
        try {
          const rows = await fetchSensorReadings(s.id, 1)
          return [s.id, rows[0]] as const
        } catch {
          return [s.id, undefined] as const
        }
      }),
    )
    setLatestReadings((prev) => {
      const next = { ...prev }
      for (const [id, row] of entries) {
        if (row) next[id] = row
      }
      return next
    })
  }

  const loadSensors = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSensors()
      setSensors(data)
      setIntervalDrafts((prev) => {
        const next = { ...prev }
        for (const s of data) {
          if (next[s.id] === undefined) {
            next[s.id] = String(s.sampling_interval_seconds)
          }
        }
        return next
      })
      await refreshAllLatestReadings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sensors')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSensors()
  }, [])

  // Subscribe to WebSocket status and live reading.created events
  useEffect(() => {
    const unsubStatus = subscribeRealtimeStatus(setWsStatus)
    const unsubEvents = subscribeRealtime((event) => {
      if (event.type === 'reading.created' && event.payload) {
        const p = event.payload as {
          device_id?: string
          value?: number
          unit?: string
          source?: string
          recorded_at?: string
        }
        if (p.device_id && typeof p.value === 'number' && p.unit && p.recorded_at) {
          setLatestReadings((prev) => ({
            ...prev,
            [p.device_id!]: {
              device_id: p.device_id!,
              value: p.value!,
              unit: p.unit!,
              source: p.source || 'simulation',
              recorded_at: p.recorded_at!,
            },
          }))
        }
      }
    })
    return () => {
      unsubStatus()
      unsubEvents()
    }
  }, [])

  // Pause Phase 5 readings polling while WebSocket is 'connected'; resume polling as fallback when 'down'
  useEffect(() => {
    if (sensors.length === 0 || wsStatus === 'connected') return
    const timer = window.setInterval(() => {
      void refreshAllLatestReadings(sensors)
    }, 3000)
    return () => window.clearInterval(timer)
  }, [sensors, wsStatus])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await createSensor(type, displayName.trim() || null)
      setDisplayName('')
      await loadSensors()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create sensor')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReadNow = async (sensorId: string) => {
    setReadingSensorId(sensorId)
    setError(null)
    try {
      const reading = await triggerSensorRead(sensorId)
      setLatestReadings((prev) => ({ ...prev, [sensorId]: reading }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to read sensor')
    } finally {
      setReadingSensorId(null)
    }
  }

  const handleSaveSampling = async (
    sensor: SensorDto,
    nextTracking: boolean,
  ) => {
    const parsed = Number(
      intervalDrafts[sensor.id] ?? sensor.sampling_interval_seconds,
    )
    if (!Number.isFinite(parsed) || parsed < 5) {
      setError('Sampling interval must be at least 5 seconds.')
      return
    }

    setSavingConfigId(sensor.id)
    setError(null)
    try {
      const updated = await updateDeviceSampling(
        sensor.id,
        Math.round(parsed),
        nextTracking,
      )
      setSensors((prev) =>
        prev.map((s) =>
          s.id === sensor.id
            ? {
                ...s,
                sampling_interval_seconds: updated.sampling_interval_seconds ?? 300,
                tracking_enabled: updated.tracking_enabled ?? true,
              }
            : s,
        ),
      )
      setIntervalDrafts((prev) => ({
        ...prev,
        [sensor.id]: String(updated.sampling_interval_seconds ?? 300),
      }))
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to update sampling settings',
      )
    } finally {
      setSavingConfigId(null)
    }
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>
          Stream mode:{' '}
          <strong>
            {wsStatus === 'connected'
              ? 'Live WebSocket (poll paused)'
              : 'Fallback HTTP Poll (3s)'}
          </strong>
        </span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-700">
            Sensor Type
          </label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as 'moisture' | 'light')}
            className="mt-1 w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-emerald-600 focus:outline-none"
          >
            <option value="moisture">moisture</option>
            <option value="light">light</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700">
            Display Name (optional)
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. North Bed Moisture"
            className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm focus:border-emerald-600 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {submitting ? 'Creating...' : 'Create Sensor'}
        </button>
      </form>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading sensors...</p>
      ) : sensors.length === 0 ? (
        <p className="text-sm text-slate-500">
          No sensors registered yet. Create one above.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
          {sensors.map((sensor) => {
            const latest = latestReadings[sensor.id]
            const isSaving = savingConfigId === sensor.id

            return (
              <li key={sensor.id} className="space-y-2 p-2.5 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-800">
                    {sensor.display_name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      {sensor.device_type}
                    </span>
                    <button
                      type="button"
                      disabled={readingSensorId === sensor.id}
                      onClick={() => handleReadNow(sensor.id)}
                      className="rounded bg-slate-800 px-2 py-0.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
                    >
                      {readingSensorId === sensor.id ? 'Reading...' : 'Read now'}
                    </button>
                  </div>
                </div>

                {latest ? (
                  <div className="rounded border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700">
                    <div className="flex items-center justify-between">
                      <span>
                        Latest: <strong>{latest.value}</strong> {latest.unit}
                      </span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                        {latest.source}
                      </span>
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-400">
                      {new Date(latest.recorded_at).toLocaleTimeString()}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    No readings recorded yet.
                  </p>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-2 text-xs">
                  <label className="flex items-center gap-1.5 text-slate-700">
                    <input
                      type="checkbox"
                      checked={sensor.tracking_enabled}
                      disabled={isSaving}
                      onChange={(e) =>
                        handleSaveSampling(sensor, e.target.checked)
                      }
                      className="rounded border-slate-300 text-emerald-600"
                    />
                    <span>Tracking</span>
                  </label>

                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-500">Interval (s):</span>
                    <input
                      type="number"
                      min={5}
                      value={
                        intervalDrafts[sensor.id] ??
                        sensor.sampling_interval_seconds
                      }
                      onChange={(e) =>
                        setIntervalDrafts((prev) => ({
                          ...prev,
                          [sensor.id]: e.target.value,
                        }))
                      }
                      className="w-16 rounded border border-slate-300 bg-white px-1.5 py-0.5 text-xs"
                    />
                    <button
                      type="button"
                      disabled={isSaving}
                      onClick={() =>
                        handleSaveSampling(sensor, sensor.tracking_enabled)
                      }
                      className="rounded bg-emerald-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      Save
                    </button>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}