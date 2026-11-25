import axios from 'axios'
import { ENTREGAS_DISPONIBLES } from '../mocks/entregas'
import type { EntregaCreada, EntregaDisponible, NuevaEntrega } from '../types'

// * Pantalla de Entrega. Por ahora todo devuelve datos de prueba. Cuando Lobo una la
// * API, cambiamos solo el interior de estas funciones y la pantalla no se toca.
// ! El contrato es un borrador de Lobo: puede cambiar.
// * El operador que entrega sale del token (no va en el cuerpo).

// Simula la demora de una API de verdad
const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

// Copia del mock que se va descontando con cada entrega (se reinicia al recargar la página)
const disponibles: EntregaDisponible[] = ENTREGAS_DISPONIBLES.map((f) => ({ ...f }))
let contadorEntregas = 0

// * Error con el código HTTP, para que el mock falle igual que la API
export class ErrorDeEntrega extends Error {
  status: number
  constructor(status: number) {
    super(`Error ${status} al registrar la entrega`)
    this.status = status
  }
}

export interface FiltrosEntrega {
  servicioId?: number
  loteNumero?: number
  q?: string // código o nombre del material
}

// Material listo para entregar: en Almacén, de lotes aprobados y sin entregar.
// Ordenado: urgentes primero y después los lotes más antiguos (la pantalla respeta este orden).
export async function obtenerDisponibles(filtros: FiltrosEntrega): Promise<EntregaDisponible[]> {
  // TODO: GET /entregas/disponibles?servicio_id=&lote_numero=&q=
  await esperar(300)

  const q = filtros.q?.trim().toLowerCase() ?? ''

  return disponibles
    .filter((f) => f.cantidad_entregable > 0)
    .filter((f) => filtros.servicioId === undefined || f.servicio_id === filtros.servicioId)
    .filter((f) => filtros.loteNumero === undefined || f.lote_numero === filtros.loteNumero)
    .filter((f) => q === '' || f.material.toLowerCase().includes(q) || (f.codigo ?? '').toLowerCase().includes(q))
    .sort((a, b) => Number(b.urgente) - Number(a.urgente) || a.lote_id - b.lote_id)
    .map((f) => ({ ...f }))
}

// Registra la entrega a UN servicio. Una cantidad menor que la entregable es una entrega
// parcial: el resto sigue disponible.
// Errores: 401 sin sesión; 404 servicio, lote o material inexistente; 422 más de lo
// entregable, (lote, material) repetido o cantidad inválida; 409 el lote cambió de estado.
export async function registrarEntrega(datos: NuevaEntrega): Promise<EntregaCreada> {
  // TODO: POST /entregas
  await esperar(500)

  // ! SOLO PARA PROBAR LOS ERRORES CON EL MOCK: sacarlo al conectar la API
  if (datos.observacion === 'simular 409') throw new ErrorDeEntrega(409)
  if (datos.observacion === 'simular 422') throw new ErrorDeEntrega(422)

  // * Validamos TODAS las líneas antes de descontar, así no queda una entrega a medias
  const usadas = new Set<string>()
  const filas: { fila: EntregaDisponible; cantidad: number }[] = []

  for (const linea of datos.lineas) {
    const clave = `${linea.lote_id}-${linea.material_id}`
    if (usadas.has(clave)) throw new ErrorDeEntrega(422) // (lote, material) repetido
    usadas.add(clave)

    const fila = disponibles.find(
      (f) =>
        f.lote_id === linea.lote_id &&
        f.material_id === linea.material_id &&
        f.servicio_id === datos.servicio_id,
    )
    if (!fila) throw new ErrorDeEntrega(404)

    if (!Number.isInteger(linea.cantidad) || linea.cantidad <= 0 || linea.cantidad > fila.cantidad_entregable) {
      throw new ErrorDeEntrega(422)
    }

    filas.push({ fila, cantidad: linea.cantidad })
  }

  if (filas.length === 0) throw new ErrorDeEntrega(422)

  for (const { fila, cantidad } of filas) fila.cantidad_entregable -= cantidad

  contadorEntregas++
  return {
    id: contadorEntregas,
    servicio_id: datos.servicio_id,
    fecha_hora: new Date().toISOString(),
    observacion: datos.observacion ?? null,
    total_items: filas.reduce((suma, f) => suma + f.cantidad, 0),
  }
}

// Código HTTP del error, venga del mock o de la API (null si no hubo respuesta)
function codigoDeError(error: unknown): number | null {
  if (error instanceof ErrorDeEntrega) return error.status
  if (axios.isAxiosError(error)) return error.response?.status ?? null
  return null
}

// 409: el lote cambió de estado mientras tanto. La pantalla vuelve a pedir la lista.
export function esLoteCambiado(error: unknown): boolean {
  return codigoDeError(error) === 409
}

// Convierte el error en un texto para mostrar en pantalla.
// * El formato del 422 no está unificado en el back: mostramos un mensaje genérico.
export function mensajeDeError(error: unknown): string {
  if (codigoDeError(error) === 409) {
    return 'El estado de un lote cambió. Actualizamos la lista: revisá y volvé a intentar.'
  }
  return 'No se pudo registrar la entrega. Revisá las cantidades y volvé a intentar.'
}
