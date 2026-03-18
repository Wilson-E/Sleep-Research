import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header.jsx'
import SimulatorPage from './pages/SimulatorPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#0b1220', color: '#e8eefc' }}>
        <Header />
        <div style={{ maxWidth: 980, margin: '0 auto', padding: '24px 16px' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/simulator" replace />} />
            <Route path="/simulator" element={<SimulatorPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
