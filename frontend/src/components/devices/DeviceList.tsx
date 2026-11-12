import { useEffect, useState } from 'react'
import {
  fetchDevices,
  provisionDeviceFamily,
  type DeviceDto,
} from '../../services/api'
import {
  DeviceFamilySwitcher,
  type DeviceFamilyKey,
} from './DeviceFamilySwitcher'

export function DeviceList() {
  const [selectedFamily, setSelectedFamily] =
    useState<DeviceFamilyKey>('simulation')
  const [devices, setDevices] = useState<DeviceDto[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [provisioning, setProvisioning] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const loadDevices = async (family: DeviceFamilyKey) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDevices(family)
      setDevices(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load devices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDevices(selectedFamily)
  }, [selectedFamily])

  const handleProvision = async () => {
    setProvisioning(true)
    setError(null)
    try {
      await provisionDeviceFamily(selectedFamily)
      await loadDevices(selectedFamily)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to provision device family',
      )
    } finally {
      setProvisioning(false)
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
        <p className="text-sm text-slate-500">Loading {selectedFamily} devices...</p>
      ) : devices.length === 0 ? (
        <p className="text-sm text-slate-500">
          No {selectedFamily} devices provisioned yet. Click Provision above to create a matching kit.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
          {devices.map((device) => (
            <li key={device.id} className="p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-800">
                  {device.display_name}
                </span>
                <div className="flex items-center gap-1.5">
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
              <pre className="mt-2 overflow-x-auto rounded border border-slate-100 bg-white p-2 text-xs text-slate-600">
                {JSON.stringify(device.default_config, null, 2)}
              </pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}