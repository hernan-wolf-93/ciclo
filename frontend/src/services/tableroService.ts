import { api } from './api'
import type { FilaTablero, FiltrosTablero, LoteResumen } from '../types'

// GET /tablero: recepciones en curso, urgentes primero y la más antigua primero.
// lote_id se repite en la URL (?lote_id=1&lote_id=5), como lo espera FastAPI.
export async function obtenerTablero(filtros: FiltrosTablero = {}): Promise<FilaTablero[]> {
  const { data } = await api.get<FilaTablero[]>('/tablero', {
    params: { urgente: filtros.urgente, lote_id: filtros.lote_ids },
    paramsSerializer: { indexes: null },
  })
  return data
}

// GET /lotes?numero=: el número se repite (es por equipo), así que puede haber varios.
export async function buscarLotes(numero: number): Promise<LoteResumen[]> {
  const { data } = await api.get<LoteResumen[]>('/lotes', { params: { numero } })
  return data
}
