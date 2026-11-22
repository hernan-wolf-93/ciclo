import { api } from './api'
import type { Aviso } from '../types'

// GET /avisos: material detenido (fuera de su tiempo normal) y listo para retirar.
// Vienen ordenados: primero los detenidos, del más demorado al menos.
export async function obtenerAvisos(): Promise<Aviso[]> {
  const { data } = await api.get<Aviso[]>('/avisos')
  return data
}
