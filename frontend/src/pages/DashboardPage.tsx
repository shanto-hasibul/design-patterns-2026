import { useEffect, useState } from 'react'
import { ExecutionLog } from '../components/actuators/ExecutionLog'
import { StrategyPanel } from '../components/automation/StrategyPanel'
import { CommandPanel } from '../components/commands/CommandPanel'
import { LocationConfigWizard } from '../components/config/LocationConfigWizard'
import { DeviceList } from '../components/devices/DeviceList'
import { EventFeed } from '../components/events/EventFeed'
import { OverviewPanel } from '../components/overview/OverviewPanel'
import { SensorList } from '../features/sensors/SensorList'
import {
  subscribeRealtimeStatus,
  type RealtimeStatus,
} from '../services/realtime'

const sections = [
  {
    id: 'overview',
    title: 'Overview',
    description:
      'Single-endpoint location summary aggregating zones, devices, readings, and strategy (Facade).',
  },
  {
    id: 'sensors',
    title: 'Sensors',
    description: 'Create and view moisture and light sensors (Factory Method).',
  },
  {
    id: 'devices',
    title: 'Devices',
    description:
      'Provision coherent sensor and actuator kits and assign zones (Abstract Factory).',
  },
  {
    id: 'controls',
    title: 'Controls',
    description:
      'Dispatch audited actuator commands respecting allowed_commands and inspect execution logs (Command & Decorator).',
  },
  {
    id: 'automation',
    title: 'Automation',
    description:
      'Select and evaluate pluggable irrigation strategies per location (Strategy).',
  },
  {
    id: 'configuration',
    title: 'Configuration',
    description:
      'Build and manage locations and zones with moisture thresholds (Builder).',
  },
  {
    id: 'events',
    title: 'Events',
    description:
      'Persisted domain alerts and live event feed filtered by location and zone (Observer & WS).',
  },
]

export default function DashboardPage() {
  const [wsStatus, setWsStatus] = useState<RealtimeStatus>('connecting')

  useEffect(() => {
    return subscribeRealtimeStatus(setWsStatus)
  }, [])

  const wsBadgeClass =
    wsStatus === 'connected'
      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
      : wsStatus === 'connecting'
        ? 'bg-amber-100 text-amber-800 border-amber-300'
        : 'bg-red-100 text-red-800 border-red-300'

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold">Smart Greenhouse Dashboard</h2>
          <p className="mt-2 text-slate-600">
            Production dashboard with live WebSocket fan-out, hardened schema,
            and full GoF architecture.
          </p>
        </div>

        <div
          className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${wsBadgeClass}`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              wsStatus === 'connected'
                ? 'bg-emerald-600'
                : wsStatus === 'connecting'
                  ? 'bg-amber-500'
                  : 'bg-red-600'
            }`}
          />
          <span>WS: {wsStatus}</span>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {sections.map((section) => (
          <section
            key={section.id}
            id={section.id}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h3 className="text-lg font-semibold">{section.title}</h3>
            <p className="mt-2 text-sm text-slate-600">
              {section.description}
            </p>
            {section.id === 'overview' && <OverviewPanel />}
            {section.id === 'sensors' && <SensorList />}
            {section.id === 'devices' && <DeviceList />}
            {section.id === 'controls' && (
              <>
                <CommandPanel />
                <hr className="my-5 border-slate-200" />
                <ExecutionLog />
              </>
            )}
            {section.id === 'automation' && <StrategyPanel />}
            {section.id === 'configuration' && <LocationConfigWizard />}
            {section.id === 'events' && <EventFeed />}
          </section>
        ))}
      </div>
    </div>
  )
}