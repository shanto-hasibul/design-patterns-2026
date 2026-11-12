import { useEffect, useState } from 'react'
import {
  addZoneToLocation,
  createLocationConfig,
  deleteLocation,
  deleteZoneFromLocation,
  fetchLocationConfig,
  fetchLocations,
  fetchZoneDevices,
  updateZoneOnLocation,
  type DeviceDto,
  type LocationConfigResponseDto,
  type LocationSummaryDto,
  type ZoneInputDto,
  type ZoneResponseDto,
} from '../../services/api'

interface DraftZone {
  name: string
  low: string
  high: string
  scheduleJson: string
}

export function LocationConfigWizard() {
  const [locations, setLocations] = useState<LocationSummaryDto[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(
    null,
  )
  const [selectedConfig, setSelectedConfig] =
    useState<LocationConfigResponseDto | null>(null)
  const [zoneDevices, setZoneDevices] = useState<Record<string, DeviceDto[]>>(
    {},
  )

  const [locationName, setLocationName] = useState<string>('')
  const [draftZones, setDraftZones] = useState<DraftZone[]>([
    {
      name: 'Zone A',
      low: '0.30',
      high: '0.70',
      scheduleJson: '{"cron": "0 6 * * *"}',
    },
  ])

  const [newZone, setNewZone] = useState<DraftZone>({
    name: '',
    low: '0.25',
    high: '0.65',
    scheduleJson: '{"cron": "0 8 * * *"}',
  })

  const [editingZoneId, setEditingZoneId] = useState<string | null>(null)
  const [editZoneDraft, setEditZoneDraft] = useState<DraftZone>({
    name: '',
    low: '0.30',
    high: '0.70',
    scheduleJson: '{}',
  })

  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const loadLocationsList = async () => {
    try {
      const list = await fetchLocations()
      setLocations(list)
      if (selectedLocationId && !list.some((l) => l.id === selectedLocationId)) {
        setSelectedLocationId(null)
        setSelectedConfig(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load locations')
    }
  }

  const loadSelectedConfig = async (locId: string) => {
    try {
      const cfg = await fetchLocationConfig(locId)
      setSelectedConfig(cfg)

      const devicesMap: Record<string, DeviceDto[]> = {}
      await Promise.all(
        cfg.zones.map(async (z) => {
          devicesMap[z.id] = await fetchZoneDevices(locId, z.id)
        }),
      )
      setZoneDevices(devicesMap)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load location details',
      )
    }
  }

  useEffect(() => {
    void loadLocationsList()
  }, [])

  useEffect(() => {
    if (selectedLocationId) {
      void loadSelectedConfig(selectedLocationId)
    } else {
      setSelectedConfig(null)
      setZoneDevices({})
    }
  }, [selectedLocationId])

  useEffect(() => {
    const onDevicesUpdated = () => {
      if (selectedLocationId) {
        void loadSelectedConfig(selectedLocationId)
      }
    }
    window.addEventListener('greenhouse-devices-updated', onDevicesUpdated)
    return () => {
      window.removeEventListener('greenhouse-devices-updated', onDevicesUpdated)
    }
  }, [selectedLocationId])

  const parseDraftZone = (d: DraftZone): ZoneInputDto => {
    const trimmedName = d.name.trim()
    if (!trimmedName) {
      throw new Error('Zone name is required.')
    }
    const low = Number(d.low)
    const high = Number(d.high)
    if (Number.isNaN(low) || Number.isNaN(high)) {
      throw new Error('Thresholds must be valid numbers.')
    }
    if (low < 0 || low > 1 || high < 0 || high > 1) {
      throw new Error('Moisture thresholds must be between 0.0 and 1.0.')
    }
    if (low >= high) {
      throw new Error('Low threshold must be strictly less than high threshold.')
    }
    let parsedSchedule: Record<string, unknown> = {}
    if (d.scheduleJson.trim()) {
      try {
        parsedSchedule = JSON.parse(d.scheduleJson) as Record<string, unknown>
      } catch {
        throw new Error('Schedule must be valid JSON.')
      }
    }
    return {
      name: trimmedName,
      moisture_threshold_low: low,
      moisture_threshold_high: high,
      schedule: parsedSchedule,
    }
  }

  const handleCreateLocation = async () => {
    setError(null)
    setSuccess(null)
    if (!locationName.trim()) {
      setError('Location name is required.')
      return
    }
    if (draftZones.length === 0) {
      setError('At least one zone is required.')
      return
    }

    let zonesPayload: ZoneInputDto[]
    try {
      zonesPayload = draftZones.map(parseDraftZone)
    } catch (validationErr) {
      setError(
        validationErr instanceof Error
          ? validationErr.message
          : 'Invalid zone inputs.',
      )
      return
    }

    setSubmitting(true)
    try {
      const created = await createLocationConfig({
        location_name: locationName.trim(),
        zones: zonesPayload,
      })
      setLocationName('')
      setDraftZones([
        {
          name: 'Zone A',
          low: '0.30',
          high: '0.70',
          scheduleJson: '{"cron": "0 6 * * *"}',
        },
      ])
      setSuccess(`Created location "${created.location.name}".`)
      await loadLocationsList()
      setSelectedLocationId(created.location.id)
      window.dispatchEvent(new Event('greenhouse-locations-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create location')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteLocation = async (loc: LocationSummaryDto) => {
    if (!window.confirm(`Delete location "${loc.name}" and all its zones?`)) {
      return
    }
    setError(null)
    setSuccess(null)
    try {
      await deleteLocation(loc.id)
      if (selectedLocationId === loc.id) {
        setSelectedLocationId(null)
        setSelectedConfig(null)
      }
      await loadLocationsList()
      setSuccess(`Deleted location "${loc.name}".`)
      window.dispatchEvent(new Event('greenhouse-locations-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete location')
    }
  }

  const handleAddZoneToSelected = async () => {
    if (!selectedLocationId) return
    setError(null)
    setSuccess(null)
    let payload: ZoneInputDto
    try {
      payload = parseDraftZone(newZone)
    } catch (validationErr) {
      setError(
        validationErr instanceof Error
          ? validationErr.message
          : 'Invalid zone input.',
      )
      return
    }

    try {
      await addZoneToLocation(selectedLocationId, payload)
      setNewZone({
        name: '',
        low: '0.25',
        high: '0.65',
        scheduleJson: '{"cron": "0 8 * * *"}',
      })
      await loadSelectedConfig(selectedLocationId)
      setSuccess(`Added zone "${payload.name}".`)
      window.dispatchEvent(new Event('greenhouse-locations-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add zone')
    }
  }

  const startEditingZone = (z: ZoneResponseDto) => {
    setEditingZoneId(z.id)
    setEditZoneDraft({
      name: z.name,
      low: String(z.moisture_threshold_low),
      high: String(z.moisture_threshold_high),
      scheduleJson: JSON.stringify(z.schedule || {}),
    })
  }

  const handleSaveZoneEdit = async (zoneId: string) => {
    if (!selectedLocationId) return
    setError(null)
    setSuccess(null)
    let payload: ZoneInputDto
    try {
      payload = parseDraftZone(editZoneDraft)
    } catch (validationErr) {
      setError(
        validationErr instanceof Error
          ? validationErr.message
          : 'Invalid zone input.',
      )
      return
    }

    try {
      await updateZoneOnLocation(selectedLocationId, zoneId, payload)
      setEditingZoneId(null)
      await loadSelectedConfig(selectedLocationId)
      setSuccess(`Updated zone "${payload.name}".`)
      window.dispatchEvent(new Event('greenhouse-locations-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update zone')
    }
  }

  const handleDeleteZone = async (zoneId: string, zoneName: string) => {
    if (!selectedLocationId) return
    setError(null)
    setSuccess(null)
    try {
      await deleteZoneFromLocation(selectedLocationId, zoneId)
      await loadSelectedConfig(selectedLocationId)
      setSuccess(`Deleted zone "${zoneName}".`)
      window.dispatchEvent(new Event('greenhouse-locations-updated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete zone')
    }
  }

  return (
    <div className="mt-4 space-y-6 text-sm">
      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2.5 text-xs text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-2.5 text-xs text-emerald-800">
          {success}
        </div>
      )}

      {/* Saved Locations List */}
      <div className="space-y-2">
        <h4 className="font-semibold text-slate-800">Saved Locations</h4>
        {locations.length === 0 ? (
          <p className="text-xs text-slate-500">
            No locations saved yet. Use the builder form below to create one.
          </p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-slate-50">
            {locations.map((loc) => (
              <li
                key={loc.id}
                className="flex items-center justify-between gap-2 p-2.5"
              >
                <button
                  type="button"
                  onClick={() => setSelectedLocationId(loc.id)}
                  className={`text-left text-xs font-medium ${
                    selectedLocationId === loc.id
                      ? 'text-indigo-700 underline'
                      : 'text-slate-800 hover:text-indigo-600'
                  }`}
                >
                  {loc.name}
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedLocationId(loc.id)}
                    className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-300"
                  >
                    Open
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteLocation(loc)}
                    className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700 hover:bg-red-200"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Selected Location Detail & Zone Management */}
      {selectedConfig && (
        <div className="space-y-3 rounded border border-indigo-200 bg-indigo-50/40 p-3">
          <div>
            <h4 className="font-semibold text-slate-900">
              Selected: {selectedConfig.location.name}
            </h4>
            <p className="font-mono text-[11px] text-slate-500">
              location_id: {selectedConfig.location.id}
            </p>
          </div>

          <div className="space-y-2">
            <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
              Zones ({selectedConfig.zones.length})
            </h5>
            <ul className="space-y-2">
              {selectedConfig.zones.map((z) => {
                const assigned = zoneDevices[z.id] || []
                const isEditing = editingZoneId === z.id
                return (
                  <li
                    key={z.id}
                    className="rounded border border-slate-200 bg-white p-2.5 text-xs"
                  >
                    {isEditing ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editZoneDraft.name}
                          onChange={(e) =>
                            setEditZoneDraft({
                              ...editZoneDraft,
                              name: e.target.value,
                            })
                          }
                          placeholder="Zone name"
                          className="w-full rounded border border-slate-300 px-2 py-1"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="number"
                            step="0.05"
                            value={editZoneDraft.low}
                            onChange={(e) =>
                              setEditZoneDraft({
                                ...editZoneDraft,
                                low: e.target.value,
                              })
                            }
                            placeholder="Low (0-1)"
                            className="rounded border border-slate-300 px-2 py-1"
                          />
                          <input
                            type="number"
                            step="0.05"
                            value={editZoneDraft.high}
                            onChange={(e) =>
                              setEditZoneDraft({
                                ...editZoneDraft,
                                high: e.target.value,
                              })
                            }
                            placeholder="High (0-1)"
                            className="rounded border border-slate-300 px-2 py-1"
                          />
                        </div>
                        <input
                          type="text"
                          value={editZoneDraft.scheduleJson}
                          onChange={(e) =>
                            setEditZoneDraft({
                              ...editZoneDraft,
                              scheduleJson: e.target.value,
                            })
                          }
                          placeholder='{"cron": "0 6 * * *"}'
                          className="w-full rounded border border-slate-300 px-2 py-1 font-mono"
                        />
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleSaveZoneEdit(z.id)}
                            className="rounded bg-emerald-600 px-2.5 py-1 text-white hover:bg-emerald-700"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingZoneId(null)}
                            className="rounded bg-slate-200 px-2.5 py-1 text-slate-700"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800">
                            {z.name}
                          </span>
                          <div className="flex gap-1.5">
                            <button
                              type="button"
                              onClick={() => startEditingZone(z)}
                              className="rounded bg-slate-100 px-2 py-0.5 text-slate-700 hover:bg-slate-200"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteZone(z.id, z.name)}
                              className="rounded bg-red-50 px-2 py-0.5 text-red-700 hover:bg-red-100"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        <p className="text-slate-600">
                          VWC Thresholds: {z.moisture_threshold_low} –{' '}
                          {z.moisture_threshold_high}
                        </p>
                        <p className="font-mono text-[11px] text-slate-500">
                          Schedule: {JSON.stringify(z.schedule)}
                        </p>
                        <div className="pt-1 text-[11px] text-slate-600">
                          <strong>Devices in zone:</strong>{' '}
                          {assigned.length === 0
                            ? 'None'
                            : assigned.map((d) => d.display_name).join(', ')}
                        </div>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>

          {/* Add Zone to Selected Location */}
          <div className="space-y-2 border-t border-indigo-200 pt-2">
            <h5 className="text-xs font-semibold text-slate-700">
              + Add Zone to {selectedConfig.location.name}
            </h5>
            <input
              type="text"
              value={newZone.name}
              onChange={(e) => setNewZone({ ...newZone, name: e.target.value })}
              placeholder="New zone name..."
              className="w-full rounded border border-slate-300 bg-white px-2.5 py-1 text-xs"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                step="0.05"
                value={newZone.low}
                onChange={(e) =>
                  setNewZone({ ...newZone, low: e.target.value })
                }
                placeholder="Low VWC (0.0-1.0)"
                className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs"
              />
              <input
                type="number"
                step="0.05"
                value={newZone.high}
                onChange={(e) =>
                  setNewZone({ ...newZone, high: e.target.value })
                }
                placeholder="High VWC (0.0-1.0)"
                className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs"
              />
            </div>
            <input
              type="text"
              value={newZone.scheduleJson}
              onChange={(e) =>
                setNewZone({ ...newZone, scheduleJson: e.target.value })
              }
              placeholder='Schedule JSON e.g. {"cron": "0 8 * * *"}'
              className="w-full rounded border border-slate-300 bg-white px-2.5 py-1 font-mono text-xs"
            />
            <button
              type="button"
              onClick={handleAddZoneToSelected}
              className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700"
            >
              Add Zone
            </button>
          </div>
        </div>
      )}

      {/* Builder Form for New Location */}
      <div className="space-y-3 border-t border-slate-200 pt-4">
        <h4 className="font-semibold text-slate-800">
          Build New Location Configuration
        </h4>
        <input
          type="text"
          value={locationName}
          onChange={(e) => setLocationName(e.target.value)}
          placeholder="Location name (e.g. North Wing Greenhouse)"
          className="w-full rounded border border-slate-300 px-3 py-1.5 text-xs focus:border-emerald-600 focus:outline-none"
        />

        <div className="space-y-2">
          {draftZones.map((dz, idx) => (
            <div
              key={idx}
              className="space-y-1.5 rounded border border-slate-200 bg-slate-50 p-2.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">
                  Draft Zone #{idx + 1}
                </span>
                {draftZones.length > 1 && (
                  <button
                    type="button"
                    onClick={() =>
                      setDraftZones(draftZones.filter((_, i) => i !== idx))
                    }
                    className="text-red-600 hover:underline"
                  >
                    Remove
                  </button>
                )}
              </div>
              <input
                type="text"
                value={dz.name}
                onChange={(e) => {
                  const copy = [...draftZones]
                  copy[idx] = { ...dz, name: e.target.value }
                  setDraftZones(copy)
                }}
                placeholder="Zone name"
                className="w-full rounded border border-slate-300 bg-white px-2 py-1"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.05"
                  value={dz.low}
                  onChange={(e) => {
                    const copy = [...draftZones]
                    copy[idx] = { ...dz, low: e.target.value }
                    setDraftZones(copy)
                  }}
                  placeholder="Low (0.0 - 1.0)"
                  className="rounded border border-slate-300 bg-white px-2 py-1"
                />
                <input
                  type="number"
                  step="0.05"
                  value={dz.high}
                  onChange={(e) => {
                    const copy = [...draftZones]
                    copy[idx] = { ...dz, high: e.target.value }
                    setDraftZones(copy)
                  }}
                  placeholder="High (0.0 - 1.0)"
                  className="rounded border border-slate-300 bg-white px-2 py-1"
                />
              </div>
              <input
                type="text"
                value={dz.scheduleJson}
                onChange={(e) => {
                  const copy = [...draftZones]
                  copy[idx] = { ...dz, scheduleJson: e.target.value }
                  setDraftZones(copy)
                }}
                placeholder='Schedule JSON'
                className="w-full rounded border border-slate-300 bg-white px-2 py-1 font-mono"
              />
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              setDraftZones([
                ...draftZones,
                {
                  name: `Zone ${String.fromCharCode(65 + draftZones.length)}`,
                  low: '0.30',
                  high: '0.70',
                  scheduleJson: '{"cron": "0 6 * * *"}',
                },
              ])
            }
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            + Add Another Draft Zone
          </button>
          <button
            type="button"
            onClick={handleCreateLocation}
            disabled={submitting}
            className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? 'Building...' : 'Build & Save Location'}
          </button>
        </div>
      </div>
    </div>
  )
}