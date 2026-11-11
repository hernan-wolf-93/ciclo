import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import Tablero from './pages/Tablero'
import Recepcion from './pages/Recepcion'
import Esterilizacion from './pages/Esterilizacion'
import Lotes from './pages/Lotes'
import Entrega from './pages/Entrega'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Tablero />} />
        <Route path="recepcion" element={<Recepcion />} />
        <Route path="esterilizacion" element={<Esterilizacion />} />
        <Route path="lotes" element={<Lotes />} />
        <Route path="entrega" element={<Entrega />} />
      </Route>
    </Routes>
  )
}
