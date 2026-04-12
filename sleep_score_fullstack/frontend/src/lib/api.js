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
