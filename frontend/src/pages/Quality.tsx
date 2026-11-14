import { api } from '../api'
import { Badge, Empty, ErrorBox, Loading, Section } from '../ui'
import { useAsync } from '../useAsync'

function num(value: number | null): string {
  return value === null ? 'n/a' : value.toFixed(3)
}

function Metrics() {
  const m = useAsync(api.metrics, 'metrics')
  if (m.loading) return <Loading label="Scoring detection…" />
  if (m.error) return <ErrorBox message={m.error} onRetry={m.reload} />
  if (!m.data) return <Empty text="No metrics." />
  const d = m.data

  return (
    <>
      <table>
        <thead>
          <tr>
            <th>Scenarios</th>
            <th>Detections</th>
            <th>TP</th>
            <th>FP</th>
            <th>FN</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
            <th>Mean delay (min)</th>
            <th>Max delay (min)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{d.truth_scenarios}</td>
            <td>{d.detections}</td>
            <td>{d.true_positives}</td>
            <td>{d.false_positives}</td>
            <td>{d.false_negatives}</td>
            <td>{num(d.precision)}</td>
            <td>{num(d.recall)}</td>
            <td>{num(d.f1)}</td>
            <td>{d.mean_delay_min ?? 'n/a'}</td>
            <td>{d.max_delay_min ?? 'n/a'}</td>
          </tr>
        </tbody>
      </table>

      <h3>By alarm type</h3>
      <table>
        <thead>
          <tr>
            <th>Alarm type</th>
            <th>TP</th>
            <th>FP</th>
            <th>FN</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(d.per_type).map(([type, c]) => (
            <tr key={type}>
              <td>{type}</td>
              <td>{c.tp}</td>
              <td>{c.fp}</td>
              <td>{c.fn}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Edge cases the detector can see</h3>
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Issue</th>
            <th>Expected alarm</th>
            <th>Detected</th>
          </tr>
        </thead>
        <tbody>
          {d.edge_cases.map((e) => (
            <tr key={e.scenario_id}>
              <td>{e.scenario_id}</td>
              <td>{e.issue_type}</td>
              <td>{e.expected_alarm_type}</td>
              <td>{e.detected ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {d.not_scored_here.length > 0 && (
        <p className="muted">
          Checked by other services, not scored here:{' '}
          {d.not_scored_here.map((n) => `${n.scenario_id} (${n.issue_type})`).join(', ')}.
        </p>
      )}
    </>
  )
}

export default function Quality() {
  const q = useAsync(api.dataQuality, 'data-quality')
  if (q.loading) return <Loading label="Checking data quality…" />
  if (q.error) return <ErrorBox message={q.error} onRetry={q.reload} />
  if (!q.data) return <Empty text="No report." />
  const d = q.data

  return (
    <>
      <Section title="Overall">
        <p>
          <Badge value={d.overall} /> Telemetry from {d.telemetry_from ?? 'n/a'} to{' '}
          {d.telemetry_to ?? 'n/a'} (UTC).
        </p>
        <table>
          <thead>
            <tr>
              {Object.keys(d.counts).map((k) => (
                <th key={k}>{k.replace(/_/g, ' ')}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {Object.entries(d.counts).map(([k, v]) => (
                <td key={k}>{v.toLocaleString()}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </Section>

      <Section title="Topology by facility">
        <table>
          <thead>
            <tr>
              <th>Facility</th>
              <th>Status</th>
              <th>Nodes</th>
              <th>Pipes</th>
              <th>Connected</th>
              <th>Invalid pipes</th>
            </tr>
          </thead>
          <tbody>
            {d.topology.map((t) => (
              <tr key={t.facility_id}>
                <td>{t.facility_id}</td>
                <td>
                  <Badge value={t.status} />
                </td>
                <td>{t.node_count}</td>
                <td>{t.pipe_count}</td>
                <td>{t.connected ? 'Yes' : 'No'}</td>
                <td>{t.invalid_pipes.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Flow balance by facility">
        <table>
          <thead>
            <tr>
              <th>Facility</th>
              <th>Status</th>
              <th>Windows checked</th>
              <th>Violation windows</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {d.balance.map((b) => (
              <tr key={b.facility_id}>
                <td>{b.facility_id}</td>
                <td>
                  <Badge value={b.status} />
                </td>
                <td>{b.windows_checked}</td>
                <td>{b.violation_windows}</td>
                <td>{b.note ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Detection metrics against ground truth">
        <Metrics />
      </Section>
    </>
  )
}