import { MATERIALES_OFICIALES, SERVICIOS_OFICIALES } from '../mocks/catalogoOficial'
import { PENDIENTES_ESTERILIZACION } from '../mocks/esterilizacion'
import { EQUIPOS, LOTES, PROGRAMAS } from '../mocks/lotes'
import type {
  CierreLote,
  Equipo,
  LoteAbierto,
  LoteCreado,
  NuevoLote,
  PendienteCarga,
  Programa,
} from '../types'

// * Por ahora todo devuelve datos de prueba. Cuando Lobo tenga la API,
// * cambiamos solo el interior de estas funciones y la pantalla no se toca.

// Simula la demora de una API de verdad
const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

// Copia de los pendientes: al crear un lote se descuenta de acá
const pendientes = PENDIENTES_ESTERILIZACION.map((p) => ({ ...p }))

// Lotes en curso: los de prueba con resultado null más los que se crean acá
const abiertos: LoteAbierto[] = LOTES.filter((l) => l.resultado === null).map((l) => ({
  id: l.id,
  numero: l.numero,
  inicio: l.inicio,
  equipo: l.equipo,
  programa: l.programa,
}))

// Lotes creados en esta sesión (aunque ya estén cerrados): sirven para proponer el número
const creados: { equipo_id: number; numero: number; inicio: string }[] = []
let ultimoId = Math.max(...LOTES.map((l) => l.id))

function buscarEquipo(id: number): Equipo {
  const equipo = EQUIPOS.find((e) => e.id === id)
  if (!equipo) throw new Error(`No existe el equipo ${id}`)
  return equipo
}

export async function obtenerEquipos(): Promise<Equipo[]> {
  // TODO: GET /equipos  (solo los activos)
  await esperar(200)
  return EQUIPOS
}

// Programas del método del equipo (cada uno con sus parámetros)
export async function obtenerProgramas(equipoId: number): Promise<Programa[]> {
  // TODO: GET /programas?equipo_id={equipoId}
  await esperar(200)
  const equipo = buscarEquipo(equipoId)
  return PROGRAMAS.filter((p) => p.metodo_id === equipo.metodo_id)
}

// Lo que espera entrar a ese equipo: solo lo del método del equipo
export async function obtenerPendientes(equipoId: number): Promise<PendienteCarga[]> {
  // TODO: GET /avances/pendientes?etapa_orden=4&equipo_id={equipoId}
  await esperar(300)
  const equipo = buscarEquipo(equipoId)

  return pendientes
    .filter((p) => p.metodo_id === equipo.metodo_id && p.cantidad > 0)
    .map((p) => ({
      servicio: SERVICIOS_OFICIALES.find((s) => s.id === p.servicio_id)!,
      material: MATERIALES_OFICIALES.find((m) => m.id === p.material_id)!,
      cantidad: p.cantidad,
    }))
}

// El número va de 1 a 999, es por equipo y se reinicia: último usado + 1
export async function obtenerProximoNumero(equipoId: number): Promise<number> {
  // TODO: GET /equipos/{equipoId}/proximo-numero
  await esperar(200)

  const usados = [
    ...LOTES.map((l) => ({ equipo_id: l.equipo_id, numero: l.numero, inicio: l.inicio })),
    ...creados,
  ].filter((l) => l.equipo_id === equipoId)

  // Sin lotes en ese equipo, arranca en 1
  if (usados.length === 0) return 1

  // El último es el más nuevo (no el número más alto, porque se reinicia)
  const ultimo = usados.reduce((a, b) => (b.inicio > a.inicio ? b : a))
  return ultimo.numero >= 999 ? 1 : ultimo.numero + 1
}

export async function crearLote(datos: NuevoLote): Promise<LoteCreado> {
  // TODO: POST /lotes  (responde 201 con el lote creado)
  await esperar(500)

  const equipo = buscarEquipo(datos.equipo_id)
  const programa = PROGRAMAS.find((p) => p.id === datos.programa_id && p.metodo_id === equipo.metodo_id)
  if (!programa) throw new Error('El programa no corresponde al método del equipo.')

  if (!Number.isInteger(datos.numero) || datos.numero < 1 || datos.numero > 999) {
    throw new Error('El número de lote tiene que ser de 1 a 999.')
  }
  if (datos.lineas.length === 0) throw new Error('Cargá al menos un paquete.')

  // Primero revisamos todas las líneas y después descontamos, así no queda a medias
  const aDescontar = datos.lineas.map((linea) => {
    const pendiente = pendientes.find(
      (p) =>
        p.metodo_id === equipo.metodo_id &&
        p.servicio_id === linea.servicio_id &&
        p.material_id === linea.material_id,
    )
    const disponible = pendiente?.cantidad ?? 0
    if (linea.cantidad < 1 || linea.cantidad > disponible) {
      const material = MATERIALES_OFICIALES.find((m) => m.id === linea.material_id)?.nombre ?? 'ese material'
      throw new Error(`Solo hay ${disponible} de ${material} esperando para este equipo.`)
    }
    return { pendiente: pendiente!, cantidad: linea.cantidad }
  })
  for (const { pendiente, cantidad } of aDescontar) pendiente.cantidad -= cantidad

  ultimoId++
  const inicio = new Date().toISOString()
  creados.push({ equipo_id: equipo.id, numero: datos.numero, inicio })
  abiertos.push({ id: ultimoId, numero: datos.numero, inicio, equipo, programa })

  return { id: ultimoId, numero: datos.numero, equipo_id: equipo.id, inicio }
}

// Lotes con resultado null. Vienen del más viejo al más nuevo.
export async function obtenerLotesEnCurso(): Promise<LoteAbierto[]> {
  // TODO: GET /lotes y filtrar los que tienen resultado en null
  await esperar(200)
  return [...abiertos].sort((a, b) => a.inicio.localeCompare(b.inicio))
}

export async function cerrarLote(id: number, datos: CierreLote): Promise<void> {
  // TODO: POST /lotes/{id}/cierre  ({ numero_ciclo (opcional), resultado, observacion })
  await esperar(400)

  const indice = abiertos.findIndex((l) => l.id === id)
  if (indice === -1) throw new Error(`No existe el lote ${id} o ya está cerrado`)

  if (datos.resultado === 'fallido' && !datos.observacion?.trim()) {
    throw new Error('La observación es obligatoria si el lote falla.')
  }

  abiertos.splice(indice, 1)
}
