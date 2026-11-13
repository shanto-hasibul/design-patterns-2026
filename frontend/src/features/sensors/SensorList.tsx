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

export function SensorList() {
  const [sensors, setSensors] = useState<SensorDto[]>([])
  const [latestReadings, setLatestReadings] = useState<
    Record<string, ReadingDto | undefined>
  >({})
  const [intervalDrafts, setIntervalDrafts] = useState<Record<string, string>>(
    {},
  )
  const [loading, setLoading] = useState<boolean>(true)
  const [creating, setCreating] = useState<boolean>(false)
  const [readingSensorId, setReadingSensorId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [displayName, setDisplayName] = useState<string>('')

  const loadLatestReadingsForList = async (sensorList: SensorDto[]) => {
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
    setLatestReadings(Object.fromEntries(entries))
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
            next[s.id] = String(s.sampling_interval_seconds ?? 300)
          }
        }
        return next
      })
      await loadLatestReadingsForList(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sensors')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSensors()
  }, [])

  // Temporary polling of the latest stored reading every 4 seconds.
  // Phase 12 replaces this temporary poll with live WebSocket push events.
  useEffect(() => {
    if (sensors.length === 0) return
    const timer = window.setInterval(() => {
      void loadLatestReadingsForList(sensors)
    }, 4000)
    return () => window.clearInterval(timer)
  }, [sensors])

  const handleAddSensor = async (kind: 'moisture' | 'light') => {
    setCreating(true)
    setError(null)
    try {
      await createSensor(kind, displayName.trim() || null)
      setDisplayName('')
      await loadSensors()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create sensor')
    } finally {
      setCreating(false)
    }
  }

  const handleReadNow = async (sensorId: string) => {
    setReadingSensorId(sensorId)
    setError(null)
    try {
      const dto = await triggerSensorRead(sensorId)
      setLatestReadings((prev) => ({ ...prev, [sensorId]: dto }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to read sensor')
    } finally {
      setReadingSensorId(null)
    }
  }

  const handleSaveSampling = async (
    sensor: SensorDto,
    newTrackingEnabled?: boolean,
  ) => {
    setError(null)
    const rawInterval = Number(
      intervalDrafts[sensor.id] ?? sensor.sampling_interval_seconds,
    )
    const tracking =
      newTrackingEnabled !== undefined
        ? newTrackingEnabled
        : sensor.tracking_enabled

    if (Number.isNaN(rawInterval) || rawInterval < 5) {
      setError('Sampling interval must be at least 5 seconds.')
      return
    }

    try {
      const updated = await updateDeviceSampling(
        sensor.id,
        rawInterval,
        tracking,
      )
      setSensors((prev) =>
        prev.map((s) =>
          s.id === sensor.id
            ? {
                ...s,
                sampling_interval_seconds:
                  updated.sampling_interval_seconds ?? rawInterval,
                tracking_enabled: updated.tracking_enabled ?? tracking,
              }
            : s,
        ),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update sampling')
    }
  }

  const sourceBadgeClass = (source: string) => {
    if (source === 'mqtt') return 'bg-amber-100 text-amber-800'
    if (source === 'vendor') return 'bg-purple-100 text-purple-800'
    return 'bg-emerald-100 text-emerald-800'
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex flex-col gap-2">
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Optional sensor display name..."
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-emerald-600 focus:outline-none"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={creating}
            onClick={() => handleAddSensor('moisture')}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            + Add Moisture
          </button>
          <button
            type="button"
            disabled={creating}
            onClick={() => handleAddSensor('light')}
            className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
          >
            + Add Light
          </button>
        </div>
      </div>

      <p className="text-[11px] text-slate-400">
        Live readings poll PostgreSQL every 4s (temporary until Phase 12 WebSocket).
      </p>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading sensors...</p>
      ) : sensors.length === 0 ? (
        <p className="text-sm text-slate-500">
          No sensors registered yet. Use the buttons above to create one.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-slate-50">
          {sensors.map((sensor) => {
            const latest = latestReadings[sensor.id]
            return (
              <li key={sensor.id} className="space-y-2.5 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-800">
                    {sensor.display_name}
                  </span>
                  <span className="rounded bg-slate-200 px-2 py-0.5 font-mono text-xs text-slate-700">
                    {sensor.device_type}
                  </span>
                </div>

                {/* Latest Reading + Read Now button */}
                <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 bg-white p-2 text-xs">
                  <div>
                    {latest ? (
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">
                          {latest.value} {latest.unit}
                        </span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${sourceBadgeClass(
                            latest.source,
                          )}`}
                        >
                          {latest.source}
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-400">No readings yet</span>
                    )}
                  </div>
                  <button
                    type="button"
                    disabled={readingSensorId === sensor.id}
                    onClick={() => handleReadNow(sensor.id)}
                    className="rounded bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {readingSensorId === sensor.id ? 'Reading...' : 'Read now'}
                  </button>
                </div>

                {/* Sampling interval & Tracking controls */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-1.5">
                    <label className="text-slate-600">Interval (s):</label>
                    <input
                      type="number"
                      min={5}
                      value={
                        intervalDrafts[sensor.id] ??
                        String(sensor.sampling_interval_seconds)
                      }
                      onChange={(e) =>
                        setIntervalDrafts({
                          ...intervalDrafts,
                          [sensor.id]: e.target.value,
                        })
                      }
                      className="w-16 rounded border border-slate-300 bg-white px-1.5 py-0.5 text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => handleSaveSampling(sensor)}
                      className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-300"
                    >
                      Save
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      handleSaveSampling(sensor, !sensor.tracking_enabled)
                    }
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      sensor.tracking_enabled
                        ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                        : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                    }`}
                  >
                    {sensor.tracking_enabled ? 'Tracking: ON' : 'Tracking: OFF'}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}