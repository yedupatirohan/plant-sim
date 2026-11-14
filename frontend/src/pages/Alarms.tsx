import { Fragment, useState } from 'react'
import { api } from '../api'
import { Badge, Empty, ErrorBox, Loading, Section } from '../ui'
import { useAsync } from '../useAsync'

const STATES = ['', 'RAISED', 'ACKNOWLEDGED', 'CLEARED']

function History({ alarmId }: { alarmId: string }) {
  const h = useAsync(() => api.alarmHistory(alarmId), `history-${alarmId}`)
  if (h.loading) return <Loading label="Loading history…" />
  if (h.error) return <ErrorBox message={h.error} onRetry={h.reload} />
  if (!h.data || h.data.length === 0) return <Empty text="No history." />
  return (
    <ol>
      {h.data.map((e, i) => (
        <li key={i}>
          {e.old_state ?? 'new'} → {e.new_state} at {e.changed_at}
        </li>
      ))}
    </ol>
  )
}

export default function Alarms() {
  const [state, setState] = useState('')
  const [open, setOpen] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const list = useAsync(() => api.alarms(state || undefined), `alarms-${state}`)

  async function act(run: () => Promise<string>) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      setMessage(await run())
      list.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Alarms">
      <div className="toolbar">
        <label>
          State{' '}
          <select value={state} onChange={(e) => setState(e.target.value)}>
            {STATES.map((s) => (
              <option key={s} value={s}>
                {s === '' ? 'All' : s}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={busy}
          onClick={() =>
            act(async () => {
              const r = await api.detectRun()
              return `Detection found ${r.events_found} event(s) and created ${r.alarms_created} new alarm(s).`
            })
          }
        >
          Run detection
        </button>
      </div>

      {message && <p className="notice">{message}</p>}
      {error && <ErrorBox message={error} />}

      {list.loading && <Loading label="Loading alarms…" />}
      {list.error && <ErrorBox message={list.error} onRetry={list.reload} />}
      {list.data && list.data.length === 0 && (
        <Empty text="No alarms yet. Press Run detection to raise alarms from the telemetry." />
      )}
      {list.data && list.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Alarm</th>
              <th>Facility</th>
              <th>Sensor</th>
              <th>Type</th>
              <th>State</th>
              <th>Raised (UTC)</th>
              <th>Cleared</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {list.data.map((a) => (
              <Fragment key={a.alarm_id}>
                <tr>
                  <td>{a.alarm_id}</td>
                  <td>{a.facility_id}</td>
                  <td>{a.sensor_id ?? ''}</td>
                  <td>{a.alarm_type}</td>
                  <td>
                    <Badge value={a.state} />
                  </td>
                  <td>{a.raised_at}</td>
                  <td>{a.cleared_at ?? ''}</td>
                  <td className="actions">
                    {a.state === 'RAISED' && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          act(async () => {
                            await api.acknowledge(a.alarm_id)
                            return `${a.alarm_id} acknowledged.`
                          })
                        }
                      >
                        Acknowledge
                      </button>
                    )}
                    {a.state !== 'CLEARED' && (
                      <button
                        disabled={busy}
                        onClick={() =>
                          act(async () => {
                            await api.clear(a.alarm_id)
                            return `${a.alarm_id} cleared.`
                          })
                        }
                      >
                        Clear
                      </button>
                    )}
                    <button onClick={() => setOpen(open === a.alarm_id ? '' : a.alarm_id)}>
                      {open === a.alarm_id ? 'Hide history' : 'History'}
                    </button>
                  </td>
                </tr>
                {open === a.alarm_id && (
                  <tr>
                    <td colSpan={8}>
                      <History alarmId={a.alarm_id} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  )
}