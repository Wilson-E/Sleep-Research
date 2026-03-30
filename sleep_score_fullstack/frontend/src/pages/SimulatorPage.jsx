import { useMemo, useState } from 'react'
import { predictSleep } from '../lib/api'

const MG_PER_CUP = 95

function Field({ label, children, hint }) {
  return (
    <div style={{ padding: 12, border: '1px solid rgba(255,255,255,0.08)', borderRadius: 12, background: 'rgba(255,255,255,0.03)' }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>{label}</div>
      <div>{children}</div>
      {hint ? <div style={{ marginTop: 6, fontSize: 12, opacity: 0.75 }}>{hint}</div> : null}
    </div>
  )
}

function Slider({ value, onChange, min, max, step = 1 }) {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: '100%' }}
      />
      <div style={{ width: 70, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
    </div>
  )
}

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

export default function SimulatorPage() {
  const [state, setState] = useState({
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

    // Recovery (optional)
    rmssd_ms: null,
    resting_hr_bpm: null,
  })

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

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 16 }}>
      <div style={{ display: 'grid', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <div style={{ fontSize: 22, fontWeight: 800 }}>What-if Sleep Score</div>
            <div style={{ opacity: 0.8, fontSize: 13 }}>Adjust inputs → run model → see score + contribution breakdown</div>
          </div>
          <button
            onClick={onRun}
            disabled={loading}
            style={{
              background: loading ? '#2a3554' : '#3b5bff',
              color: 'white',
              border: 'none',
              borderRadius: 12,
              padding: '10px 14px',
              fontWeight: 800,
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Running…' : 'Run Prediction'}
          </button>
        </div>

        <Field label="Baseline Sleep Score" hint="Your starting point before factor adjustments (0–100).">
          <Slider min={0} max={100} step={1} value={state.baseline_sleep_score} onChange={(v) => setState(s => ({ ...s, baseline_sleep_score: v }))} />
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Caffeine doses" hint="Set each caffeine dose with an intake time so half-life decay is personalized.">
            <div style={{ display: 'grid', gap: 8 }}>
              {state.caffeine_doses.map((dose, idx) => (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 8, alignItems: 'center' }}>
                  <input
                    type="time"
                    value={dose.time}
                    onChange={(e) => setState((s) => ({
                      ...s,
                      caffeine_doses: s.caffeine_doses.map((d, i) => (i === idx ? { ...d, time: e.target.value } : d)),
                    }))}
                    style={{ width: '100%', padding: 10, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.2)', color: 'white' }}
                  />
                  <input
                    type="number"
                    min={0}
                    max={1000}
                    step={5}
                    value={dose.dose_mg}
                    onChange={(e) => setState((s) => ({
                      ...s,
                      caffeine_doses: s.caffeine_doses.map((d, i) => (i === idx ? { ...d, dose_mg: Number(e.target.value) } : d)),
                    }))}
                    style={{ width: '100%', padding: 10, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.2)', color: 'white' }}
                  />
                  <button
                    onClick={() => setState((s) => ({
                      ...s,
                      caffeine_doses: s.caffeine_doses.length > 1 ? s.caffeine_doses.filter((_, i) => i !== idx) : s.caffeine_doses,
                    }))}
                    disabled={state.caffeine_doses.length <= 1}
                    style={{
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: 10,
                      background: 'rgba(255,255,255,0.05)',
                      color: 'white',
                      padding: '8px 10px',
                      cursor: state.caffeine_doses.length <= 1 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Remove
                  </button>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <button
                  onClick={() => setState((s) => ({
                    ...s,
                    caffeine_doses: [...s.caffeine_doses, { time: '13:00', dose_mg: 95 }],
                  }))}
                  style={{
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: 10,
                    background: 'rgba(255,255,255,0.05)',
                    color: 'white',
                    padding: '8px 10px',
                    cursor: 'pointer',
                    fontWeight: 700,
                  }}
                >
                  Add Dose
                </button>
                <div style={{ fontSize: 12, opacity: 0.85 }}>
                  Total: {(payload.caffeine_cups || 0).toFixed(2)} cups ({Math.round((payload.caffeine_cups || 0) * MG_PER_CUP)} mg)
                </div>
              </div>
            </div>
          </Field>
          <Field label="Alcohol (drinks/night)" hint="Used by the traders model + diary latency model.">
            <Slider min={0} max={10} step={0.5} value={state.alcohol_drinks} onChange={(v) => setState(s => ({ ...s, alcohol_drinks: v }))} />
          </Field>
        </div>

        <Field label="Caffeine Sensitivity" hint="Personalize caffeine impact. < 1.0 means caffeine-adjusted, > 1.0 means caffeine-sensitive.">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            {SENSITIVITY_PRESETS.map((preset) => {
              const isActive = Math.abs(state.caffeine_sensitivity - preset.multiplier) < 0.001
              return (
                <button
                  key={preset.key}
                  onClick={() => setState((s) => ({ ...s, caffeine_sensitivity: preset.multiplier }))}
                  style={{
                    border: isActive ? '1px solid rgba(110,231,183,0.8)' : '1px solid rgba(255,255,255,0.2)',
                    borderRadius: 10,
                    background: isActive ? 'rgba(110,231,183,0.15)' : 'rgba(255,255,255,0.05)',
                    color: 'white',
                    padding: '8px 10px',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: 12 }}>{preset.label}</div>
                  <div style={{ fontSize: 11, opacity: 0.8 }}>{preset.multiplier.toFixed(2)}x</div>
                </button>
              )
            })}
          </div>
          <div style={{ marginTop: 6, fontSize: 12, opacity: 0.85 }}>
            {sensitivityLabel(state.caffeine_sensitivity)} ({state.caffeine_sensitivity.toFixed(2)}x caffeine penalty)
          </div>
        </Field>

        <Field label="Bedtime (optional)" hint="Used directly by caffeine half-life residual calculations. Leave blank to derive bedtime from meal timing fields.">
          <input
            type="time"
            value={state.bedtime_time}
            onChange={(e) => setState((s) => ({ ...s, bedtime_time: e.target.value }))}
            style={{ width: '100%', padding: 10, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.2)', color: 'white' }}
          />
        </Field>

        <Field label="Weekend?" hint="Matches the traders dataset weekend effect.">
          <label style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input
              type="checkbox"
              checked={state.weekend}
              onChange={(e) => setState(s => ({ ...s, weekend: e.target.checked }))}
            />
            Weekend
          </label>
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Recovery: RMSSD (ms)" hint="Optional. Higher RMSSD usually = better recovery.">
            <input type="number" value={state.rmssd_ms ?? ''} placeholder="e.g., 45" onChange={(e) => setState(s => ({ ...s, rmssd_ms: e.target.value === '' ? null : Number(e.target.value) }))} style={{ width: '100%', padding: 10, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.2)', color: 'white' }} />
          </Field>
          <Field label="Recovery: Resting HR (bpm)" hint="Optional. Lower resting HR usually = better recovery.">
            <input type="number" value={state.resting_hr_bpm ?? ''} placeholder="e.g., 60" onChange={(e) => setState(s => ({ ...s, resting_hr_bpm: e.target.value === '' ? null : Number(e.target.value) }))} style={{ width: '100%', padding: 10, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(0,0,0,0.2)', color: 'white' }} />
          </Field>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="Morning light (lux)" hint="Proxy for circadian-effective light after waking. Target ~250+ lux.">
            <Slider min={0} max={2000} step={10} value={state.morning_light_lux} onChange={(v) => setState(s => ({ ...s, morning_light_lux: v }))} />
          </Field>
          <Field label="Evening light (lux)" hint="Proxy for light in the last ~30 min before bed. Higher → worse latency.">
            <Slider min={0} max={1000} step={10} value={state.evening_light_lux} onChange={(v) => setState(s => ({ ...s, evening_light_lux: v }))} />
          </Field>
        </div>

        <Field label="Night light (minutes)" hint="Minutes of light during sleep (e.g., phone checks, hallway light).">
          <Slider min={0} max={180} step={5} value={state.night_light_minutes} onChange={(v) => setState(s => ({ ...s, night_light_minutes: v }))} />
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <Field label="Wake → 1st eating (h)">
            <Slider min={0} max={8} step={0.5} value={state.hours_wake_to_first_eat} onChange={(v) => setState(s => ({ ...s, hours_wake_to_first_eat: v }))} />
          </Field>
          <Field label="Last eating → bed (h)">
            <Slider min={0} max={8} step={0.5} value={state.hours_last_eat_to_bed} onChange={(v) => setState(s => ({ ...s, hours_last_eat_to_bed: v }))} />
          </Field>
          <Field label="Eating window (h)">
            <Slider min={4} max={18} step={0.5} value={state.eating_window_hours} onChange={(v) => setState(s => ({ ...s, eating_window_hours: v }))} />
          </Field>
        </div>

        {error ? (
          <div style={{ padding: 12, borderRadius: 12, background: 'rgba(255,0,0,0.12)', border: '1px solid rgba(255,0,0,0.25)' }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Error</div>
            <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{error}</div>
          </div>
        ) : null}
      </div>

      <div style={{ position: 'sticky', top: 16, alignSelf: 'start' }}>
        <div style={{ padding: 14, borderRadius: 16, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
          <div style={{ fontSize: 14, opacity: 0.8 }}>Estimated Sleep Score</div>
          <div style={{ fontSize: 56, fontWeight: 900, lineHeight: 1, marginTop: 6 }}>
            {result ? Math.round(result.sleep_score) : '—'}
          </div>
          <div style={{ marginTop: 10, fontSize: 12, opacity: 0.8 }}>
            0 = terrible, 100 = excellent (starter calibration)
          </div>

          <div style={{ marginTop: 14 }}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>Breakdown</div>
            {result ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {result.breakdown.map((b, idx) => (
                  <div key={idx} style={{ padding: 10, borderRadius: 12, background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <div style={{ fontWeight: 800, fontSize: 13 }}>{b.label}</div>
                      <div style={{ fontWeight: 900, color: b.delta >= 0 ? '#6ee7b7' : '#fca5a5' }}>
                        {b.delta >= 0 ? '+' : ''}{b.delta.toFixed(1)}
                      </div>
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>{b.details}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 13, opacity: 0.7 }}>Run a prediction to see contributions.</div>
            )}
          </div>

          {result ? (
            <div style={{ marginTop: 14, fontSize: 12, opacity: 0.85 }}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Model notes</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                <li>Backend uses a pathway-based simulation engine with study-based coefficients.</li>
                <li>Components are Duration, Quality, Timing, and Alertness.</li>
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
