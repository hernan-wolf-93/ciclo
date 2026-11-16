import { Navigate, Outlet } from 'react-router-dom'
import { Loader } from '@mantine/core'
import { useAuth } from './useAuth'

// Si no hay sesión, manda al login. Si hay, muestra las pantallas de adentro.
export default function RutaProtegida() {
  const { usuario, cargando } = useAuth()
  if (cargando) return <Loader m="xl" />
  if (!usuario) return <Navigate to="/login" replace />
  return <Outlet />
}