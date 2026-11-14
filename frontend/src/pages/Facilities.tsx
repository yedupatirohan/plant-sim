import { useState } from 'react'
import { api } from '../api'
import { Badge, Empty, ErrorBox, Loading, Section } from '../ui'
import { useAsync } from '../useAsync'

function Detail({ facilityId }: { facilityId: string }) {
  const comp = useAsync(() => api.components(facilityId), `components-${facilityId}`)
  const topo = useAsync(() => api.topology(facilityId), `topology-${facilityId}`)

  if (comp.loading) return <Loading label="Loading components…" />
  if (comp.error) return <ErrorBox message={comp.error} onRetry={comp.reload} />
  if (!comp.data) return <Empty text="No data." />
  const c = comp.data

  return (
    <>
      <Section title="Network check">
        {topo.loading && <Loading />}
        {topo.error && <ErrorBox message={topo.error} onRetry={topo.reload} />}
        {topo.data && (
          <p>
            <Badge value={topo.data.status} /> {topo.data.node_count} nodes, {topo.data.pipe_count}{' '}
            pipes, {topo.data.component_count} connected group(s). Isolated nodes:{' '}
            {topo.data.isolated_nodes.length}. Invalid pipes: {topo.data.invalid_pipes.length}.
          </p>
        )}
      </Section>

      <Section title={`Pumps (${c.pumps.length})`}>
        {c.pumps.length === 0 ? (
          <Empty text="No pumps." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Rated flow (m³/h)</th>
                <th>Shutoff head (m)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {c.pumps.map((p) => (
                <tr key={p.pump_id}>
                  <td>{p.pump_id}</td>
                  <td>{p.name}</td>
                  <td>{p.rated_flow_m3h}</td>
                  <td>{p.shutoff_head_m}</td>
                  <td>
                    <Badge value={p.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title={`Tanks (${c.tanks.length})`}>
        {c.tanks.length === 0 ? (
          <Empty text="No tanks." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Capacity (m³)</th>
                <th>Min level (%)</th>
                <th>Max level (%)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {c.tanks.map((t) => (
                <tr key={t.tank_id}>
                  <td>{t.tank_id}</td>
                  <td>{t.name}</td>
                  <td>{t.capacity_m3}</td>
                  <td>{t.min_level_pct}</td>
                  <td>{t.max_level_pct}</td>
                  <td>
                    <Badge value={t.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title={`Valves (${c.valves.length})`}>
        {c.valves.length === 0 ? (
          <Empty text="No valves." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Default state</th>
                <th>Default position (%)</th>
              </tr>
            </thead>
            <tbody>
              {c.valves.map((v) => (
                <tr key={v.valve_id}>
                  <td>{v.valve_id}</td>
                  <td>{v.name}</td>
                  <td>{v.default_state}</td>
                  <td>{v.default_position_pct}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <p className="muted">
        {c.pipes.length} pipes and {c.sensors.length} sensors in this facility.
      </p>
    </>
  )
}

export default function Facilities() {
  const list = useAsync(api.facilities, 'facilities')
  const [selected, setSelected] = useState('')

  if (list.loading) return <Loading label="Loading facilities…" />
  if (list.error) return <ErrorBox message={list.error} onRetry={list.reload} />
  if (!list.data || list.data.length === 0) return <Empty text="No facilities found." />

  const facilityId = selected || list.data[0].facility_id
  const current = list.data.find((f) => f.facility_id === facilityId)

  return (
    <>
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
        {current && <Badge value={current.status} />}
      </div>
      <Detail key={facilityId} facilityId={facilityId} />
    </>
  )
}