import { createContext } from 'react'
import type { Usuario } from '../types'

export interface ContextoAuth {
  usuario: Usuario | null
  cargando: boolean // true mientras se comprueba si el token guardado sirve
  iniciarSesion: (numero: string, contrasena: string) => Promise<Usuario>
  salir: () => void
}

export const AuthContext = createContext<ContextoAuth | null>(null)