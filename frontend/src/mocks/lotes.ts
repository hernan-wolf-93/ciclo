import { MATERIALES, SERVICIOS } from './catalogos'
import type {
  Equipo,
  Etapa,
  EventoItem,
  ItemDelLote,
  LoteDetalle,
  MetodoEsterilizacion,
  Operador,
  Programa,
} from '../types'

// * Datos de prueba ficticios para la pantalla Lotes.
// * Las fechas se calculan a partir de hoy, así siempre se ven recientes
// * y el lote de óxido de etileno sigue "en aireación" cuando se prueba.

// ---------------------------------------------------------------------------
// Catálogos: mismos que las migraciones 0002 y 0004 del back
// ---------------------------------------------------------------------------

const METODOS: MetodoEsterilizacion[] = [
  { id: 1, nombre: 'Calor húmedo' },
  { id: 2, nombre: 'Calor seco' },
  { id: 3, nombre: 'Óxido de etileno' },
]

const metodo = (id: number) => METODOS.find((m) => m.id === id)!

const EQUIPOS: Equipo[] = [
  { id: 1, nombre: 'Autoclave 1', metodo_id: 1, metodo: metodo(1) },
  { id: 2, nombre: 'Autoclave 2', metodo_id: 1, metodo: metodo(1) },
  { id: 3, nombre: 'Estufa 1', metodo_id: 2, metodo: metodo(2) },
  { id: 4, nombre: 'Estufa 2', metodo_id: 2, metodo: metodo(2) },
  { id: 5, nombre: 'Óxido de etileno 1', metodo_id: 3, metodo: metodo(3) },
]

const PROGRAMAS: Programa[] = [
  { id: 1, nombre: 'Textil 134 °C', metodo_id: 1 },
  { id: 2, nombre: 'Instrumental 134 °C', metodo_id: 1 },
  { id: 3, nombre: 'Gomas 121 °C', metodo_id: 1 },
  // ! Lobo: confirmado por el servicio, pero todavía no está en la base
  // ! (la migración 0004 solo carga programas de calor húmedo). Provisorio.
  { id: 4, nombre: 'Ciclo caliente 56 °C', metodo_id: 3 },
]

const ETAPAS: Etapa[] = [
  { id: 1, orden: 1, nombre: 'Recepción', area: 'Sucia', color: 'Rojo' },
  { id: 2, orden: 2, nombre: 'Lavado y secado', area: 'Sucia', color: 'Rojo' },
  { id: 3, orden: 3, nombre: 'Empaque y rotulación', area: 'Limpia', color: 'Azul' },
  { id: 4, orden: 4, nombre: 'Esterilización', area: 'Esterilización', color: 'Gris' },
  { id: 5, orden: 5, nombre: 'Almacén estéril', area: 'Limpia', color: 'Verde' },
  { id: 6, orden: 6, nombre: 'Entrega', area: 'Limpia', color: 'Verde' },
]

// Operadores ficticios: solo número, nunca nombres
const OPERADORES: Operador[] = [
  { id: 1, numero_operador: '2041' },
  { id: 2, numero_operador: '2057' },
  { id: 3, numero_operador: '3112' },
  { id: 4, numero_operador: '3120' },
]

const equipo = (id: number) => EQUIPOS.find((e) => e.id === id)!
const programa = (id: number) => PROGRAMAS.find((p) => p.id === id)!
const etapa = (id: number) => ETAPAS.find((e) => e.id === id)!
const operador = (id: number) => OPERADORES.find((o) => o.id === id)!
const servicio = (id: number) => SERVICIOS.find((s) => s.id === id)!
const material = (id: number) => MATERIALES.find((m) => m.id === id)!

// Ids de etapa, para que los pasos se lean mejor
const RECEPCION = 1
const LAVADO = 2
const EMPAQUE = 3
const ESTERILIZACION = 4
const ALMACEN = 5
const ENTREGA = 6

// ---------------------------------------------------------------------------
// Fechas relativas a hoy
// ---------------------------------------------------------------------------

// Un día pasado a una hora fija. Ej: momento(2, '10:30') = anteayer a las 10:30
function momento(diasAtras: number, hora: string): string {
  const [h, m] = hora.split(':').map(Number)
  const fecha = new Date()
  fecha.setDate(fecha.getDate() - diasAtras)
  fecha.setHours(h, m, 0, 0)
  return fecha.toISOString()
}

function haceMinutos(minutos: number): string {
  return new Date(Date.now() - minutos * 60_000).toISOString()
}

function sumarDias(iso: string, dias: number): string {
  const fecha = new Date(iso)
  fecha.setDate(fecha.getDate() + dias)
  return fecha.toISOString()
}

// ---------------------------------------------------------------------------
// Aireación (solo óxido de etileno)
// ! Lobo: regla confirmada por la jefa del servicio. Los días dependen del
// ! servicio de origen del ítem: Neonatología 10, Pediatría 7, el resto 3.
// ! Conviene que la calcule el back y devuelva aireacion_fin en cada ítem.
// ---------------------------------------------------------------------------

const DIAS_AIREACION: Record<number, number> = {
  2: 10, // Neonatología
  4: 7, // Pediatría
}

function finAireacion(finLote: string, servicioId: number): string {
  return sumarDias(finLote, DIAS_AIREACION[servicioId] ?? 3)
}

// ---------------------------------------------------------------------------
// Ítems y eventos
// ---------------------------------------------------------------------------

// Un paso del historial: [etapa, fecha y hora, operador]
type Paso = [etapaId: number, fechaHora: string, operadorId: number]

let siguienteEvento = 1

function eventos(itemId: number, pasos: Paso[]): EventoItem[] {
  return pasos.map(([etapa_id, fecha_hora, operador_id]) => ({
    id: siguienteEvento++,
    item_id: itemId,
    etapa_id,
    operador_id,
    fecha_hora,
    etapa: etapa(etapa_id),
    operador: operador(operador_id),
  }))
}

interface DatosItem {
  id: number
  recepcion_id: number
  material_id: number
  servicio_id: number
  metodo_id: number
  lote_id: number
  entrega_id?: number
  aireacion_fin?: string
  pasos: Paso[]
}

function item(d: DatosItem): ItemDelLote {
  return {
    id: d.id,
    recepcion_id: d.recepcion_id,
    material_id: d.material_id,
    metodo_id: d.metodo_id,
    lote_id: d.lote_id,
    entrega_id: d.entrega_id ?? null,
    material: material(d.material_id),
    servicio: servicio(d.servicio_id),
    aireacion_fin: d.aireacion_fin ?? null,
    eventos: eventos(d.id, d.pasos),
  }
}

// ---------------------------------------------------------------------------
// Lotes
// ! Lobo: el número de lote va del 01 al 999 y se reinicia, así que se repite.
// ! Por eso hay dos lotes N.º 12: la fecha es lo que los distingue.
// ---------------------------------------------------------------------------

// Lote viejo con el mismo número que uno reciente (N.º 12)
const finLoteViejo = momento(150, '10:05')
const loteViejo: LoteDetalle = {
  id: 1,
  numero: 12,
  equipo_id: 1,
  programa_id: 3,
  operador_id: 3,
  inicio: momento(150, '09:00'),
  fin: finLoteViejo,
  equipo: equipo(1),
  programa: programa(3),
  operador: operador(3),
  ciclo: { numero_ciclo: '0412', temperatura_c: 121, tiempo_min: 65, resultado: 'aprobado' },
  reesterilizacion: null,
  reemplaza_a: null,
  items: [
    item({
      id: 1, recepcion_id: 1, material_id: 15, servicio_id: 1, metodo_id: 1, lote_id: 1, entrega_id: 1,
      pasos: [
        [RECEPCION, momento(151, '08:10'), 1],
        [LAVADO, momento(151, '09:30'), 2],
        [EMPAQUE, momento(151, '11:00'), 2],
        [ESTERILIZACION, momento(150, '09:00'), 3],
        [ALMACEN, momento(150, '10:20'), 3],
        [ENTREGA, momento(149, '08:40'), 1],
      ],
    }),
  ],
}

// Óxido de etileno en aireación: mezcla Guardia (3 días) y Pediatría (7 días).
// Terminó hace 4 días: Guardia ya cumplió la aireación, Pediatría todavía no.
const finLoteOxido = momento(4, '13:30')
const loteOxido: LoteDetalle = {
  id: 2,
  numero: 11,
  equipo_id: 5,
  programa_id: 4,
  operador_id: 2,
  inicio: momento(4, '08:30'),
  fin: finLoteOxido,
  equipo: equipo(5),
  programa: programa(4),
  operador: operador(2),
  ciclo: { numero_ciclo: '0087', temperatura_c: 56, tiempo_min: 300, resultado: 'aprobado' },
  reesterilizacion: null,
  reemplaza_a: null,
  items: [
    item({
      id: 2, recepcion_id: 2, material_id: 14, servicio_id: 3, metodo_id: 3, lote_id: 2,
      aireacion_fin: finAireacion(finLoteOxido, 3),
      pasos: [
        [RECEPCION, momento(5, '07:40'), 1],
        [LAVADO, momento(5, '09:15'), 2],
        [EMPAQUE, momento(5, '11:00'), 4],
        [ESTERILIZACION, momento(4, '08:30'), 2],
        [ALMACEN, momento(1, '14:00'), 4],
      ],
    }),
    item({
      id: 3, recepcion_id: 3, material_id: 3, servicio_id: 4, metodo_id: 3, lote_id: 2,
      aireacion_fin: finAireacion(finLoteOxido, 4),
      pasos: [
        [RECEPCION, momento(5, '08:05'), 1],
        [LAVADO, momento(5, '09:40'), 2],
        [EMPAQUE, momento(5, '11:20'), 4],
        [ESTERILIZACION, momento(4, '08:30'), 2],
      ],
    }),
    item({
      id: 4, recepcion_id: 3, material_id: 4, servicio_id: 4, metodo_id: 3, lote_id: 2,
      aireacion_fin: finAireacion(finLoteOxido, 4),
      pasos: [
        [RECEPCION, momento(5, '08:05'), 1],
        [LAVADO, momento(5, '09:40'), 2],
        [EMPAQUE, momento(5, '11:25'), 4],
        [ESTERILIZACION, momento(4, '08:30'), 2],
      ],
    }),
  ],
}

// Autoclave completo: un ítem ya entregado y dos en almacén estéril
const loteAutoclave: LoteDetalle = {
  id: 3,
  numero: 12,
  equipo_id: 1,
  programa_id: 1,
  operador_id: 1,
  inicio: momento(2, '10:00'),
  fin: momento(2, '11:10'),
  equipo: equipo(1),
  programa: programa(1),
  operador: operador(1),
  ciclo: { numero_ciclo: '1187', temperatura_c: 134, tiempo_min: 45, resultado: 'aprobado' },
  reesterilizacion: null,
  reemplaza_a: null,
  items: [
    item({
      id: 5, recepcion_id: 4, material_id: 12, servicio_id: 1, metodo_id: 1, lote_id: 3, entrega_id: 2,
      pasos: [
        [RECEPCION, momento(3, '07:50'), 1],
        [LAVADO, momento(3, '09:00'), 2],
        [EMPAQUE, momento(3, '12:30'), 4],
        [ESTERILIZACION, momento(2, '10:00'), 1],
        [ALMACEN, momento(2, '11:30'), 1],
        [ENTREGA, momento(1, '08:15'), 3],
      ],
    }),
    item({
      id: 6, recepcion_id: 5, material_id: 2, servicio_id: 3, metodo_id: 1, lote_id: 3,
      pasos: [
        [RECEPCION, momento(3, '08:20'), 1],
        [LAVADO, momento(3, '09:40'), 2],
        [EMPAQUE, momento(3, '13:00'), 4],
        [ESTERILIZACION, momento(2, '10:00'), 1],
        [ALMACEN, momento(2, '11:30'), 1],
      ],
    }),
    item({
      id: 7, recepcion_id: 4, material_id: 13, servicio_id: 1, metodo_id: 1, lote_id: 3,
      pasos: [
        [RECEPCION, momento(3, '07:50'), 1],
        [LAVADO, momento(3, '09:10'), 2],
        [EMPAQUE, momento(3, '12:45'), 4],
        [ESTERILIZACION, momento(2, '10:00'), 1],
        [ALMACEN, momento(2, '11:30'), 1],
      ],
    }),
  ],
}

// ! Lobo: reesterilización. Con el modelo actual hay dos problemas:
// !  1. item.lote_id guarda un solo lote: al pasar al lote nuevo, el lote
// !     fallido "pierde" sus ítems. Acá el detalle devuelve los ítems que
// !     PASARON por el lote, aunque su lote_id ya sea el del lote nuevo.
// !  2. uq_evento_item_etapa no deja que un ítem pase dos veces por
// !     Esterilización. Acá el historial tiene los dos eventos.
// ! Los mismos ítems aparecen en el lote fallido y en el de reemplazo.
const itemsReesterilizados: ItemDelLote[] = [
  item({
    id: 8, recepcion_id: 6, material_id: 13, servicio_id: 2, metodo_id: 1, lote_id: 5,
    pasos: [
      [RECEPCION, momento(2, '08:00'), 1],
      [LAVADO, momento(2, '10:00'), 2],
      [EMPAQUE, momento(2, '14:00'), 4],
      [ESTERILIZACION, momento(1, '09:00'), 3], // lote 13, falló
      [ESTERILIZACION, momento(1, '11:00'), 1], // lote 14, reemplazo
      [ALMACEN, momento(1, '12:20'), 1],
    ],
  }),
  item({
    id: 9, recepcion_id: 7, material_id: 9, servicio_id: 5, metodo_id: 1, lote_id: 5,
    pasos: [
      [RECEPCION, momento(2, '08:30'), 1],
      [LAVADO, momento(2, '10:15'), 2],
      [EMPAQUE, momento(2, '14:10'), 4],
      [ESTERILIZACION, momento(1, '09:00'), 3], // lote 13, falló
      [ESTERILIZACION, momento(1, '11:00'), 1], // lote 14, reemplazo
      [ALMACEN, momento(1, '12:20'), 1],
    ],
  }),
]

const loteFallido: LoteDetalle = {
  id: 4,
  numero: 13,
  equipo_id: 2,
  programa_id: 2,
  operador_id: 3,
  inicio: momento(1, '09:00'),
  fin: momento(1, '09:40'),
  equipo: equipo(2),
  programa: programa(2),
  operador: operador(3),
  ciclo: { numero_ciclo: '2231', temperatura_c: 128, tiempo_min: 40, resultado: 'fallido' },
  reesterilizacion: {
    motivo: 'El ciclo se cortó por caída de presión y el indicador químico no viró.',
    lote_nuevo_id: 5,
    lote_nuevo_numero: 14,
  },
  reemplaza_a: null,
  items: itemsReesterilizados,
}

const loteReemplazo: LoteDetalle = {
  id: 5,
  numero: 14,
  equipo_id: 1,
  programa_id: 2,
  operador_id: 1,
  inicio: momento(1, '11:00'),
  fin: momento(1, '12:10'),
  equipo: equipo(1),
  programa: programa(2),
  operador: operador(1),
  ciclo: { numero_ciclo: '1188', temperatura_c: 134, tiempo_min: 50, resultado: 'aprobado' },
  reesterilizacion: null,
  reemplaza_a: { id: 4, numero: 13 },
  items: itemsReesterilizados,
}

// En curso: empezó hace 35 minutos, todavía sin fin ni resultado
const loteEnCurso: LoteDetalle = {
  id: 6,
  numero: 15,
  equipo_id: 1,
  programa_id: 1,
  operador_id: 2,
  inicio: haceMinutos(35),
  fin: null,
  equipo: equipo(1),
  programa: programa(1),
  operador: operador(2),
  ciclo: { numero_ciclo: '1189', temperatura_c: null, tiempo_min: null, resultado: null },
  reesterilizacion: null,
  reemplaza_a: null,
  items: [
    item({
      id: 10, recepcion_id: 8, material_id: 6, servicio_id: 1, metodo_id: 1, lote_id: 6,
      pasos: [
        [RECEPCION, momento(1, '07:45'), 1],
        [LAVADO, momento(1, '09:30'), 2],
        [EMPAQUE, momento(1, '13:40'), 4],
        [ESTERILIZACION, haceMinutos(35), 2],
      ],
    }),
    item({
      id: 11, recepcion_id: 8, material_id: 11, servicio_id: 1, metodo_id: 1, lote_id: 6,
      pasos: [
        [RECEPCION, momento(1, '07:45'), 1],
        [LAVADO, momento(1, '09:35'), 2],
        [EMPAQUE, momento(1, '13:50'), 4],
        [ESTERILIZACION, haceMinutos(35), 2],
      ],
    }),
    item({
      id: 12, recepcion_id: 9, material_id: 5, servicio_id: 3, metodo_id: 1, lote_id: 6,
      pasos: [
        [RECEPCION, momento(1, '08:10'), 1],
        [LAVADO, momento(1, '10:00'), 2],
        [EMPAQUE, momento(1, '14:05'), 4],
        [ESTERILIZACION, haceMinutos(35), 2],
      ],
    }),
  ],
}

export const LOTES: LoteDetalle[] = [
  loteViejo,
  loteOxido,
  loteAutoclave,
  loteFallido,
  loteReemplazo,
  loteEnCurso,
]
