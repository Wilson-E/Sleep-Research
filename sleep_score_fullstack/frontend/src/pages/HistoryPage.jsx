import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { logNight, postObserved, getLog, getLogStats } from '../lib/api.js'
import './HistoryPage.css'

const USER_ID_KEY = 'vitalityCoreUserId'

const LIKERT_LABELS = {
  quality: [
    '1. terrible',
    '2. poor',
    '3. average',
    '4. good',
    '5. excellent',
  ],
  alertness: [
    '1. exhausted',
    '2. groggy',
    '3. okay',
    '4. alert',
    '5. refreshed',
  ],
  latency: [
    '1. over an hour',
    '2. 30 to 60 min',
    '3. 15 to 30 min',
    '4. 5 to 15 min',
    '5. under 5 min',
  ],
  duration: [
    '1. under 5 hours',
    '2. 5 to 6 hours',
    '3. 6 to 7 hours',
    '4. 7 to 8 hours',
    '5. over 8 hours',
  ],
}

function latencyLikertToMinutes(v) {
  return [75, 45, 22, 10, 3][Number(v) - 1] ?? 22
}

function durationLikertToHours(v) {
  return [4.5, 5.5, 6.5, 7.5, 8.5][Number(v) - 1] ?? 7.0
}

function todayISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const DEFAULT_EVENING = {
  caffeine_cups: 2,
  caffeine_sensitivity: 1.0,
  alcohol_drinks: 0,
  alcohol_last_drink_time: '',
  weekend: false,
  bedtime_hours: 23,
  morning_light_lux: 200,
  evening_light_lux: 30,
  night_light_minutes: 0,
  hours_wake_to_first_eat: 1,
  hours_last_eat_to_bed: 3,
  eating_window_hours: 12,
  screen_time_before_bed_minutes: 0,
  rmssd_ms: '',
  resting_hr_bpm: '',
}

const DEFAULT_OUTCOMES = {
  quality: 3,
  alertness: 3,
  latency: 3,
  duration: 3,
  awakenings: 0,
}

export default function HistoryPage() {
  const [userId, setUserId] = useState(() => {
    return localStorage.getItem(USER_ID_KEY) || 'default_user'
  })
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState(null)
  const [evening, setEvening] = useState(DEFAULT_EVENING)
  const [outcomes, setOutcomes] = useState(DEFAULT_OUTCOMES)
  const [date, setDate] = useState(todayISO())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  useEffect(() => {
    localStorage.setItem(USER_ID_KEY, userId)
    refresh(userId)
  }, [userId])

  async function refresh(uid) {
    try {
      const [log, s] = await Promise.all([getLog(uid), getLogStats(uid)])
      setEntries((log.entries || []).slice().reverse())
      setStats(s)
    } catch (err) {
      setError(err.message || 'Failed to fetch history')
    }
  }

  function updateEvening(field, value) {
    setEvening((prev) => ({ ...prev, [field]: value }))
  }

  function updateOutcomes(field, value) {
    setOutcomes((prev) => ({ ...prev, [field]: value }))
  }

  function buildPredictRequest() {
    const payload = {
      caffeine_cups: Number(evening.caffeine_cups) || 0,
      caffeine_sensitivity: Number(evening.caffeine_sensitivity) || 1.0,
      alcohol_drinks: Number(evening.alcohol_drinks) || 0,
      weekend: Boolean(evening.weekend),
      morning_light_lux: Number(evening.morning_light_lux) || 0,
      evening_light_lux: Number(evening.evening_light_lux) || 0,
      night_light_minutes: Number(evening.night_light_minutes) || 0,
      hours_wake_to_first_eat: Number(evening.hours_wake_to_first_eat) || 0,
      hours_last_eat_to_bed: Number(evening.hours_last_eat_to_bed) || 0,
      eating_window_hours: Number(evening.eating_window_hours) || 0,
      screen_time_before_bed_minutes: Number(evening.screen_time_before_bed_minutes) || 0,
      user_id: userId,
    }
    if (evening.bedtime_hours !== '' && evening.bedtime_hours !== null) {
      payload.bedtime_hours = Number(evening.bedtime_hours)
    }
    if (evening.alcohol_last_drink_time !== '') {
      payload.alcohol_last_drink_time = Number(evening.alcohol_last_drink_time)
    }
    if (evening.rmssd_ms !== '') {
      payload.rmssd_ms = Number(evening.rmssd_ms)
    }
    if (evening.resting_hr_bpm !== '') {
      payload.resting_hr_bpm = Number(evening.resting_hr_bpm)
    }
    return payload
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!userId.trim()) {
      setError('User ID cannot be empty.')
      return
    }
    setLoading(true)
    setError('')
    setSuccessMsg('')
    try {
      await logNight({
        user_id: userId,
        date,
        predict_request: buildPredictRequest(),
      })
      const observedPayload = {
        observed_sleep_quality_subjective: Number(outcomes.quality),
        observed_morning_alertness: Number(outcomes.alertness),
        observed_sleep_onset_latency_minutes: latencyLikertToMinutes(outcomes.latency),
        observed_sleep_duration_hours: durationLikertToHours(outcomes.duration),
        observed_awakenings: Number(outcomes.awakenings) || 0,
      }
      const result = await postObserved({
        user_id: userId,
        date,
        observed: observedPayload,
      })
      setSuccessMsg(
        `Saved night ${date}. Predicted ${result.predicted_score.toFixed(1)}, observed ${
          result.observed_score != null ? result.observed_score.toFixed(1) : 'n/a'
        }.`,
      )
      await refresh(userId)
    } catch (err) {
      setError(err.message || 'Failed to save night.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="history-page">
      <header className="history-header">
        <div className="history-brand">
          <Link to="/" className="history-back">Vitality Core</Link>
          <nav className="history-nav">
            <Link to="/simulator">Simulator</Link>
            <Link to="/science">Science</Link>
            <Link to="/history" className="active">History</Link>
          </nav>
        </div>
        <div className="history-user">
          <label htmlFor="user-id">User ID</label>
          <input
            id="user-id"
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value.trim() || 'default_user')}
            placeholder="default_user"
          />
        </div>
      </header>

      <main className="history-main">
        <section className="history-intro">
          <h1>Sleep History and Personalization</h1>
          <p>
            Log completed nights with the behavioral inputs from yesterday and a short rating of how
            you slept. After five to ten nights, the Bayesian updater begins to personalize the
            pathway coefficients for this user ID. Entries are stored in
            {' '}<code>backend/data/logs/{userId}.json</code> on this machine; nothing is uploaded.
          </p>
        </section>

        {stats && (
          <section className="history-stats">
            <StatCard label="Nights logged" value={stats.total_nights} />
            <StatCard
              label="Avg predicted"
              value={stats.avg_predicted_score != null ? stats.avg_predicted_score.toFixed(1) : 'n/a'}
            />
            <StatCard
              label="Avg observed"
              value={stats.avg_observed_score != null ? stats.avg_observed_score.toFixed(1) : 'n/a'}
            />
            <StatCard
              label="Avg residual"
              value={stats.avg_residual != null ? stats.avg_residual.toFixed(1) : 'n/a'}
              hint="predicted minus observed"
            />
          </section>
        )}

        <form className="history-form" onSubmit={handleSubmit}>
          <div className="history-form-head">
            <h2>Log a completed night</h2>
            <div className="history-date">
              <label htmlFor="entry-date">Night date</label>
              <input
                id="entry-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>

          <fieldset className="history-fieldset">
            <legend>Evening inputs (what happened yesterday)</legend>

            <div className="history-grid">
              <NumField label="Caffeine cups" value={evening.caffeine_cups}
                onChange={(v) => updateEvening('caffeine_cups', v)} min={0} max={20} step={0.25} />
              <SelectField
                label="Caffeine sensitivity"
                value={evening.caffeine_sensitivity}
                onChange={(v) => updateEvening('caffeine_sensitivity', v)}
                options={[
                  { value: 0.7, label: 'Adjusted (0.70x)' },
                  { value: 1.0, label: 'Average (1.00x)' },
                  { value: 1.5, label: 'Sensitive (1.50x)' },
                ]}
              />
              <NumField label="Alcohol drinks" value={evening.alcohol_drinks}
                onChange={(v) => updateEvening('alcohol_drinks', v)} min={0} max={30} step={0.5} />
              <NumField label="Last drink time (hour, blank if none)"
                value={evening.alcohol_last_drink_time}
                onChange={(v) => updateEvening('alcohol_last_drink_time', v)}
                min={0} max={24} step={0.5} allowBlank />
              <CheckboxField label="Weekend night"
                checked={evening.weekend}
                onChange={(v) => updateEvening('weekend', v)} />
              <NumField label="Bedtime (hour of day, blank for auto)"
                value={evening.bedtime_hours}
                onChange={(v) => updateEvening('bedtime_hours', v)}
                min={0} max={24} step={0.5} allowBlank />

              <NumField label="Morning light (lux)" value={evening.morning_light_lux}
                onChange={(v) => updateEvening('morning_light_lux', v)} min={0} max={20000} step={50} />
              <NumField label="Evening light (lux)" value={evening.evening_light_lux}
                onChange={(v) => updateEvening('evening_light_lux', v)} min={0} max={20000} step={5} />
              <NumField label="Night light minutes" value={evening.night_light_minutes}
                onChange={(v) => updateEvening('night_light_minutes', v)} min={0} max={480} step={5} />

              <NumField label="Hours wake to first meal" value={evening.hours_wake_to_first_eat}
                onChange={(v) => updateEvening('hours_wake_to_first_eat', v)} min={0} max={12} step={0.25} />
              <NumField label="Hours last meal to bed" value={evening.hours_last_eat_to_bed}
                onChange={(v) => updateEvening('hours_last_eat_to_bed', v)} min={0} max={12} step={0.25} />
              <NumField label="Eating window (hours)" value={evening.eating_window_hours}
                onChange={(v) => updateEvening('eating_window_hours', v)} min={0} max={24} step={0.5} />
              <NumField label="Screen time before bed (min)"
                value={evening.screen_time_before_bed_minutes}
                onChange={(v) => updateEvening('screen_time_before_bed_minutes', v)} min={0} max={480} step={5} />

              <NumField label="RMSSD ms (optional)" value={evening.rmssd_ms}
                onChange={(v) => updateEvening('rmssd_ms', v)} min={0} max={300} step={1} allowBlank />
              <NumField label="Resting HR bpm (optional)" value={evening.resting_hr_bpm}
                onChange={(v) => updateEvening('resting_hr_bpm', v)} min={0} max={200} step={1} allowBlank />
            </div>
          </fieldset>

          <fieldset className="history-fieldset">
            <legend>Morning outcomes (how you slept, 1 to 5)</legend>
            <div className="history-likerts">
              <LikertField label="Overall sleep quality" value={outcomes.quality}
                onChange={(v) => updateOutcomes('quality', v)} labels={LIKERT_LABELS.quality} />
              <LikertField label="Morning alertness" value={outcomes.alertness}
                onChange={(v) => updateOutcomes('alertness', v)} labels={LIKERT_LABELS.alertness} />
              <LikertField label="Time to fall asleep" value={outcomes.latency}
                onChange={(v) => updateOutcomes('latency', v)} labels={LIKERT_LABELS.latency} />
              <LikertField label="Total hours slept" value={outcomes.duration}
                onChange={(v) => updateOutcomes('duration', v)} labels={LIKERT_LABELS.duration} />
              <NumField label="Number of awakenings"
                value={outcomes.awakenings}
                onChange={(v) => updateOutcomes('awakenings', v)} min={0} max={30} step={1} />
            </div>
          </fieldset>

          {error && <div className="history-error">{error}</div>}
          {successMsg && <div className="history-success">{successMsg}</div>}

          <div className="history-actions">
            <button type="submit" className="history-submit" disabled={loading}>
              {loading ? 'Saving...' : 'Save this night'}
            </button>
          </div>
        </form>

        <section className="history-entries">
          <h2>Past nights</h2>
          {entries.length === 0 ? (
            <p className="history-empty">No nights logged yet for user ID "{userId}".</p>
          ) : (
            <table className="history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Predicted</th>
                  <th>Observed</th>
                  <th>Delta</th>
                  <th>Duration (h)</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => {
                  const delta = (e.predicted_score != null && e.observed_score != null)
                    ? (e.predicted_score - e.observed_score).toFixed(1)
                    : 'n/a'
                  return (
                    <tr key={e.date + e.timestamp}>
                      <td>{e.date}</td>
                      <td>{e.predicted_score != null ? e.predicted_score.toFixed(1) : 'n/a'}</td>
                      <td>{e.observed_score != null ? e.observed_score.toFixed(1) : 'n/a'}</td>
                      <td>{delta}</td>
                      <td>{e.observed_sleep_duration_hours != null ? e.observed_sleep_duration_hours.toFixed(1) : 'n/a'}</td>
                      <td>{e.observed_sleep_quality_subjective ?? 'n/a'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  )
}

function StatCard({ label, value, hint }) {
  return (
    <div className="history-stat-card">
      <div className="history-stat-label">{label}</div>
      <div className="history-stat-value">{value}</div>
      {hint && <div className="history-stat-hint">{hint}</div>}
    </div>
  )
}

function NumField({ label, value, onChange, min, max, step, allowBlank }) {
  return (
    <label className="history-field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const v = e.target.value
          if (allowBlank && v === '') {
            onChange('')
          } else {
            onChange(v)
          }
        }}
      />
    </label>
  )
}

function CheckboxField({ label, checked, onChange }) {
  return (
    <label className="history-field history-check">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  )
}

function SelectField({ label, value, onChange, options }) {
  return (
    <label className="history-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </label>
  )
}

function LikertField({ label, value, onChange, labels }) {
  return (
    <div className="history-likert">
      <div className="history-likert-head">
        <span className="history-likert-label">{label}</span>
        <span className="history-likert-current">{labels[Number(value) - 1]}</span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="history-likert-ticks">
        <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
      </div>
    </div>
  )
}
