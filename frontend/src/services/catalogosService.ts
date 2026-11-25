import axios from 'axios'
import { api } from './api'
import type { MaterialAdmin, ServicioAdmin } from '../types'

// * ABM de servicios y materiales (solo administradores). Contrato de
// * backend/app/api/catalogos.py. La baja es lógica: PATCH con activo: false.

// GET /servicios?incluir_inactivos=true: todos, con externo y estado (solo administradores)
export async function listarServiciosAdmin(): Promise<ServicioAdmin[]> {
  const { data } = await api.get<ServicioAdmin[]>('/servicios', {
    params: { incluir_inactivos: true },
  })
  return data
}

// POST /servicios. Sin externo ni dias_aireacion, el back usa false y 3.
export async function crearServicio(datos: {
  nombre: string
  externo: boolean
  dias_aireacion: number
}): Promise<ServicioAdmin> {
  const { data } = await api.post<ServicioAdmin>('/servicios', datos)
  return data
}

// PATCH /servicios/{id}: modificación, baja (activo: false) y reactivación (activo: true)
export async function modificarServicio(
  id: number,
  cambios: Partial<Pick<ServicioAdmin, 'nombre' | 'externo' | 'dias_aireacion' | 'activo'>>,
): Promise<ServicioAdmin> {
  const { data } = await api.patch<ServicioAdmin>(`/servicios/${id}`, cambios)
  return data
}

// GET /materiales?incluir_inactivos=true: todos, con estado (solo administradores)
export async function listarMaterialesAdmin(): Promise<MaterialAdmin[]> {
  const { data } = await api.get<MaterialAdmin[]>('/materiales', {
    params: { incluir_inactivos: true },
  })
  return data
}

// POST /materiales. El back guarda el código en mayúsculas y sin espacios.
export async function crearMaterial(datos: {
  nombre: string
  codigo: string | null
  nombre_alternativo: string | null
}): Promise<MaterialAdmin> {
  const { data } = await api.post<MaterialAdmin>('/materiales', datos)
  return data
}

// PATCH /materiales/{id}: codigo y nombre_alternativo se borran mandando null
export async function modificarMaterial(
  id: number,
  cambios: Partial<Pick<MaterialAdmin, 'nombre' | 'codigo' | 'nombre_alternativo' | 'activo'>>,
): Promise<MaterialAdmin> {
  const { data } = await api.patch<MaterialAdmin>(`/materiales/${id}`, cambios)
  return data
}

// Convierte el error del back en un texto para mostrar en pantalla.
// Reglas (409 repetido, 404 inexistente, 403 sin permiso) llegan como texto; las
// validaciones (422), como lista de pydantic: se muestra el primer mensaje sin su prefijo.
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'No se pudo conectar con el servidor.'
    const detalle = error.response.data?.detail
    if (typeof detalle === 'string') return detalle
    if (Array.isArray(detalle) && typeof detalle[0]?.msg === 'string') {
      return detalle[0].msg.replace(/^Value error, /, '')
    }
    if (error.response.status === 403) return 'No tenés permiso para hacer esto.'
  }
  return 'Ocurrió un error inesperado.'
}
