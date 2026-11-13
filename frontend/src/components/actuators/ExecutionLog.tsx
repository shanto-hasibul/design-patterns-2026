import { useEffect, useState } from 'react'
import {
  applyActuatorCommand,
  fetchActuatorExecutions,
  fetchDevices,
  type ActuatorExecutionDto,
  type DeviceDto,
} from '../../services/api'

export function ExecutionLog() {
  const [actuators, setActuators] = useState<DeviceDto[]>([])
  const [selectedActuatorId, setSelectedActuatorId] = useState<string>('')
  const [commandInput, setCommandInput] = useState<string>('start_pump')
  const [executions, setExecutions] = useState<ActuatorExecutionDto[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [applying, setApplying] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [devs, logs] = await Promise.all([
        fetchDevices(undefined, 'actuator'),
        fetchActuatorExecutions(20),
      ])
      setActuators(devs)
      if (devs.length > 0 && !devs.some((d) => d.id === selectedActuatorId)) {
        setSelectedActuatorId(devs[0].id)
      }
      setExecutions(logs)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load execution log',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const handleDemoApply = async () => {
    if (!selectedActuatorId || !commandInput.trim()) return
    setApplying(true)
    setError(null)
    try {
      await applyActuatorCommand(selectedActuatorId, commandInput.trim(), {})
      const logs = await fetchActuatorExecutions(20)
      setExecutions(logs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply command')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="mt-4 space-y-4 text-sm">
      <p className="rounded border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-600">
        Any command succeeds until the actuator has been{' '}
        <strong>running</strong> for 30 minutes. A successful attempt logs{' '}
        <code className="font-mono">policy_applied: [&quot;logging&quot;]</code>{' '}
        with an empty message, while a blocked attempt shows{' '}
        <code className="font-mono">Max run time exceeded</code> with policies{' '}
        <code className="font-mono">maxRunTime</code> and{' '}
        <code className="font-mono">logging</code>.
      </p>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Demo Apply Control */}
      {actuators.length > 0 && (
        <div className="space-y-2 rounded border border-slate-200 bg-slate-50 p-2.5 text-xs">
          <div className="flex flex-col gap-2">
            <select
              value={selectedActuatorId}
              onChange={(e) => setSelectedActuatorId(e.target.value)}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
            >
              {actuators.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.display_name} ({a.state ?? 'idle'})
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                placeholder="Command (e.g. start_pump)"
                className="flex-1 rounded border border-slate-300 bg-white px-2 py-1 text-xs"
              />
              <button
                type="button"
                disabled={applying}
                onClick={handleDemoApply}
                className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {applying ? 'Applying...' : 'Apply'}
              </button>
              <button
                type="button"
                onClick={() => void loadData()}
                className="rounded bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Execution Log Table */}
      {loading ? (
        <p className="text-xs text-slate-500">Loading execution log...</p>
      ) : executions.length === 0 ? (
        <p className="text-xs text-slate-500">
          No actuator execution attempts logged yet.
        </p>
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-2.5 py-1.5 font-semibold">Status</th>
                <th className="px-2.5 py-1.5 font-semibold">Policies</th>
                <th className="px-2.5 py-1.5 font-semibold">Message</th>
                <th className="px-2.5 py-1.5 font-semibold">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {executions.map((row) => (
                <tr key={row.id}>
                  <td className="px-2.5 py-1.5">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[11px] font-bold ${
                        row.success
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {row.success ? 'SUCCESS' : 'BLOCKED'}
                    </span>
                  </td>
                  <td className="px-2.5 py-1.5 font-mono text-[11px] text-slate-700">
                    {row.policy_applied.join(', ')}
                  </td>
                  <td className="px-2.5 py-1.5 text-slate-600">
                    {row.message || '—'}
                  </td>
                  <td className="px-2.5 py-1.5 text-[11px] text-slate-500">
                    {new Date(row.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}