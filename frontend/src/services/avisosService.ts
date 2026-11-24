import { api } from './api'
import type { Aviso } from '../types'

// GET /avisos: material detenido (fuera de su tiempo normal) y listo para retirar.
// Vienen ordenados: primero los detenidos (graves, después por cuántas veces pasaron
// su umbral y después por antigüedad) y al final los listos para retirar, por antigüedad.
export async function obtenerAvisos(): Promise<Aviso[]> {
  const { data } = await api.get<Aviso[]>('/avisos')
  return data
}
