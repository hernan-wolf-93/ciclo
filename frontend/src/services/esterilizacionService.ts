import axios from 'axios'
import { api } from './api'
import type {
  BowieDickHoy,
  BowieDickRegistrado,
  CierreLote,
  EquipoDeCarga,
  LoteCerrado,
  LoteCreado,
  LoteResumen,
  NuevoBowieDick,
  NuevoLote,
  PendienteCarga,
  Programa,
} from '../types'

// * Pantalla de Esterilización: backend/app/api/esterilizacion.py, bowie_dick.py,
// * catalogos.py y lotes.py. El operador que firma sale del token (no va en el cuerpo).

// GET /equipos: equipos activos, con el nombre de su método
export async function obtenerEquipos(): Promise<EquipoDeCarga[]> {
  const { data } = await api.get<EquipoDeCarga[]>('/equipos')
  return data
}

// GET /programas?equipo_id=: programas del método del equipo, con sus parámetros
export async function obtenerProgramas(equipoId: number): Promise<Programa[]> {
  const { data } = await api.get<Programa[]>('/programas', { params: { equipo_id: equipoId } })
  return data
}

// GET /equipos/{id}/pendientes: lo que puede entrar a ese equipo (ya filtrado por su método)
export async function obtenerPendientes(equipoId: number): Promise<PendienteCarga[]> {
  const { data } = await api.get<PendienteCarga[]>(`/equipos/${equipoId}/pendientes`)
  return data
}

// GET /equipos/{id}/proximo-numero: es una propuesta, no una reserva (1 a 999, se repite)
export async function obtenerProximoNumero(equipoId: number): Promise<number> {
  const { data } = await api.get<{ equipo_id: number; numero: number }>(
    `/equipos/${equipoId}/proximo-numero`,
  )
  return data.numero
}

// POST /lotes: crea el lote y pasa sus ítems a Esterilización.
// Errores: 404 equipo inexistente; 422 programa de otro método, Bowie-Dick faltante,
// material insuficiente o servicios incompatibles (usar mensajeDeError).
export async function crearLote(datos: NuevoLote): Promise<LoteCreado> {
  const { data } = await api.post<LoteCreado>('/lotes', datos)
  return data
}

// GET /lotes?en_curso=true: lotes sin cerrar, del más nuevo al más viejo
export async function obtenerLotesEnCurso(): Promise<LoteResumen[]> {
  const { data } = await api.get<LoteResumen[]>('/lotes', { params: { en_curso: true } })
  return data
}

// POST /lotes/{id}/cierre: 404 no existe, 409 ya cerrado, 422 cuerpo inválido
export async function cerrarLote(id: number, datos: CierreLote): Promise<LoteCerrado> {
  const { data } = await api.post<LoteCerrado>(`/lotes/${id}/cierre`, datos)
  return data
}

// GET /equipos/{id}/bowie-dick/hoy: si el último control de hoy del equipo está aprobado
export async function obtenerBowieDickHoy(equipoId: number): Promise<BowieDickHoy> {
  const { data } = await api.get<BowieDickHoy>(`/equipos/${equipoId}/bowie-dick/hoy`)
  return data
}

// POST /equipos/{id}/bowie-dick: solo en el autoclave (si no, 422). 404 equipo inexistente.
export async function registrarBowieDick(
  equipoId: number,
  datos: NuevoBowieDick,
): Promise<BowieDickRegistrado> {
  const { data } = await api.post<BowieDickRegistrado>(`/equipos/${equipoId}/bowie-dick`, datos)
  return data
}

// Convierte el error del back en un texto para mostrar en pantalla.
// Las reglas (404, 409 y 422 de negocio) llegan como texto; las validaciones del
// esquema (422), como lista de pydantic: se muestra el primer mensaje sin su prefijo.
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
