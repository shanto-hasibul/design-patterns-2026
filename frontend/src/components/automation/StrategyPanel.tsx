import { useEffect, useState } from 'react'
import {
  evaluateLocationAutomation,
  fetchLocations,
  fetchLocationStrategy,
  saveLocationStrategy,
  type EvaluateResponseDto,
  type LocationSummaryDto,
} from '../../services/api'

export function StrategyPanel() {
  const [locations, setLocations] = useState<LocationSummaryDto[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<string>('')
  const [strategyKey, setStrategyKey] = useState<string>('conservative')
  const [recommendation, setRecommendation] =
    useState<EvaluateResponseDto | null>(null)
  const [saving, setSaving] = useState<boolean>(false)
  const [evaluating, setEvaluating] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const loadLocations = async () => {
    try {
      const list = await fetchLocations()
      setLocations(list)
      if (list.length > 0 && !list.some((l) => l.id === selectedLocationId)) {
        setSelectedLocationId(list[0].id)
      } else if (list.length === 0) {
        setSelectedLocationId('')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load locations')
    }
  }

  useEffect(() => {
    void loadLocations()

    const onLocationsUpdated = () => {
      void loadLocations()
    }
    window.addEventListener('greenhouse-locations-updated', onLocationsUpdated)
    return () => {
      window.removeEventListener(
        'greenhouse-locations-updated',
        onLocationsUpdated,
      )
    }
  }, [])

  useEffect(() => {
    if (!selectedLocationId) {
      setRecommendation(null)
      return
    }
    setError(null)
    setSuccess(null)
    setRecommendation(null)
    void fetchLocationStrategy(selectedLocationId)
      .then((rule) => setStrategyKey(rule.strategy_key))
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : 'Failed to load active strategy',
        ),
      )
  }, [selectedLocationId])

  const handleSaveStrategy = async () => {
    if (!selectedLocationId) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const saved = await saveLocationStrategy(selectedLocationId, strategyKey)
      setStrategyKey(saved.strategy_key)
      setSuccess(`Saved "${saved.strategy_key}" strategy for location.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save strategy')
    } finally {
      setSaving(false)
    }
  }

  const handleEvaluate = async () => {
    if (!selectedLocationId) return
    setEvaluating(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await evaluateLocationAutomation(selectedLocationId)
      setRecommendation(result)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to evaluate automation',
      )
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="mt-4 space-y-4 text-sm">
      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-xs text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-2 text-xs text-emerald-800">
          {success}
        </div>
      )}

      {locations.length === 0 ? (
        <p className="text-xs text-slate-500">
          Create a location in Configuration first to assign and evaluate an
          automation strategy.
        </p>
      ) : (
        <>
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-700">
              Target Location
            </label>
            <select
              value={selectedLocationId}
              onChange={(e) => setSelectedLocationId(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-600 focus:outline-none"
            >
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-700">
              Irrigation Strategy
            </label>
            <div className="flex flex-wrap gap-2">
              <select
                value={strategyKey}
                onChange={(e) => setStrategyKey(e.target.value)}
                className="flex-1 rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs focus:border-indigo-600 focus:outline-none"
              >
                <option value="conservative">
                  Conservative (irrigate below low threshold)
                </option>
                <option value="aggressive">
                  Aggressive (irrigate below midpoint)
                </option>
              </select>
              <button
                type="button"
                disabled={saving}
                onClick={handleSaveStrategy}
                className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>

          <div>
            <button
              type="button"
              disabled={evaluating}
              onClick={handleEvaluate}
              className="w-full rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {evaluating ? 'Evaluating...' : 'Evaluate Location Now'}
            </button>
          </div>

          {recommendation && (
            <div className="space-y-2 rounded border border-slate-200 bg-slate-50 p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-700">
                  Strategy: {recommendation.strategy_key}
                </span>
                <span
                  className={`rounded px-2 py-0.5 font-bold uppercase ${
                    recommendation.action === 'irrigate'
                      ? 'bg-sky-100 text-sky-800'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {recommendation.action}
                </span>
              </div>
              <p className="text-slate-700">{recommendation.reason}</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}