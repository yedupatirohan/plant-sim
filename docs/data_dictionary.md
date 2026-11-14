# Data Dictionary

Conventions: IDs are immutable, zero-padded and unique. All timestamps are UTC ISO-8601. Units are explicit in column names or the Unit column.

## Facility (FAC-001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| facility_id | text PK | Y | `FAC-\d{3}` | Y | pattern |
| name | text | Y | | Y | non-empty |
| status | text | Y | ACTIVE, MAINTENANCE, DECOMMISSIONED | N | enum |
| commissioned_on | date | Y | | N | not in future |

## Pump (PUMP-001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| pump_id | text PK | Y | `PUMP-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| name | text | Y | | N | non-empty |
| rated_flow_m3h | real | Y | m3/h | N | > 0 |
| shutoff_head_m | real | Y | m (pump curve H0) | N | > 0 |
| curve_coeff_k | real | Y | m per (m3/h)^2 | N | > 0 |
| status | text | Y | RUNNING, STANDBY, FAULTED, MAINTENANCE | N | enum |
| effective_from | date | Y | | N | <= effective_to |
| effective_to | date | N | | N | null = current |

## Tank (TANK-001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| tank_id | text PK | Y | `TANK-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| name | text | Y | | N | non-empty |
| capacity_m3 | real | Y | m3 | N | > 0 |
| cross_section_m2 | real | Y | m2 | N | > 0 |
| min_level_pct / max_level_pct | real | Y | % | N | 0 <= min < max <= 100 |
| status | text | Y | IN_SERVICE, OUT_OF_SERVICE | N | enum |

## Valve (VALVE-001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| valve_id | text PK | Y | `VALVE-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| name | text | Y | | N | non-empty |
| default_state | text | Y | OPEN, CLOSED, THROTTLED | N | enum |
| default_position_pct | real | Y | % | N | 0-100; CLOSED=0, OPEN=100 |

## Pipe (PIPE-001, assumed format)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| pipe_id | text PK | Y | `PIPE-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| from_node_id | text | Y | a Pump, Tank or Valve ID | N | must exist, same facility |
| to_node_id | text | Y | a Pump, Tank or Valve ID | N | must exist, same facility, != from |
| length_m | real | Y | m | N | > 0 |
| diameter_mm | real | Y | mm | N | > 0 |

## Sensor (SNS-001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| sensor_id | text PK | Y | `SNS-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| component_type | text | Y | PUMP, TANK, VALVE, PIPE | N | enum |
| component_id | text | Y | ID of that component | N | must exist |
| measurement | text | Y | FLOW, PRESSURE, LEVEL | N | enum |
| unit | text | Y | m3/h, kPa, % | N | must match measurement |

## OperatingMode (MODE-001, assumed format)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| mode_id | text PK | Y | `MODE-\d{3}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| name | text | Y | NORMAL, LOW_DEMAND, PEAK_DEMAND, MAINTENANCE | N | enum |
| pump_speed_pct | real | Y | % | N | 0-100 |
| effective_from / effective_to | datetime | Y / N | UTC | N | from < to |

Bridge table `operating_mode_valve_state` (N:M, Mode and Valve): `mode_id`, `valve_id`, `state`, `position_pct`. The pair `(mode_id, valve_id)` is unique.

## Telemetry (TEL-000001, assumed format)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| telemetry_id | text PK | Y | `TEL-\d{6}` | Y | pattern |
| sensor_id | text FK | Y | Sensor | N | must exist |
| ts_utc | datetime | Y | UTC | N | `(sensor_id, ts_utc)` unique |
| value | real | Y | unit of the sensor | N | within physical range |
| quality | text | Y | GOOD, SUSPECT, BAD | N | enum |

## Alarm (ALM-000001, assumed format)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| alarm_id | text PK | Y | `ALM-\d{6}` | Y | pattern |
| facility_id | text FK | Y | Facility | N | must exist |
| sensor_id | text FK | N | Sensor | N | must exist if given |
| alarm_type | text | Y | LEAK, BLOCKAGE, PUMP_DEGRADATION, SENSOR_FAULT, MASS_BALANCE, OVERFLOW | N | enum |
| raised_at / cleared_at | datetime | Y / N | UTC | N | raised < cleared |
| state | text | Y | RAISED, ACKNOWLEDGED, CLEARED | N | lifecycle order |

## SimulationRun (SIM-2026-000001)

| Field | Type | Req | Allowed values / unit | Unique | Validation |
|---|---|---|---|---|---|
| simulation_id | text PK | Y | `SIM-2026-\d{6}` | Y | pattern |
| mode_id | text FK | Y | OperatingMode | N | **must exist** (input config) |
| seed | integer | Y | | N | |
| assumptions_json | text | Y | JSON | N | valid JSON |
| result_json | text | Y | JSON | N | valid JSON |
| status | text | Y | COMPLETED, FAILED | N | enum |

Bridge table `simulation_run_alarm` (N:M): `simulation_id`, `alarm_id`.

## Event tables (history is never overwritten)

- `valve_state_event`: `event_id`, `valve_id`, `old_state`, `new_state`, `changed_at`, `reason`.
- `equipment_status_event`: `event_id`, `component_type`, `component_id`, `old_status`, `new_status`, `changed_at`.
- `alarm_event`: `event_id`, `alarm_id`, `old_state`, `new_state`, `changed_at`.

## Ground truth (separate file, never an input feature)

`ground_truth.csv`: `scenario_id`, `issue_type` (LEAK, BLOCKAGE, PUMP_DEGRADATION, SENSOR_FAULT, plus the five edge cases), `component_id`, `start_ts`, `end_ts`, `expected_alarm_type`, `rule_applied`.

## Relationships and cardinality

| Parent | Child | Cardinality | Key and rule |
|--------|-------|-------------|--------------|
| Facility | Pump, Tank, Valve, Pipe, Sensor, OperatingMode | 1:N for each | `facility_id` is required in every child table |
| Sensor | Telemetry | 1:N | `sensor_id`; `(sensor_id, ts_utc)` is unique |
| Pump, Tank or Valve | Sensor | 1:N | each sensor measures exactly one component (`component_type`, `component_id`) |
| Node (pump, tank or valve) | Pipe | N:M through pipes | each pipe has exactly two ends (`from_node_id`, `to_node_id`), both nodes of the same facility; a missing end is EDGE-001 |
| OperatingMode | Valve | N:M | bridge table `operating_mode_valve_state`, `(mode_id, valve_id)` unique |
| OperatingMode | SimulationRun | 1:N | a run needs an operating mode as its input configuration; a run without one is EDGE-004 |
| SimulationRun | Alarm | N:M | bridge table `simulation_run_alarm` |

Optional fields: `effective_to` (null means current). Alarm changes are stored as event rows and history is never overwritten.