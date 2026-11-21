import {
  MATERIALES_OFICIALES,
  MATERIALES_POR_SERVICIO,
  SERVICIOS_OFICIALES,
} from '../mocks/catalogoOficial'
import type { Material, NuevaRecepcion, RecepcionCreada, Servicio } from '../types'

// * Por ahora todo devuelve datos de prueba. Cuando Lobo tenga la API,
// * cambiamos solo el interior de estas funciones y la pantalla no se toca.

let contadorRecepciones = 0

// Simula la demora de una API de verdad
const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function obtenerServicios(): Promise<Servicio[]> {
  // TODO: GET /servicios
  await esperar(200)
  return SERVICIOS_OFICIALES
}

// Materiales que se RECIBEN de un servicio (lo tachado en la planilla no va)
export async function obtenerMateriales(servicioId: number): Promise<Material[]> {
  // TODO: GET /materiales?servicio_id=
  await esperar(200)
  const ids = MATERIALES_POR_SERVICIO[servicioId] ?? []
  return MATERIALES_OFICIALES.filter((m) => m.se_recibe && ids.includes(m.id))
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