import { useState } from 'react'
import './App.css'
import Alarms from './pages/Alarms'
import Facilities from './pages/Facilities'
import Quality from './pages/Quality'
import Simulation from './pages/Simulation'
import Telemetry from './pages/Telemetry'

const TABS = [
  { id: 'facilities', label: 'Facilities' },
  { id: 'telemetry', label: 'Telemetry' },
  { id: 'alarms', label: 'Alarms' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'quality', label: 'Data quality' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function App() {
  const [tab, setTab] = useState<TabId>('facilities')

  return (
    <div className="app">
      <header>
        <h1>Plant Simulation Dashboard</h1>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={t.id === tab ? 'tab active' : 'tab'}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'facilities' && <Facilities />}
        {tab === 'telemetry' && <Telemetry />}
        {tab === 'alarms' && <Alarms />}
        {tab === 'simulation' && <Simulation />}
        {tab === 'quality' && <Quality />}
      </main>
    </div>
  )
}