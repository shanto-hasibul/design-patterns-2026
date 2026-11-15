export type RealtimeEvent = {
  type: string
  payload: unknown
}

export type RealtimeStatus = 'connected' | 'connecting' | 'down'

export type RealtimeHandler = (event: RealtimeEvent) => void
export type StatusHandler = (status: RealtimeStatus) => void

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function buildWebSocketUrl(): string {
  const normalized = API_BASE_URL.replace(/\/+$/, '')
  if (normalized.startsWith('https://')) {
    return `${normalized.replace(/^https:\/\//, 'wss://')}/api/ws`
  }
  if (normalized.startsWith('http://')) {
    return `${normalized.replace(/^http:\/\//, 'ws://')}/api/ws`
  }
  return `ws://${normalized}/api/ws`
}

class DashboardRealtimeClient {
  private socket: WebSocket | null = null
  private status: RealtimeStatus = 'connecting'
  private eventListeners = new Set<RealtimeHandler>()
  private statusListeners = new Set<StatusHandler>()
  private reconnectTimer: number | null = null
  private manuallyStopped = false

  public getStatus(): RealtimeStatus {
    return this.status
  }

  private setStatus(next: RealtimeStatus): void {
    if (this.status === next) return
    this.status = next
    for (const listener of this.statusListeners) {
      listener(next)
    }
  }

  public ensureConnected(): void {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return
    }
    this.manuallyStopped = false
    this.connect()
  }

  private connect(): void {
    if (this.manuallyStopped) return
    this.setStatus('connecting')

    try {
      const ws = new WebSocket(buildWebSocketUrl())
      this.socket = ws

      ws.onopen = () => {
        this.setStatus('connected')
      }

      ws.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(String(msg.data)) as RealtimeEvent
          if (parsed && typeof parsed.type === 'string') {
            for (const listener of this.eventListeners) {
              listener(parsed)
            }
          }
        } catch {
          // Ignore non-JSON frames
        }
      }

      ws.onerror = () => {
        this.setStatus('down')
      }

      ws.onclose = () => {
        this.socket = null
        this.setStatus('down')
        if (!this.manuallyStopped && this.eventListeners.size > 0) {
          this.scheduleReconnect()
        }
      }
    } catch {
      this.setStatus('down')
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      if (!this.manuallyStopped && this.eventListeners.size > 0) {
        this.connect()
      }
    }, 3000)
  }

  public subscribe(onEvent: RealtimeHandler): () => void {
    this.eventListeners.add(onEvent)
    this.ensureConnected()

    return () => {
      this.eventListeners.delete(onEvent)
      if (this.eventListeners.size === 0 && this.statusListeners.size === 0) {
        this.manuallyStopped = true
        if (this.reconnectTimer !== null) {
          window.clearTimeout(this.reconnectTimer)
          this.reconnectTimer = null
        }
        if (this.socket) {
          this.socket.close()
          this.socket = null
        }
      }
    }
  }

  public subscribeStatus(onStatus: StatusHandler): () => void {
    this.statusListeners.add(onStatus)
    onStatus(this.status)
    this.ensureConnected()

    return () => {
      this.statusListeners.delete(onStatus)
    }
  }
}

const sharedClient = new DashboardRealtimeClient()

export function subscribeRealtime(onEvent: RealtimeHandler): () => void {
  return sharedClient.subscribe(onEvent)
}

export function subscribeRealtimeStatus(onStatus: StatusHandler): () => void {
  return sharedClient.subscribeStatus(onStatus)
}

export function getRealtimeStatus(): RealtimeStatus {
  return sharedClient.getStatus()
}