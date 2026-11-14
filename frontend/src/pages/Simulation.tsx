import { useState } from 'react'
import { api } from '../api'
import type { SimulationIn, SimulationOut } from '../types'
import { Badge, Empty, ErrorBox, Loading, Section } from '../ui'
import { useAsync } from '../useAsync'

interface SimResult {
  facility_id: string
  inflow_m3h: number
  outflow_m3h: number
  storage_change_m3h: number
  hours_until_tanks_full: number | null
  warnings: string[]
  pumps: { pump_id: string; flow_m3h: number; head_m: number; pressure_kpa: number }[]
}

function resultOf(sim: SimulationOut): SimResult {
  return sim.result as unknown as SimResult
}

function Outcome({ sim }: { sim: SimulationOut }) {
  const r = resultOf(sim)
  return (
    <>
      <p>
        <strong>{sim.simulation_id}</strong> <Badge value={sim.status} /> mode {sim.mode_id}, seed{' '}
        {sim.seed}, facility {r.facility_id}
      </p>
      <table>
        <thead>
          <tr>
            <th>Inflow (m³/h)</th>
            <th>Outflow (m³/h)</th>
            <th>Storage change (m³/h)</th>
            <th>Hours until tanks full</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{r.inflow_m3h}</td>
            <td>{r.outflow_m3h}</td>
            <td>{r.storage_change_m3h}</td>
            <td>{r.hours_until_tanks_full ?? 'n/a'}</td>
          </tr>
        </tbody>
      </table>
      {r.warnings.length > 0 && <p className="notice">Warnings: {r.warnings.join(', ')}</p>}
      <h3>Pumps</h3>
      <table>
        <thead>
          <tr>
            <th>Pump</th>
            <th>Flow (m³/h)</th>
            <th>Head (m)</th>
            <th>Pressure (kPa)</th>
          </tr>
        </thead>
        <tbody>
          {r.pumps.map((p) => (
            <tr key={p.pump_id}>
              <td>{p.pump_id}</td>
              <td>{p.flow_m3h}</td>
              <td>{p.head_m}</td>
              <td>{p.pressure_kpa}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Assumptions used</h3>
      <pre>{JSON.stringify(sim.assumptions, null, 2)}</pre>
    </>
  )
}

function Form({ facilityId, onDone }: { facilityId: string; onDone: (s: SimulationOut) => void }) {
  const modes = useAsync(() => api.modes(facilityId), `modes-${facilityId}`)
  const [mode, setMode] = useState('')
  const [speed, setSpeed] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (modes.loading) return <Loading label="Loading operating modes…" />
  if (modes.error) return <ErrorBox message={modes.error} onRetry={modes.reload} />
  if (!modes.data || modes.data.length === 0) return <Empty text="No operating modes here." />

  const modeId = mode || modes.data[0].mode_id

  async function submit() {
    setBusy(true)
    setError(null)
    const body: SimulationIn = { mode_id: modeId }
    if (speed !== '') body.pump_speed_pct = Number(speed)
    try {
      onDone(await api.simulate(body))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="toolbar">
        <label>
          Operating mode{' '}
          <select value={modeId} onChange={(e) => setMode(e.target.value)}>
            {modes.data.map((m) => (
              <option key={m.mode_id} value={m.mode_id}>
                {m.mode_id} · {m.name} ({m.pump_speed_pct}%)
              </option>
            ))}
          </select>
        </label>
        <label>
          Pump speed override (%){' '}
          <input
            type="number"
            min={0}
            max={100}
            placeholder="use mode speed"
            value={speed}
            onChange={(e) => setSpeed(e.target.value)}
          />
        </label>
        <button disabled={busy} onClick={submit}>
          {busy ? 'Running…' : 'Run simulation'}
        </button>
      </div>
      {error && <ErrorBox message={error} />}
    </>
  )
}

export default function Simulation() {
  const facilities = useAsync(api.facilities, 'facilities')
  const runs = useAsync(api.simulations, 'simulations')
  const [selected, setSelected] = useState('')
  const [last, setLast] = useState<SimulationOut | null>(null)

  if (facilities.loading) return <Loading label="Loading facilities…" />
  if (facilities.error) return <ErrorBox message={facilities.error} onRetry={facilities.reload} />
  if (!facilities.data || facilities.data.length === 0) return <Empty text="No facilities found." />

  const facilityId = selected || facilities.data[0].facility_id

  return (
    <>
      <Section title="New simulation">
        <div className="toolbar">
          <label>
            Facility{' '}
            <select value={facilityId} onChange={(e) => setSelected(e.target.value)}>
              {facilities.data.map((f) => (
                <option key={f.facility_id} value={f.facility_id}>
                  {f.facility_id} · {f.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Form
          key={facilityId}
          facilityId={facilityId}
          onDone={(s) => {
            setLast(s)
            runs.reload()
          }}
        />
        {last && <Outcome sim={last} />}
      </Section>

      <Section title="Stored simulation runs">
        {runs.loading && <Loading />}
        {runs.error && <ErrorBox message={runs.error} onRetry={runs.reload} />}
        {runs.data && runs.data.length === 0 && <Empty text="No simulations run yet." />}
        {runs.data && runs.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Simulation</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Inflow (m³/h)</th>
                <th>Outflow (m³/h)</th>
              </tr>
            </thead>
            <tbody>
              {runs.data.map((s) => (
                <tr key={s.simulation_id}>
                  <td>{s.simulation_id}</td>
                  <td>{s.mode_id}</td>
                  <td>
                    <Badge value={s.status} />
                  </td>
                  <td>{resultOf(s).inflow_m3h}</td>
                  <td>{resultOf(s).outflow_m3h}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </>
  )
}