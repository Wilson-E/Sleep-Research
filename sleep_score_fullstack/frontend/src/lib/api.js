export async function predictSleep(payload) {
  const res = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Request failed')
  }
  return res.json()
}

export async function getModelMetrics() {
  const res = await fetch('/api/model/metrics')
  if (!res.ok) throw new Error('Failed to fetch model metrics')
  return res.json()
}

export async function getModelComparison() {
  const res = await fetch('/api/model/comparison')
  if (!res.ok) throw new Error('Failed to fetch model comparison')
  return res.json()
}

export async function logNight({ user_id, date, predict_request }) {
  const res = await fetch('/api/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, date, predict_request }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to log night')
  }
  return res.json()
}

export async function postObserved({ user_id, date, observed }) {
  const res = await fetch(`/api/log/${encodeURIComponent(date)}/observed`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, ...observed }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to post observed outcomes')
  }
  return res.json()
}

export async function getLog(user_id) {
  const res = await fetch(`/api/log?user_id=${encodeURIComponent(user_id)}`)
  if (!res.ok) throw new Error('Failed to fetch log entries')
  return res.json()
}

export async function getLogStats(user_id) {
  const res = await fetch(`/api/log/stats?user_id=${encodeURIComponent(user_id)}`)
  if (!res.ok) throw new Error('Failed to fetch log stats')
  return res.json()
}
