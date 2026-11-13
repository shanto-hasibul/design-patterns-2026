export type HealthResponse = {
  status: string
  db: 'ok' | 'fail'
}

export interface SensorDto {
  id: string
  device_type: string
  display_name: string
  default_config: Record<string, unknown>
  sampling_interval_seconds: number
  tracking_enabled: boolean
  zone_id?: string | null
  location_id?: string | null
}

export interface ReadingDto {
  device_id: string
  value: number
  unit: string
  source: 'simulation' | 'mqtt' | 'vendor' | string
  recorded_at: string
}

export interface DeviceDto {
  id: string
  device_type: string
  role: 'sensor' | 'actuator'
  device_family: string
  display_name: string
  default_config: Record<string, unknown>
  zone_id?: string | null
  location_id?: string | null
  sampling_interval_seconds?: number
  tracking_enabled?: boolean
}

export interface ZoneInputDto {
  name: string
  moisture_threshold_low: number
  moisture_threshold_high: number
  schedule?: Record<string, unknown>
}

export interface CreateLocationConfigRequestDto {
  location_name: string
  zones: ZoneInputDto[]
}

export interface LocationSummaryDto {
  id: string
  name: string
}

export interface ZoneResponseDto {
  id: string
  location_id: string
  name: string
  moisture_threshold_low: number
  moisture_threshold_high: number
  schedule: Record<string, unknown>
}

export interface LocationConfigResponseDto {
  location: LocationSummaryDto
  zones: ZoneResponseDto[]
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error('Failed to fetch API health')
  }
  return response.json() as Promise<HealthResponse>
}

export async function fetchSensors(): Promise<SensorDto[]> {
  const response = await fetch(`${API_BASE_URL}/api/sensors`)
  if (!response.ok) {
    throw new Error(`Failed to fetch sensors (${response.status})`)
  }
  return response.json() as Promise<SensorDto[]>
}

export async function createSensor(
  type: 'moisture' | 'light' | string,
  displayName?: string | null,
): Promise<SensorDto> {
  const response = await fetch(`${API_BASE_URL}/api/sensors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      type,
      display_name: displayName ?? null,
    }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to create sensor (${response.status})`,
    )
  }
  return response.json() as Promise<SensorDto>
}

export async function triggerSensorRead(sensorId: string): Promise<ReadingDto> {
  const response = await fetch(`${API_BASE_URL}/api/sensors/${sensorId}/read`, {
    method: 'POST',
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to read sensor (${response.status})`,
    )
  }
  return response.json() as Promise<ReadingDto>
}

export async function fetchSensorReadings(
  sensorId: string,
  limit = 1,
): Promise<ReadingDto[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/sensors/${sensorId}/readings?limit=${limit}`,
  )
  if (!response.ok) {
    throw new Error(`Failed to fetch sensor readings (${response.status})`)
  }
  return response.json() as Promise<ReadingDto[]>
}

export async function updateDeviceSampling(
  deviceId: string,
  samplingIntervalSeconds: number,
  trackingEnabled: boolean,
): Promise<DeviceDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/devices/${deviceId}/sampling`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sampling_interval_seconds: samplingIntervalSeconds,
        tracking_enabled: trackingEnabled,
      }),
    },
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to update sampling (${response.status})`,
    )
  }
  return response.json() as Promise<DeviceDto>
}

export async function fetchDevices(
  family?: string,
  role?: string,
): Promise<DeviceDto[]> {
  const params = new URLSearchParams()
  if (family) params.set('family', family)
  if (role) params.set('role', role)

  const queryString = params.toString()
  const url = `${API_BASE_URL}/api/devices${queryString ? `?${queryString}` : ''}`

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to fetch devices (${response.status})`)
  }
  return response.json() as Promise<DeviceDto[]>
}

export async function provisionDeviceFamily(
  family: 'simulation' | 'edge' | string,
): Promise<DeviceDto[]> {
  const params = new URLSearchParams({ family })
  const response = await fetch(
    `${API_BASE_URL}/api/devices/provision?${params.toString()}`,
    { method: 'POST' },
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to provision family (${response.status})`,
    )
  }
  return response.json() as Promise<DeviceDto[]>
}

export async function assignDeviceZone(
  deviceId: string,
  zoneId: string | null,
): Promise<DeviceDto> {
  const response = await fetch(`${API_BASE_URL}/api/devices/${deviceId}/zone`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone_id: zoneId }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to assign zone (${response.status})`,
    )
  }
  return response.json() as Promise<DeviceDto>
}

export async function fetchLocations(): Promise<LocationSummaryDto[]> {
  const response = await fetch(`${API_BASE_URL}/api/locations`)
  if (!response.ok) {
    throw new Error(`Failed to fetch locations (${response.status})`)
  }
  return response.json() as Promise<LocationSummaryDto[]>
}

export async function createLocationConfig(
  payload: CreateLocationConfigRequestDto,
): Promise<LocationConfigResponseDto> {
  const response = await fetch(`${API_BASE_URL}/api/locations/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to create location (${response.status})`,
    )
  }
  return response.json() as Promise<LocationConfigResponseDto>
}

export async function fetchLocationConfig(
  locationId: string,
): Promise<LocationConfigResponseDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${locationId}/config`,
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to load location config (${response.status})`,
    )
  }
  return response.json() as Promise<LocationConfigResponseDto>
}

export async function deleteLocation(locationId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/locations/${locationId}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to delete location (${response.status})`,
    )
  }
}

export async function addZoneToLocation(
  locationId: string,
  payload: ZoneInputDto,
): Promise<ZoneResponseDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${locationId}/zones`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to add zone (${response.status})`,
    )
  }
  return response.json() as Promise<ZoneResponseDto>
}

export async function updateZoneOnLocation(
  locationId: string,
  zoneId: string,
  payload: ZoneInputDto,
): Promise<ZoneResponseDto> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${locationId}/zones/${zoneId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to update zone (${response.status})`,
    )
  }
  return response.json() as Promise<ZoneResponseDto>
}

export async function deleteZoneFromLocation(
  locationId: string,
  zoneId: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${locationId}/zones/${zoneId}`,
    {
      method: 'DELETE',
    },
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(
      errorData?.detail || `Failed to delete zone (${response.status})`,
    )
  }
}

export async function fetchZoneDevices(
  locationId: string,
  zoneId: string,
): Promise<DeviceDto[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/locations/${locationId}/zones/${zoneId}/devices`,
  )
  if (!response.ok) {
    throw new Error(`Failed to fetch zone devices (${response.status})`)
  }
  return response.json() as Promise<DeviceDto[]>
}