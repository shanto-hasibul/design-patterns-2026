import { useEffect, useState } from 'react'
import {
  executeActuatorCommand,
  fetchCommandHistory,
  fetchDevices,
  type CommandLogResponseDto,
  type DeviceDto,
} from '../../services/api'

export function CommandPanel() {
  const [actuators, setActuators] = useState<DeviceDto[]>([])
  const [selectedActuatorId, setSelectedActuatorId] = useState<string>('')
  const [lightLevel, setLightLevel] = useState<string>('1')
  const [history, setHistory] = useState<CommandLogResponseDto[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error'
    text: string
  } | null>(null)

  const loadActuatorsAndHistory = async () => {
    setLoading(true)
    try {
      const [devs, logs] = await Promise.all([
        fetchDevices(undefined, 'actuator'),
        fetchCommandHistory(50),
      ])
      setActuators(devs)
      if (devs.length > 0 && !devs.some((d) => d.id === selectedActuatorId)) {
        setSelectedActuatorId(devs[0].id)
      }
      setHistory(logs)
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load commands',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadActuatorsAndHistory()
  }, [])

  const selectedActuator = actuators.find((a) => a.id === selectedActuatorId)
  const allowedCommands = selectedActuator?.allowed_commands ?? []

  const handleDispatchCommand = async (
    commandType: 'start_pump' | 'stop_pump' | 'set_light_level',
  ) => {
    if (!selectedActuatorId) return
    setSubmitting(true)
    setFeedback(null)

    const payload =
      commandType === 'set_light_level'
        ? { level: Number(lightLevel) || 0 }
        : {}

    try {
      const result = await executeActuatorCommand(
        commandType,
        selectedActuatorId,
        payload,
      )
      if (result.status === 'success') {
        setFeedback({
          type: 'success',
          text: `Executed ${result.command_type} (status: success).`,
        })
      } else {
        setFeedback({
          type: 'error',
          text: `${result.status.toUpperCase()}: ${result.error_message || 'Command blocked'}`,
        })
      }
      await loadActuatorsAndHistory()
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to execute command',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const statusBadgeClass = (status: string) => {
    if (status === 'success') return 'bg-emerald-100 text-emerald-800'
    if (status === 'rejected') return 'bg-amber-100 text-amber-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <div className="mt-4 space-y-4 text-sm">
      {feedback && (
        <div
          className={`rounded border p-2 text-xs ${
            feedback.type === 'success'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
              : 'border-red-300 bg-red-50 text-red-700'
          }`}
        >
          {feedback.text}
        </div>
      )}

      {actuators.length === 0 ? (
        <p className="text-xs text-slate-500">
          Provision a simulation or edge device kit first to send actuator
          commands.
        </p>
      ) : (
        <div className="space-y-3 rounded border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="space-y-1">
            <label className="block font-medium text-slate-700">
              Target Actuator
            </label>
            <select
              value={selectedActuatorId}
              onChange={(e) => setSelectedActuatorId(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            >
              {actuators.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.display_name} — state: {a.state ?? 'idle'}
                </option>
              ))}
            </select>
          </div>

          {selectedActuator && (
            <div className="text-[11px] text-slate-600">
              <strong>Current State:</strong>{' '}
              <span className="font-mono uppercase text-slate-900">
                {selectedActuator.state ?? 'idle'}
              </span>{' '}
              · <strong>Allowed:</strong>{' '}
              {allowedCommands.length > 0 ? allowedCommands.join(', ') : 'none'}
            </div>
          )}

          {/* Pump & Light Command Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={submitting || !allowedCommands.includes('start_pump')}
              onClick={() => handleDispatchCommand('start_pump')}
              className="rounded bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              Start Pump
            </button>
            <button
              type="button"
              disabled={submitting || !allowedCommands.includes('stop_pump')}
              onClick={() => handleDispatchCommand('stop_pump')}
              className="rounded bg-amber-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              Stop Pump
            </button>
          </div>

          {/* Set Light Level Control */}
          <div className="flex items-center gap-2 border-t border-slate-200 pt-2">
            <label className="text-slate-600">Light Level:</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={lightLevel}
              onChange={(e) => setLightLevel(e.target.value)}
              className="w-16 rounded border border-slate-300 bg-white px-2 py-1 text-xs"
            />
            <button
              type="button"
              disabled={
                submitting || !allowedCommands.includes('set_light_level')
              }
              onClick={() => handleDispatchCommand('set_light_level')}
              className="rounded bg-indigo-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              Set Light Level
            </button>
          </div>
        </div>
      )}

      {/* Command Log History Table */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-800">
            Command History
          </h4>
          <button
            type="button"
            onClick={() => void loadActuatorsAndHistory()}
            className="text-[11px] text-indigo-600 hover:underline"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <p className="text-xs text-slate-500">Loading command history...</p>
        ) : history.length === 0 ? (
          <p className="text-xs text-slate-500">No commands executed yet.</p>
        ) : (
          <div className="overflow-x-auto rounded border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="px-2 py-1.5 font-semibold">Command</th>
                  <th className="px-2 py-1.5 font-semibold">Status</th>
                  <th className="px-2 py-1.5 font-semibold">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {history.map((item) => (
                  <tr key={item.id}>
                    <td className="px-2 py-1.5 font-mono text-[11px] text-slate-800">
                      {item.command_type}
                    </td>
                    <td className="px-2 py-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${statusBadgeClass(
                          item.status,
                        )}`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-[11px] text-slate-600">
                      {item.error_message
                        ? item.error_message
                        : JSON.stringify(item.payload)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}