import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import SimulatorPage from './pages/SimulatorPage.jsx'
import SciencePage from './pages/SciencePage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/simulator" element={<SimulatorPage />} />
        <Route path="/science" element={<SciencePage />} />
      </Routes>
    </BrowserRouter>
  )
}
