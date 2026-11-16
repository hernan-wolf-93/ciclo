import { LOTES } from '../mocks/lotes'
import type { LoteDetalle, LoteResumen } from '../types'
import { finAireacionLote } from '../utils/aireacion'

// * Por ahora todo devuelve datos de prueba. Cuando Lobo tenga la API,
// * cambiamos solo el interior de estas funciones y la pantalla no se toca.

// Simula la demora de una API de verdad
const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

// Arma la fila de la lista a partir del detalle (en la API lo hará el back)
function resumir(lote: LoteDetalle): LoteResumen {
  return {
    id: lote.id,
    numero: lote.numero,
    inicio: lote.inicio,
    fin: lote.fin,
    equipo: lote.equipo,
    resultado: lote.resultado,
    aireacion_fin_max: finAireacionLote(
      lote.equipo,
      lote.fin,
      lote.items.map((i) => i.servicio),
    ),
  }
}

// El número de lote se reinicia (1 a 999): buscar por número puede
// devolver varios lotes. Vienen del más nuevo al más viejo.
export async function obtenerLotes(numero?: number): Promise<LoteResumen[]> {
  // TODO: GET /lotes?numero={numero}  (sin número: los más recientes)
  await esperar(300)

  return LOTES.filter((l) => numero === undefined || l.numero === numero)
    .sort((a, b) => b.inicio.localeCompare(a.inicio))
    .map(resumir)
}

export async function obtenerLote(id: number): Promise<LoteDetalle> {
  // TODO: GET /lotes/{id}  (con equipo, programa, operador, ciclo e ítems con sus eventos)
  await esperar(300)

  const lote = LOTES.find((l) => l.id === id)
  if (!lote) throw new Error(`No existe el lote ${id}`)
  return lote
}
