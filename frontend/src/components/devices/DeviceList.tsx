import { useEffect, useState } from 'react'
import {
  assignDeviceZone,
  fetchDevices,
  fetchLocationConfig,
  fetchLocations,
  provisionDeviceFamily,
  transitionActuatorState,
  type DeviceDto,
  type LocationConfigResponseDto,
} from '../../services/api'
import {
  DeviceFamilySwitcher,
  type DeviceFamilyKey,
} from './DeviceFamilySwitcher'

const ALL_STATES = ['idle', 'running', 'off', 'error', 'maintenance'] as const

export function DeviceList() {
  const [selectedFamily, setSelectedFamily] =
    useState<DeviceFamilyKey>('simulation')
  const [devices, setDevices] = useState<DeviceDto[]>([])
  const [locationConfigs, setLocationConfigs] = useState<
    LocationConfigResponseDto[]
  >([])
  const [loading, setLoading] = useState<boolean>(true)
  const [provisioning, setProvisioning] = useState<boolean>(false)
  const [transitioningId, setTransitioningId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadDevicesAndZones = async (family: DeviceFamilyKey) => {
    setLoading(true)
    setError(null)
    try {
      const [devs, locs] = await Promise.all([
        fetchDevices(family),
        fetchLocations(),
      ])
      setDevices(devs)

      const configs = await Promise.all(
        locs.map((l) => fetchLocationConfig(l.id)),
      )
      setLocationConfigs(configs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load devices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDevicesAndZones(selectedFamily)

    const onZonesChanged = () => {
      void loadDevicesAndZones(selectedFamily)
    }
    window.addEventListener('greenhouse-locations-updated', onZonesChanged)
    return () => {
      window.removeEventListener('greenhouse-locations-updated', onZonesChanged)
    }
  }, [selectedFamily])

  const handleProvision = async () => {
    setProvisioning(true)
    setError(null)
    try {
      await provisionDeviceFamily(selectedFamily)
      await loadDevicesAndZones(selectedFamily)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to provision device family',
      )
    } finally {
      setProvisioning(false)
    }
  }

  const handleAssignZone = async (deviceId: string, zoneId: string) => {
    setError(null)
    try {
      const targetZone = zoneId === '' ? null : zoneId
      await assignDeviceZone(deviceId, targetZone)
      await loadDevicesAndZones(selectedFamily)
      window.dispatchEvent(new Event('greenhouse-devices-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign zone')
    }
  }

  const handleTransition = async (deviceId: string, target: string) => {
    setTransitioningId(deviceId)
    setError(null)
    try {
      const updated = await transitionActuatorState(deviceId, target)
      setDevices((prev) =>
        prev.map((d) => (d.id === deviceId ? updated : d)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Illegal state transition')
    } finally {
      setTransitioningId(null)
    }
  }

  const getZoneLabel = (zoneId?: string | null): string => {
    if (!zoneId) return 'Unassigned'
    for (const cfg of locationConfigs) {
      const found = cfg.zones.find((z) => z.id === zoneId)
      if (found) {
        return `${cfg.location.name} — ${found.name}`
      }
    }
    return 'Unassigned'
  }

  const stateBadgeClass = (state?: string | null) => {
    switch (state) {
      case 'running':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300'
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'maintenance':
        return 'bg-amber-100 text-amber-800 border-amber-300'
      case 'off':
        return 'bg-slate-200 text-slate-700 border-slate-300'
      default:
        return 'bg-sky-100 text-sky-800 border-sky-300'
    }
  }

  return (
    <div className="mt-4 space-y-4">
      <DeviceFamilySwitcher
        selectedFamily={selectedFamily}
        onSelectFamily={setSelectedFamily}
        onProvision={handleProvision}
        provisioning={provisioning}
      />

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">
          Loading {selectedFamily} devices...
        </p>
      ) : devices.length === 0 ? (
        <p className="text-sm text-slate-500">
          No {selectedFamily} devices provisioned yet. Click Provision above to
          create a matching kit.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
          {devices.map((device) => {
            const allowedTargets = device.allowed_targets ?? []
            const allowedCommands = device.allowed_commands ?? []

            return (
              <li key={device.id} className="space-y-2 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">
                    {device.display_name}
                  </span>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {device.role === 'actuator' && device.state && (
                      <span
                        className={`rounded border px-2 py-0.5 text-xs font-bold uppercase ${stateBadgeClass(
                          device.state,
                        )}`}
                      >
                        state: {device.state}
                      </span>
                    )}
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        device.role === 'actuator'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {device.role}
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        device.device_family === 'edge'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-sky-100 text-sky-800'
                      }`}
                    >
                      {device.device_family}
                    </span>
                    <span className="rounded bg-slate-200 px-2 py-0.5 font-mono text-xs text-slate-700">
                      {device.device_type}
                    </span>
                  </div>
                </div>

                {/* Actuator Lifecycle Transitions & Allowed Commands */}
                {device.role === 'actuator' && (
                  <div className="space-y-1.5 rounded border border-slate-200 bg-white p-2 text-xs">
                    <div className="text-[11px] text-slate-600">
                      <strong>Allowed commands:</strong>{' '}
                      {allowedCommands.length > 0
                        ? allowedCommands.join(', ')
                        : 'None'}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] text-slate-500">
                        Transition to:
                      </span>
                      {ALL_STATES.filter((s) => s !== device.state).map(
                        (targetState) => {
                          const isLegal = allowedTargets.includes(targetState)
                          return (
                            <button
                              key={targetState}
                              type="button"
                              disabled={!isLegal || transitioningId === device.id}
                              title={
                                isLegal
                                  ? `Transition from ${device.state} to ${targetState}`
                                  : `Illegal transition: cannot go from '${device.state}' directly to '${targetState}'`
                              }
                              onClick={() =>
                                handleTransition(device.id, targetState)
                              }
                              className={`rounded px-2 py-0.5 text-[11px] font-medium transition ${
                                isLegal
                                  ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                                  : 'cursor-not-allowed bg-slate-100 text-slate-400 line-through'
                              }`}
                            >
                              {targetState}
                            </button>
                          )
                        },
                      )}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="text-slate-600">
                    Zone:{' '}
                    <strong className="text-slate-800">
                      {getZoneLabel(device.zone_id)}
                    </strong>
                  </span>
                  <select
                    value={device.zone_id ?? ''}
                    onChange={(e) => handleAssignZone(device.id, e.target.value)}
                    className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 focus:border-indigo-600 focus:outline-none"
                  >
                    <option value="">— Unassigned —</option>
                    {locationConfigs.map((cfg) => (
                      <optgroup key={cfg.location.id} label={cfg.location.name}>
                        {cfg.zones.map((z) => (
                          <option key={z.id} value={z.id}>
                            {`${cfg.location.name} — ${z.name}`}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>

                <pre className="mt-1 overflow-x-auto rounded border border-slate-100 bg-white p-2 text-xs text-slate-600">
                  {JSON.stringify(device.default_config, null, 2)}
                </pre>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}