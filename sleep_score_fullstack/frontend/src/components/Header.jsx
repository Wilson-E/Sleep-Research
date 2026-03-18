export default function Header() {
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '16px' }}>
      <div style={{ maxWidth: 980, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Sleep Score Simulator</div>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Light + Chrononutrition + Caffeine/Alcohol</div>
        </div>
        <a href="/simulator" style={{ color: '#9bb5ff', textDecoration: 'none', fontWeight: 600 }}>Simulator</a>
      </div>
    </div>
  )
}
