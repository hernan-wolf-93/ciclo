import axios from 'axios'
import { api } from './api'
import type { AvanceRegistrado, EtapaAvance, Material, Metodo, NuevoAvance, Pendiente } from '../types'

// GET /materiales: catálogo de materiales activos. La pantalla de avance lo usa solo
// para mostrar el código al lado del nombre (los pendientes no lo traen).
export async function obtenerMateriales(): Promise<Material[]> {
  const { data } = await api.get<Material[]>('/materiales')
  return data
}

// GET /avances/pendientes?etapa_orden={etapa}: unidades que esperan pasar a la etapa,
// por servicio de origen y material (incluye materiales dados de baja con ítems en curso).
export async function obtenerPendientes(etapa: EtapaAvance): Promise<Pendiente[]> {
  const { data } = await api.get<Pendiente[]>('/avances/pendientes', {
    params: { etapa_orden: etapa },
  })
  return data
}

// GET /metodos: calor húmedo, calor seco y óxido de etileno
export async function obtenerMetodos(): Promise<Metodo[]> {
  const { data } = await api.get<Metodo[]>('/metodos')
  return data
}

// POST /avances: el operador que firma sale del token (no va en el cuerpo).
// En Empaque cada línea lleva su metodo_id; en Lavado, ninguna.
export async function registrarAvance(datos: NuevoAvance): Promise<AvanceRegistrado> {
  const { data } = await api.post<AvanceRegistrado>('/avances', datos)
  return data
}

// Convierte el error de la API en un texto para mostrar en pantalla.
// Las reglas de negocio llegan como texto ("solo hay 2 esperando…"); las validaciones del
// esquema, como una lista de pydantic: se muestra el primer mensaje sin su prefijo.
export function mensajeDeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'No se pudo conectar con el servidor.'
    const detalle = error.response.data?.detail
    if (typeof detalle === 'string') return detalle
    if (Array.isArray(detalle) && typeof detalle[0]?.msg === 'string') {
      return detalle[0].msg.replace(/^Value error, /, '')
    }
  }
  return 'No se pudo registrar el avance. Probá de nuevo.'
}
