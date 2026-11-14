import { useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api'
import { Empty, ErrorBox, Loading, Section } from '../ui'
import { useAsync } from '../useAsync'

const LIMITS = [100, 500, 1000, 5000]

function Chart({ sensorId, limit }: { sensorId: string; limit: number }) {
  const t = useAsync(() => api.telemetry(sensorId, limit), `telemetry-${sensorId}-${limit}`)
  if (t.loading) return <Loading label="Loading readings…" />
  if (t.error) return <ErrorBox message={t.error} onRetry={t.reload} />
  if (!t.data || t.data.points.length === 0) return <Empty text="No readings for this sensor." />

  const d = t.data
  const rows = d.points.map((p) => ({ time: p.ts_utc.slice(11, 16), value: p.value }))
  const notGood = d.points.filter((p) => p.quality !== 'GOOD').length

  return (
    <>
      <p className="muted">
        {d.count} readings of {d.measurement} in {d.unit}. First reading {d.points[0].ts_utc}, last{' '}
        {d.points[d.points.length - 1].ts_utc} (UTC). Readings not marked GOOD: {notGood}.
      </p>
      <div style={{ width: '100%', height: 320 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" minTickGap={40} />
            <YAxis
              domain={['auto', 'auto']}
              label={{ value: d.unit, angle: -90, position: 'insideLeft' }}
            />
            <Tooltip />
            <Line type="monotone" dataKey="value" dot={false} stroke="#12344d" strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function Picker({ facilityId }: { facilityId: string }) {
  const comp = useAsync(() => api.components(facilityId), `components-${facilityId}`)
  const [sensor, setSensor] = useState('')
  const [limit, setLimit] = useState(1000)

  if (comp.loading) return <Loading label="Loading sensors…" />
  if (comp.error) return <ErrorBox message={comp.error} onRetry={comp.reload} />
  if (!comp.data || comp.data.sensors.length === 0) return <Empty text="No sensors here." />

  const sensors = comp.data.sensors
  const sensorId = sensor || sensors[0].sensor_id

  return (
    <>
      <div className="toolbar">
        <label>
          Sensor{' '}
          <select value={sensorId} onChange={(e) => setSensor(e.target.value)}>
            {sensors.map((s) => (
              <option key={s.sensor_id} value={s.sensor_id}>
                {s.sensor_id} · {s.component_id} · {s.measurement} ({s.unit})
              </option>
            ))}
          </select>
        </label>
        <label>
          Readings{' '}
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            {LIMITS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Chart sensorId={sensorId} limit={limit} />
    </>
  )
}

export default function Telemetry() {
  const list = useAsync(api.facilities, 'facilities')
  const [selected, setSelected] = useState('')

  if (list.loading) return <Loading label="Loading facilities…" />
  if (list.error) return <ErrorBox message={list.error} onRetry={list.reload} />
  if (!list.data || list.data.length === 0) return <Empty text="No facilities found." />

  const facilityId = selected || list.data[0].facility_id

  return (
    <Section title="Telemetry">
      <div className="toolbar">
        <label>
          Facility{' '}
          <select value={facilityId} onChange={(e) => setSelected(e.target.value)}>
            {list.data.map((f) => (
              <option key={f.facility_id} value={f.facility_id}>
                {f.facility_id} · {f.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Picker key={facilityId} facilityId={facilityId} />
    </Section>
  )
}