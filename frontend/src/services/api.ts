export type HealthResponse = {
  status: string
  db: 'ok' | 'fail'
}

export interface SensorDto {
  id: string
  device_type: string
  display_name: string
  default_config: Record<string, unknown>
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