import { api, borrarToken, guardarToken } from './api'
import type { Usuario } from '../types'

// POST /auth/login: devuelve el token. Lo guardamos y pedimos quién es el operador.
export async function login(numero_operador: string, contrasena: string): Promise<Usuario> {
  const { data } = await api.post<{ access_token: string }>('/auth/login', {
    numero_operador,
    contrasena,
  })
  guardarToken(data.access_token)
  return obtenerYo()
}

// GET /auth/me: el operador del token (con su rol)
export async function obtenerYo(): Promise<Usuario> {
  const { data } = await api.get<Usuario>('/auth/me')
  return data
}

// POST /auth/recuperar-contrasena: pública. Cambia la clave con el código que dio un
// administrador. Responde 204 sin cuerpo; si el código no sirve, 400 (no 401, así el
// interceptor de api.ts no cierra la sesión).
export async function recuperarContrasena(
  numero_operador: string,
  codigo: string,
  contrasena_nueva: string,
): Promise<void> {
  await api.post('/auth/recuperar-contrasena', { numero_operador, codigo, contrasena_nueva })
}

export function cerrarSesion() {
  borrarToken()
}