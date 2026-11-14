import type {
  Alarm,
  AlarmEvent,
  Balance,
  Components,
  DataQuality,
  DetectRun,
  Facility,
  Metrics,
  Mode,
  SimulationIn,
  SimulationOut,
  TelemetryOut,
  Topology,
} from './types'

const BASE = 'http://localhost:8000'

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(BASE + path, init)
  } catch {
    throw new ApiError('NETWORK', 'Cannot reach the API. Is the backend running on port 8000?')
  }
  if (!response.ok) {
    let code = 'HTTP_ERROR'
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body && body.error) {
        code = body.error.code
        message = body.error.message
      }
    } catch {
      // The body was not JSON. Keep the default message.
    }
    throw new ApiError(code, message)
  }
  return (await response.json()) as T
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const api = {
  facilities: () => request<Facility[]>('/facilities'),
  components: (id: string) => request<Components>(`/facilities/${id}/components`),
  modes: (id: string) => request<Mode[]>(`/facilities/${id}/modes`),
  topology: (id: string) => request<Topology>(`/topology/${id}`),
  balance: (id: string) => request<Balance>(`/balance/${id}`),
  dataQuality: () => request<DataQuality>('/data-quality'),
  metrics: () => request<Metrics>('/metrics/detection'),
  telemetry: (sensorId: string, limit: number) =>
    request<TelemetryOut>(`/telemetry/${sensorId}?limit=${limit}`),
  alarms: (state?: string) =>
    request<Alarm[]>(state ? `/alarms?state=${state}` : '/alarms'),
  alarmHistory: (id: string) => request<AlarmEvent[]>(`/alarms/${id}/history`),
  acknowledge: (id: string) => post<Alarm>(`/alarms/${id}/acknowledge`),
  clear: (id: string) => post<Alarm>(`/alarms/${id}/clear`),
  detectRun: () => post<DetectRun>('/detection/run'),
  simulate: (body: SimulationIn) => post<SimulationOut>('/simulations', body),
  simulations: () => request<SimulationOut[]>('/simulations'),
}