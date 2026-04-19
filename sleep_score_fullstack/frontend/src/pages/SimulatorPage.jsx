import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { predictSleep } from '../lib/api'
import './SimulatorPage.css'

const MG_PER_CUP = 95

function timeStringToHours(timeString) {
  const [hours, minutes] = timeString.split(':').map(Number)
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return 0
  return hours + minutes / 60
}

const SENSITIVITY_PRESETS = [
  { key: 'adjusted', label: 'Caffeine adjusted', multiplier: 0.7, description: 'Lower caffeine impact' },
  { key: 'average', label: 'Average', multiplier: 1.0, description: 'Baseline caffeine impact' },
  { key: 'sensitive', label: 'Very sensitive', multiplier: 1.5, description: 'Higher caffeine impact' },
]

function sensitivityLabel(multiplier) {
  if (multiplier <= 0.8) return 'Caffeine adjusted'
  if (multiplier >= 1.25) return 'Very sensitive'
  return 'Average sensitivity'
}

const INITIAL_STATE = {
  baseline_sleep_score: 75,
  weekend: false,
  bedtime_time: '',
  caffeine_sensitivity: 1.0,

  caffeine_doses: [{ time: '09:00', dose_mg: 95 }],
  alcohol_drinks: 0,

  morning_light_lux: 200,
  evening_light_lux: 30,
  night_light_minutes: 0,

  hours_wake_to_first_eat: 1,
  hours_last_eat_to_bed: 3,
  eating_window_hours: 12,

  rmssd_ms: null,
  resting_hr_bpm: null,
}

export default function SimulatorPage() {
  const [state, setState] = useState(INITIAL_STATE)

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const payload = useMemo(() => {
    const normalizedDoses = state.caffeine_doses
      .map((dose) => ({
        time_hours_after_midnight: Number(timeStringToHours(dose.time).toFixed(2)),
        dose_mg: Number(dose.dose_mg) || 0,
      }))
      .filter((dose) => dose.dose_mg > 0)

    const caffeine_cups = Number(
      (normalizedDoses.reduce((sum, dose) => sum + dose.dose_mg, 0) / MG_PER_CUP).toFixed(2)
    )

    return {
      ...state,
      caffeine_cups,
      caffeine_doses: normalizedDoses,
      bedtime_hours: state.bedtime_time ? Number(timeStringToHours(state.bedtime_time).toFixed(2)) : null,
    }
  }, [state])

  async function onRun() {
    setLoading(true)
    setError('')
    try {
      const out = await predictSleep(payload)
      setResult(out)
    } catch (e) {
      setError(e?.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  function onReset() {
    setState(INITIAL_STATE)
    setResult(null)
    setError('')
  }

  const score = result ? Math.round(result.sleep_score) : Math.round(state.baseline_sleep_score)
  const scoreArc = Math.max(0, Math.min(100, score)) * 3.6
  const scoreStatus = score >= 85 ? 'Optimized' : score >= 70 ? 'Strong' : score >= 55 ? 'Moderate' : 'Needs Recovery'
  const scoreMessage = result
    ? 'Your scenario has been simulated. Small adjustments in evening caffeine and light can materially change your score.'
    : 'Adjust your biological parameters to predict tonight\'s sleep quality and metabolic recovery.'

  const totalAlcoholUnits = state.alcohol_drinks
  const bedtimePreview = state.bedtime_time || 'Not set'

  return (
    <div className="sim-page">
      <header className="top-nav">
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <Link to="/" className="brand">Vitality Core</Link>
          <nav className="top-links">
            <Link className="top-link active" to="/simulator">Simulator</Link>
            <Link className="top-link" to="/history">History</Link>
            <Link className="top-link" to="/science">Science</Link>
          </nav>
        </div>
      </header>

      <div className="layout">
        <aside className="side-nav">
          <div className="side-header">
            <h2>Vitality Core</h2>
            <p>Sleep Score Simulator</p>
          </div>
          <div className="side-list">
            <Link to="/simulator" className="side-item active">
              <span className="material-symbols-outlined">analytics</span>
              Simulator
            </Link>
            <Link to="/history" className="side-item">
              <span className="material-symbols-outlined">history</span>
              History
            </Link>
            <Link to="/science" className="side-item">
              <span className="material-symbols-outlined">science</span>
              Science
            </Link>
          </div>
        </aside>

        <main className="main">
          <div className="main-wrap">
            <header className="page-head">
              <div>
                <h1 className="page-title">Sleep Score Simulator</h1>
                <p className="page-subtitle">
                  Adjust your biological parameters to predict tonight's sleep quality and metabolic recovery.
                </p>
              </div>
              <div className="page-actions">
                <button className="btn btn-ghost" type="button" onClick={onReset}>
                  <span className="material-symbols-outlined">refresh</span>
                  Reset All
                </button>
                <button className="btn btn-primary" type="button" onClick={onRun} disabled={loading}>
                  <span className="material-symbols-outlined">analytics</span>
                  {loading ? 'Running…' : 'Run Model'}
                </button>
              </div>
            </header>

            <div className="content-grid">
              <div className="left-stack">
                <section className="card">
                  <h3 className="card-title">
                    <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>bedtime</span>
                    Baseline &amp; Core
                  </h3>
                  <div className="field">
                    <div className="label-row">
                      <label className="label">Baseline Sleep Score</label>
                      <span className="label-value">{state.baseline_sleep_score}</span>
                    </div>
                    <input
                      className="slider"
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={state.baseline_sleep_score}
                      onChange={(e) => setState((s) => ({ ...s, baseline_sleep_score: Number(e.target.value) }))}
                    />
                  </div>

                  <div className="field-grid-2" style={{ marginTop: 16 }}>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Bedtime</label>
                        <span className="label-value">{bedtimePreview}</span>
                      </div>
                      <input
                        className="time-input"
                        type="time"
                        value={state.bedtime_time}
                        onChange={(e) => setState((s) => ({ ...s, bedtime_time: e.target.value }))}
                      />
                    </div>
                    <div className="field">
                      <label className="label">Weekend Mode</label>
                      <button
                        type="button"
                        className="switch"
                        onClick={() => setState((s) => ({ ...s, weekend: !s.weekend }))}
                        aria-pressed={state.weekend}
                      >
                        <span className={`switch-track ${state.weekend ? 'on' : ''}`}>
                          <span className="switch-thumb" />
                        </span>
                        <span className="switch-label">{state.weekend ? 'Extended Routine' : 'Weekday Routine'}</span>
                      </button>
                    </div>
                  </div>
                </section>

                <section className="card">
                  <h3 className="card-title">
                    <span className="material-symbols-outlined" style={{ color: 'var(--secondary)' }}>local_cafe</span>
                    Substances
                  </h3>
                  <div className="field">
                    <div className="label-row">
                      <label className="label">Caffeine Doses</label>
                      <button className="inline-btn" type="button" onClick={() => setState((s) => ({ ...s, caffeine_doses: [...s.caffeine_doses, { time: '13:00', dose_mg: 95 }] }))}>
                        Add Dose
                      </button>
                    </div>

                    <div className="dose-list">
                      {state.caffeine_doses.map((dose, idx) => (
                        <div className="dose-item" key={idx}>
                          <input
                            className="time-input"
                            type="time"
                            value={dose.time}
                            onChange={(e) =>
                              setState((s) => ({
                                ...s,
                                caffeine_doses: s.caffeine_doses.map((d, i) => (i === idx ? { ...d, time: e.target.value } : d)),
                              }))
                            }
                          />
                          <input
                            className="number-input"
                            type="number"
                            min={0}
                            max={1000}
                            step={5}
                            value={dose.dose_mg}
                            onChange={(e) =>
                              setState((s) => ({
                                ...s,
                                caffeine_doses: s.caffeine_doses.map((d, i) =>
                                  i === idx ? { ...d, dose_mg: Number(e.target.value) } : d
                                ),
                              }))
                            }
                          />
                          <button
                            className="remove-btn"
                            type="button"
                            onClick={() =>
                              setState((s) => ({
                                ...s,
                                caffeine_doses:
                                  s.caffeine_doses.length > 1
                                    ? s.caffeine_doses.filter((_, i) => i !== idx)
                                    : s.caffeine_doses,
                              }))
                            }
                            disabled={state.caffeine_doses.length <= 1}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>

                    <div className="inline-row">
                      <span className="inline-meta">
                        Total: {(payload.caffeine_cups || 0).toFixed(2)} cups ({Math.round((payload.caffeine_cups || 0) * MG_PER_CUP)} mg)
                      </span>
                    </div>
                  </div>

                  <div className="field-grid-2" style={{ marginTop: 16 }}>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Alcohol</label>
                        <span className="label-value">{totalAlcoholUnits.toFixed(1)} standard drinks</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={0}
                        max={10}
                        step={0.5}
                        value={state.alcohol_drinks}
                        onChange={(e) => setState((s) => ({ ...s, alcohol_drinks: Number(e.target.value) }))}
                      />
                    </div>

                    <div className="field">
                      <label className="label">Caffeine Sensitivity</label>
                      <select
                        className="select-input"
                        value={state.caffeine_sensitivity}
                        onChange={(e) => setState((s) => ({ ...s, caffeine_sensitivity: Number(e.target.value) }))}
                      >
                        {SENSITIVITY_PRESETS.map((preset) => (
                          <option value={preset.multiplier} key={preset.key}>
                            {preset.label} ({preset.multiplier.toFixed(2)}x)
                          </option>
                        ))}
                      </select>
                      <div className="helper">
                        {sensitivityLabel(state.caffeine_sensitivity)} ({state.caffeine_sensitivity.toFixed(2)}x caffeine penalty)
                      </div>
                    </div>
                  </div>
                </section>

                <section className="card">
                  <h3 className="card-title">
                    <span className="material-symbols-outlined" style={{ color: 'var(--tertiary)' }}>monitor_heart</span>
                    Recovery &amp; Rhythms
                  </h3>
                  <div className="field-grid-2">
                    <div className="field">
                      <label className="label">Baseline HRV (RMSSD)</label>
                      <input
                        className="number-input"
                        type="number"
                        value={state.rmssd_ms ?? ''}
                        placeholder="e.g., 72"
                        onChange={(e) =>
                          setState((s) => ({ ...s, rmssd_ms: e.target.value === '' ? null : Number(e.target.value) }))
                        }
                      />
                    </div>
                    <div className="field">
                      <label className="label">Resting HR</label>
                      <input
                        className="number-input"
                        type="number"
                        value={state.resting_hr_bpm ?? ''}
                        placeholder="e.g., 54"
                        onChange={(e) =>
                          setState((s) => ({ ...s, resting_hr_bpm: e.target.value === '' ? null : Number(e.target.value) }))
                        }
                      />
                    </div>
                  </div>

                  <div className="field-grid-2" style={{ marginTop: 16 }}>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Morning Light</label>
                        <span className="label-value">{state.morning_light_lux} lux</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={0}
                        max={2000}
                        step={10}
                        value={state.morning_light_lux}
                        onChange={(e) => setState((s) => ({ ...s, morning_light_lux: Number(e.target.value) }))}
                      />
                    </div>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Evening Light Exposure</label>
                        <span className="label-value">{state.evening_light_lux} lux</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={0}
                        max={1000}
                        step={10}
                        value={state.evening_light_lux}
                        onChange={(e) => setState((s) => ({ ...s, evening_light_lux: Number(e.target.value) }))}
                      />
                    </div>
                  </div>

                  <div className="field" style={{ marginTop: 16 }}>
                    <div className="label-row">
                      <label className="label">Night Light Minutes</label>
                      <span className="label-value">{state.night_light_minutes} min</span>
                    </div>
                    <input
                      className="slider"
                      type="range"
                      min={0}
                      max={180}
                      step={5}
                      value={state.night_light_minutes}
                      onChange={(e) => setState((s) => ({ ...s, night_light_minutes: Number(e.target.value) }))}
                    />
                  </div>
                </section>

                <section className="card">
                  <h3 className="card-title">
                    <span className="material-symbols-outlined" style={{ color: 'var(--primary)' }}>restaurant</span>
                    Metabolic Timing
                  </h3>
                  <div className="field-grid-3">
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Wake → First Eat</label>
                        <span className="label-value">{state.hours_wake_to_first_eat.toFixed(1)} h</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={0}
                        max={8}
                        step={0.5}
                        value={state.hours_wake_to_first_eat}
                        onChange={(e) => setState((s) => ({ ...s, hours_wake_to_first_eat: Number(e.target.value) }))}
                      />
                    </div>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Last Eat → Bed</label>
                        <span className="label-value">{state.hours_last_eat_to_bed.toFixed(1)} h</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={0}
                        max={8}
                        step={0.5}
                        value={state.hours_last_eat_to_bed}
                        onChange={(e) => setState((s) => ({ ...s, hours_last_eat_to_bed: Number(e.target.value) }))}
                      />
                    </div>
                    <div className="field">
                      <div className="label-row">
                        <label className="label">Eating Window</label>
                        <span className="label-value">{state.eating_window_hours.toFixed(1)} h</span>
                      </div>
                      <input
                        className="slider"
                        type="range"
                        min={4}
                        max={18}
                        step={0.5}
                        value={state.eating_window_hours}
                        onChange={(e) => setState((s) => ({ ...s, eating_window_hours: Number(e.target.value) }))}
                      />
                    </div>
                  </div>
                </section>

                {error ? <div className="error-box">{error}</div> : null}
              </div>

              <div className="right-stack">
                <section className="score-card">
                  <p className="score-kicker">Predicted Sleep Score</p>
                  <div className="score-ring" style={{ '--arc': `${scoreArc}deg` }}>
                    <div className="score-ring-inner">
                      <p className="score-value">{score}</p>
                      <div className="score-status">{scoreStatus}</div>
                    </div>
                  </div>
                  <p className="score-message">{scoreMessage}</p>
                  <div className="badges">
                    <span className="badge badge-success">Metabolic Tracking</span>
                    <span className="badge badge-primary">Circadian Aligned</span>
                  </div>
                </section>

                <section className="breakdown">
                  <h3>Impact Breakdown</h3>
                  {result ? (
                    result.breakdown.map((b, idx) => (
                      <div className="breakdown-item" key={idx}>
                        <div>
                          <p className="breakdown-label">{b.label}</p>
                          <p className="breakdown-detail">{b.details}</p>
                        </div>
                        <div className={`breakdown-delta ${b.delta >= 0 ? 'delta-positive' : 'delta-negative'}`}>
                          {b.delta >= 0 ? '+' : ''}
                          {b.delta.toFixed(1)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="helper">Run the model to see contribution breakdown from the backend simulation.</p>
                  )}
                </section>
              </div>
            </div>
          </div>
        </main>
      </div>

      <nav className="mobile-bottom-nav">
        <Link to="/simulator" className="active">
          <span className="material-symbols-outlined">analytics</span>
          Simulator
        </Link>
        <Link to="/history">
          <span className="material-symbols-outlined">history</span>
          History
        </Link>
        <Link to="/science">
          <span className="material-symbols-outlined">science</span>
          Science
        </Link>
      </nav>
    </div>
  )
}
