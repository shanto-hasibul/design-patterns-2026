import { useEffect, useState } from 'react'
import {
  fetchLocationOverview,
  fetchLocations,
  type LocationOverviewDto,
  type LocationSummaryDto,
} from '../../services/api'

export function OverviewPanel() {
  const [locations, setLocations] = useState<LocationSummaryDto[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<string>('')
  const [overview, setOverview] = useState<LocationOverviewDto | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const loadLocations = async () => {
    try {
      const list = await fetchLocations()
      setLocations(list)
      if (list.length > 0 && !list.some((l) => l.id === selectedLocationId)) {
        setSelectedLocationId(list[0].id)
      } else if (list.length === 0) {
        setSelectedLocationId('')
        setOverview(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load locations')
    }
  }

  const loadOverview = async (locId: string) => {
    if (!locId) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchLocationOverview(locId)
      setOverview(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load overview')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadLocations()

    const onLocationsChanged = () => {
      void loadLocations()
    }
    window.addEventListener('greenhouse-locations-updated', onLocationsChanged)
    return () => {
      window.removeEventListener(
        'greenhouse-locations-updated',
        onLocationsChanged,
      )
    }
  }, [])

  useEffect(() => {
    if (selectedLocationId) {
      void loadOverview(selectedLocationId)
    }
  }, [selectedLocationId])

  return (
    <div className="mt-4 space-y-4 text-sm">
      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {locations.length === 0 ? (
        <p className="text-xs text-slate-500">
          No locations configured yet. Build a location in Configuration to see
          its overview.
        </p>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <select
              value={selectedLocationId}
              onChange={(e) => setSelectedLocationId(e.target.value)}
              className="flex-1 rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-600 focus:outline-none"
            >
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={loading || !selectedLocationId}
              onClick={() => void loadOverview(selectedLocationId)}
              className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
            >
              {loading ? '...' : 'Refresh'}
            </button>
          </div>

          {overview && (
            <div className="space-y-3 text-xs">
              {/* Assigned Device Counts */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded border border-slate-200 bg-slate-50 p-2.5">
                  <p className="text-slate-500">Assigned Sensors</p>
                  <p className="mt-0.5 text-lg font-bold text-slate-900">
                    {overview.device_counts.sensor}
                  </p>
                </div>
                <div className="rounded border border-slate-200 bg-slate-50 p-2.5">
                  <p className="text-slate-500">Assigned Actuators</p>
                  <p className="mt-0.5 text-lg font-bold text-slate-900">
                    {overview.device_counts.actuator}
                  </p>
                </div>
              </div>

              {/* Active Strategy & Recommendation */}
              <div className="space-y-1.5 rounded border border-slate-200 bg-slate-50 p-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">
                    Saved Strategy:
                  </span>
                  <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-indigo-800">
                    {overview.strategy_key ?? 'None saved'}
                  </span>
                </div>
                {overview.last_recommendation ? (
                  <div className="pt-1">
                    <span className="font-semibold text-slate-700">
                      Recommendation:{' '}
                    </span>
                    <span className="font-bold uppercase text-sky-800">
                      {overview.last_recommendation.action}
                    </span>
                    <p className="mt-1 text-slate-600">
                      {overview.last_recommendation.reason}
                    </p>
                  </div>
                ) : (
                  <p className="text-slate-500">
                    No recommendation yet (save an automation strategy first).
                  </p>
                )}
              </div>

              {/* Zones Breakdown */}
              <div className="space-y-2">
                <h4 className="font-semibold text-slate-800">
                  Zones ({overview.zones.length})
                </h4>
                {overview.zones.map((z) => {
                  const readingByDev = new Map(
                    z.latest_readings.map((r) => [r.device_id, r]),
                  )
                  return (
                    <div
                      key={z.id}
                      className="space-y-1.5 rounded border border-slate-200 bg-white p-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-900">
                          {z.name}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          VWC {z.moisture_threshold_low}–
                          {z.moisture_threshold_high}
                        </span>
                      </div>

                      {z.devices.length === 0 ? (
                        <p className="text-slate-400">
                          No devices assigned to this zone.
                        </p>
                      ) : (
                        <ul className="divide-y divide-slate-100">
                          {z.devices.map((d) => {
                            const reading = readingByDev.get(d.id)
                            return (
                              <li key={d.id} className="py-1.5">
                                <div className="flex items-center justify-between">
                                  <span className="font-medium text-slate-800">
                                    {d.display_name}
                                  </span>
                                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
                                    {d.role} · {d.device_type}
                                  </span>
                                </div>
                                {reading ? (
                                  <p className="mt-0.5 text-[11px] text-emerald-700">
                                    Latest: <strong>{reading.value}</strong>{' '}
                                    {reading.unit} (tracking:{' '}
                                    {reading.tracking_enabled ? 'on' : 'off'},{' '}
                                    {reading.sampling_interval_seconds}s)
                                  </p>
                                ) : (
                                  <p className="mt-0.5 text-[11px] text-slate-400">
                                    No reading recorded yet.
                                  </p>
                                )}
                              </li>
                            )
                          })}
                        </ul>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}