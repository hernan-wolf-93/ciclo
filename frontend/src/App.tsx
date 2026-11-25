import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import RutaProtegida from './auth/RutaProtegida'
import Login from './pages/Login'
import RecuperarContrasena from './pages/RecuperarContrasena'
import Tablero from './pages/Tablero'
import Recepcion from './pages/Recepcion'
import AvanceEtapa from './pages/AvanceEtapa'
import Esterilizacion from './pages/Esterilizacion'
import Lotes from './pages/Lotes'
import Entrega from './pages/Entrega'
import Usuarios from './pages/Usuarios'
import Catalogos from './pages/Catalogos'

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="recuperar" element={<RecuperarContrasena />} />
      <Route element={<RutaProtegida />}>
        <Route element={<AppLayout />}>
          <Route index element={<Tablero />} />
          <Route path="recepcion" element={<Recepcion />} />
          {/* key: al pasar de una a otra se arma de nuevo, sin arrastrar lo cargado */}
          <Route path="lavado" element={<AvanceEtapa key="lavado" etapa={2} />} />
          <Route path="empaque" element={<AvanceEtapa key="empaque" etapa={3} />} />
          <Route path="esterilizacion" element={<Esterilizacion />} />
          <Route path="lotes" element={<Lotes />} />
          <Route path="entrega" element={<Entrega />} />
          <Route path="catalogos" element={<Catalogos />} />
          <Route path="usuarios" element={<Usuarios />} />
        </Route>
      </Route>
    </Routes>
  )
}