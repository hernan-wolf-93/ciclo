import { MATERIALES, SERVICIOS } from '../mocks/catalogos'
import type { Material, NuevaRecepcion, RecepcionCreada, Servicio } from '../types'

// * Por ahora todo devuelve datos de prueba. Cuando Lobo tenga la API,
// * cambiamos solo el interior de estas funciones y la pantalla no se toca.

let contadorRecepciones = 0

// Simula la demora de una API de verdad
const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function obtenerServicios(): Promise<Servicio[]> {
  // TODO: GET /servicios
  await esperar(200)
  return SERVICIOS
}

export async function obtenerMateriales(): Promise<Material[]> {
  // TODO: GET /materiales
  await esperar(200)
  return MATERIALES
}

export async function registrarRecepcion(datos: NuevaRecepcion): Promise<RecepcionCreada> {
  // TODO: POST /recepciones
  await esperar(500)
  contadorRecepciones++

  return {
    id: contadorRecepciones,
    servicio_id: datos.servicio_id,
    fecha_hora: new Date().toISOString(),
    total_items: datos.items.reduce((suma, item) => suma + item.cantidad, 0),
  }
}