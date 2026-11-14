export interface Facility {
  facility_id: string
  name: string
  status: string
  commissioned_on: string
}

export interface Pump {
  pump_id: string
  name: string
  rated_flow_m3h: number
  shutoff_head_m: number
  curve_coeff_k: number
  status: string
}

export interface Tank {
  tank_id: string
  name: string
  capacity_m3: number
  min_level_pct: number
  max_level_pct: number
  status: string
}

export interface Valve {
  valve_id: string
  name: string
  default_state: string
  default_position_pct: number
}

export interface Pipe {
  pipe_id: string
  from_node_id: string
  to_node_id: string
  length_m: number
  diameter_mm: number
}

export interface Sensor {
  sensor_id: string
  component_type: string
  component_id: string
  measurement: string
  unit: string
}

export interface Components {
  facility_id: string
  pumps: Pump[]
  tanks: Tank[]
  valves: Valve[]
  pipes: Pipe[]
  sensors: Sensor[]
}

export interface Mode {
  mode_id: string
  facility_id: string
  name: string
  pump_speed_pct: number
}

export interface Topology {
  facility_id: string
  node_count: number
  pipe_count: number
  component_count: number
  connected: boolean
  isolated_nodes: string[]
  invalid_pipes: { pipe_id: string; missing_nodes: string[] }[]
  status: string
}

export interface Balance {
  facility_id: string
  status: string
  note: string | null
  windows_checked: number
  violation_windows: number
  events: { start_ts: string; end_ts: string; max_residual_m3h: number }[]
}

export interface DataQuality {
  overall: string
  counts: Record<string, number>
  telemetry_from: string | null
  telemetry_to: string | null
  topology: Topology[]
  balance: Balance[]
}

export interface Metrics {
  truth_scenarios: number
  detections: number
  true_positives: number
  false_positives: number
  false_negatives: number
  precision: number | null
  recall: number | null
  f1: number | null
  mean_delay_min: number | null
  max_delay_min: number | null
  per_type: Record<string, { tp: number; fp: number; fn: number }>
  missed: string[]
  edge_cases: {
    scenario_id: string
    issue_type: string
    expected_alarm_type: string
    detected: boolean
  }[]
  not_scored_here: { scenario_id: string; issue_type: string }[]
}

export interface Alarm {
  alarm_id: string
  facility_id: string
  sensor_id: string | null
  alarm_type: string
  state: string
  raised_at: string
  cleared_at: string | null
}

export interface AlarmEvent {
  old_state: string | null
  new_state: string
  changed_at: string
}

export interface DetectRun {
  events_found: number
  alarms_created: number
  alarms: Alarm[]
}

export interface TelemetryOut {
  sensor_id: string
  measurement: string
  unit: string
  count: number
  points: { ts_utc: string; value: number; quality: string }[]
}

export interface SimulationIn {
  mode_id: string
  pump_speed_pct?: number
}

export interface SimulationOut {
  simulation_id: string
  mode_id: string
  seed: number
  status: string
  assumptions: Record<string, unknown>
  result: Record<string, unknown>
}