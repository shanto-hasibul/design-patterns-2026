import { useEffect, useState } from 'react'
import {
  fetchAlerts,
  fetchLocationConfig,
  fetchLocations,
  type AlertDto,
  type LocationSummaryDto,
  type ZoneResponseDto,
} from '../../services/api'

const ALERT_POLL_INTERVAL_MS = 4000

export function EventFeed() {
  const [alerts, setAlerts] = useState<AlertDto[]>([])
  const [locations, setLocations] = useState<LocationSummaryDto[]>([])
  const [zones, setZones] = useState<ZoneResponseDto[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<string>('')
  const [selectedZoneId, setSelectedZoneId] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('active')
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const loadLocations = async () => {
    try {
      const locs = await fetchLocations()
      setLocations(locs)
    } catch {
      // Ignore location dropdown errors if none exist yet
    }
  }

  useEffect(() => {
    void loadLocations()
    const onLocsChanged = () => void loadLocations()
    window.addEventListener('greenhouse-locations-updated', onLocsChanged)
    return () => {
      window.removeEventListener('greenhouse-locations-updated', onLocsChanged)
    }
  }, [])

  useEffect(() => {
    if (!selectedLocationId) {
      setZones([])
      setSelectedZoneId('')
      return
    }
    void fetchLocationConfig(selectedLocationId)
      .then((cfg) => {
        setZones(cfg.zones)
        setSelectedZoneId('')
      })
      .catch(() => setZones([]))
  }, [selectedLocationId])

  const loadAlerts = async (silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const rows = await fetchAlerts({
        status: statusFilter || undefined,
        location_id: selectedLocationId || undefined,
        zone_id: selectedZoneId || undefined,
        limit: 50,
      })
      setAlerts(rows)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts')
    } finally {
      if (!silent) setLoading(false)
    }
  }

  // Initial fetch + polling every 4 seconds (4000ms) until Phase 12 WebSocket push replaces it.
  useEffect(() => {
    void loadAlerts(false)
    const timer = window.setInterval(() => {
      void loadAlerts(true)
    }, ALERT_POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [selectedLocationId, selectedZoneId, statusFilter])

  const severityBadgeClass = (severity: string) => {
    if (severity === 'critical') return 'bg-red-100 text-red-800'
    if (severity === 'warning') return 'bg-amber-100 text-amber-800'
    return 'bg-sky-100 text-sky-800'
  }

  return (
    <div className="mt-4 space-y-3 text-sm">
      <p className="text-[11px] text-slate-400">
        Polls persisted alerts every 4s (Phase 12 replaces with WebSocket).
      </p>

      {/* Location, Zone & Status Filters */}
      <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
        <select
          value={selectedLocationId}
          onChange={(e) => setSelectedLocationId(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
        >
          <option value="">All Locations</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>

        <select
          value={selectedZoneId}
          disabled={!selectedLocationId}
          onChange={(e) => setSelectedZoneId(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs disabled:bg-slate-100 disabled:text-slate-400"
        >
          <option value="">All Zones</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
        >
          <option value="active">Status: Active</option>
          <option value="resolved">Status: Resolved</option>
          <option value="">Status: All</option>
        </select>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-xs text-slate-500">Loading alerts...</p>
      ) : alerts.length === 0 ? (
        <p className="rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
          No alerts match the current filter. Trigger a low moisture reading or
          a failed command to see persisted alerts appear here.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
          {alerts.map((alert) => (
            <li key={alert.id} className="space-y-1 p-2.5 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${severityBadgeClass(
                    alert.severity,
                  )}`}
                >
                  {alert.severity}
                </span>
                <span className="font-mono text-[11px] text-slate-500">
                  {alert.event_type}
                </span>
              </div>
              <p className="text-slate-800">{alert.message}</p>
              <p className="text-[10px] text-slate-400">
                {new Date(alert.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}