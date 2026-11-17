import axios from 'axios'
import { api } from './api'
import type { Rol, UsuarioAdmin } from '../types'

// GET /operadores: sin filtro trae todos; con true solo activos, con false solo dados de baja
export async function listarUsuarios(activo?: boolean): Promise<UsuarioAdmin[]> {
  const { data } = await api.get<UsuarioAdmin[]>('/operadores', {
    params: activo === undefined ? {} : { activo },
  })
  return data
}

// GET /roles: los roles que el usuario logueado puede asignar al dar de alta
export async function listarRoles(): Promise<Rol[]> {
  const { data } = await api.get<Rol[]>('/roles')
  return data
}

// POST /operadores
export async function crearUsuario(datos: {
  numero_operador: string
  contrasena: string
  rol_id: number
}): Promise<UsuarioAdmin> {
  const { data } = await api.post<UsuarioAdmin>('/operadores', datos)
  return data
}

// PATCH /operadores/{id}: cambia el rol o la baja lógica (activo: false). El N.º no se modifica.
export async function modificarUsuario(
  id: number,
  cambios: { rol_id?: number; activo?: boolean },
): Promise<UsuarioAdmin> {
  const { data } = await api.patch<UsuarioAdmin>(`/operadores/${id}`, cambios)
  return data
}

// Convierte el error del back en un texto para mostrar en pantalla
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'No se pudo conectar con el servidor.'
    const { status, data } = error.response
    if (typeof data?.detail === 'string') return data.detail // 403, 404, 409 y 422 de reglas
    if (status === 422)
      return 'Revisá los datos: el N.º de operador no puede tener espacios y la contraseña debe tener entre 8 y 128 caracteres.'
    if (status === 403) return 'No tenés permiso para hacer esto.'
  }
  return 'Ocurrió un error inesperado.'
}