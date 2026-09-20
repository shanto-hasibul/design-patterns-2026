const sections = [
  {
    id: 'overview',
    title: 'Overview',
    description: 'Greenhouse summary and system status will appear here.',
  },
  {
    id: 'sensors',
    title: 'Sensors',
    description: 'Temperature, humidity, soil and other sensor data will appear here.',
  },
  {
    id: 'controls',
    title: 'Controls',
    description: 'Manual greenhouse controls will appear here.',
  },
  {
    id: 'automation',
    title: 'Automation',
    description: 'Automation rules and schedules will appear here.',
  },
  {
    id: 'configuration',
    title: 'Configuration',
    description: 'Greenhouse configuration options will appear here.',
  },
  {
    id: 'events',
    title: 'Events',
    description: 'System events and activity history will appear here.',
  },
]

export default function DashboardPage() {
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-3xl font-bold">Smart Greenhouse Dashboard</h2>
        <p className="mt-2 text-slate-600">
          Phase 1 dashboard shell for future greenhouse features.
        </p>
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
          </section>
        ))}
      </div>
    </div>
  )
}