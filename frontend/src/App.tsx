import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import RutaProtegida from './auth/RutaProtegida'
import Login from './pages/Login'
import Tablero from './pages/Tablero'
import Recepcion from './pages/Recepcion'
import Esterilizacion from './pages/Esterilizacion'
import Lotes from './pages/Lotes'
import Entrega from './pages/Entrega'
import Usuarios from './pages/Usuarios'

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<RutaProtegida />}>
        <Route element={<AppLayout />}>
          <Route index element={<Tablero />} />
          <Route path="recepcion" element={<Recepcion />} />
          <Route path="esterilizacion" element={<Esterilizacion />} />
          <Route path="lotes" element={<Lotes />} />
          <Route path="entrega" element={<Entrega />} />
          <Route path="usuarios" element={<Usuarios />} />
        </Route>
      </Route>
    </Routes>
  )
}