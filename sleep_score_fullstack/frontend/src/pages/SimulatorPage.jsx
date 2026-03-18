import { useMemo, useState } from 'react'
import { predictSleep } from '../lib/api'

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

export default function SimulatorPage() {
  const [state, setState] = useState({
    baseline_sleep_score: 75,
    weekend: false,

    caffeine_cups: 1,
    alcohol_drinks: 0,

    morning_light_lux: 200,
    evening_light_lux: 30,
    night_light_minutes: 0,

    hours_wake_to_first_eat: 1,
    hours_last_eat_to_bed: 3,
    eating_window_hours: 12,
  })

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const payload = useMemo(() => state, [state])

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
          <Field label="Caffeine (cups/day)" hint="Used by the traders model + diary latency model.">
            <Slider min={0} max={8} step={0.5} value={state.caffeine_cups} onChange={(v) => setState(s => ({ ...s, caffeine_cups: v }))} />
          </Field>
          <Field label="Alcohol (drinks/night)" hint="Used by the traders model + diary latency model.">
            <Slider min={0} max={10} step={0.5} value={state.alcohol_drinks} onChange={(v) => setState(s => ({ ...s, alcohol_drinks: v }))} />
          </Field>
        </div>

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
                <li>Backend trains simple linear regressions on the two CSV datasets.</li>
                <li>Light + chrononutrition are rule-based adjustments (starter).</li>
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
