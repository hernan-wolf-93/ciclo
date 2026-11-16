import { useEffect, useState, type ReactNode } from 'react'
import { cerrarSesion, login, obtenerYo } from '../services/authService'
import { leerToken } from '../services/api'
import type { Usuario } from '../types'
import { AuthContext } from './contexto'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(() => leerToken() !== null)

  // Al abrir la app: si hay token guardado, comprobamos que siga valiendo
  useEffect(() => {
    if (leerToken() === null) return
    obtenerYo()
      .then(setUsuario)
      .catch(() => setUsuario(null)) // el interceptor ya borra el token si dio 401
      .finally(() => setCargando(false))
  }, [])

  async function iniciarSesion(numero: string, contrasena: string) {
    const yo = await login(numero, contrasena)
    setUsuario(yo)
    return yo
  }

  function salir() {
    cerrarSesion()
    setUsuario(null)
  }

  return (
    <AuthContext.Provider value={{ usuario, cargando, iniciarSesion, salir }}>
      {children}
    </AuthContext.Provider>
  )
}