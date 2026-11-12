export type DeviceFamilyKey = 'simulation' | 'edge'

interface DeviceFamilySwitcherProps {
  selectedFamily: DeviceFamilyKey
  onSelectFamily: (family: DeviceFamilyKey) => void
  onProvision: () => void
  provisioning: boolean
}

export function DeviceFamilySwitcher({
  selectedFamily,
  onSelectFamily,
  onProvision,
  provisioning,
}: DeviceFamilySwitcherProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1">
        <button
          type="button"
          onClick={() => onSelectFamily('simulation')}
          className={`rounded-md px-3 py-1 text-xs font-medium transition ${
            selectedFamily === 'simulation'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Simulation
        </button>
        <button
          type="button"
          onClick={() => onSelectFamily('edge')}
          className={`rounded-md px-3 py-1 text-xs font-medium transition ${
            selectedFamily === 'edge'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Edge
        </button>
      </div>

      <button
        type="button"
        onClick={onProvision}
        disabled={provisioning}
        className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {provisioning
          ? 'Provisioning...'
          : `+ Provision ${selectedFamily === 'simulation' ? 'Simulation' : 'Edge'} Kit`}
      </button>
    </div>
  )
}