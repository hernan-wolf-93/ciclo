// * Tipos compartidos entre pantallas y servicios.
// * Los nombres copian los del modelo de Lobo (backend/app/models).

export interface Servicio {
  id: number
  nombre: string
}

export interface Material {
  id: number
  nombre: string
  codigo: string | null // en el back es opcional
}

// Lo que se carga por cada material: cuál y cuántas unidades
export interface ItemRecepcion {
  material_id: number
  cantidad: number
}

// Lo que la pantalla le manda al back (! acordar con Lobo)
export interface NuevaRecepcion {
  servicio_id: number
  operador: string
  items: ItemRecepcion[]
  completo: boolean // ? todavía no existe en el modelo
  observacion?: string // ? todavía no existe en el modelo
    servicio_avisado?: boolean // ? solo si falta una pieza: confirma que se le avisó al servicio
}

// Lo que devuelve el back al registrar
export interface RecepcionCreada {
  id: number
  servicio_id: number
  fecha_hora: string
  total_items: number
}

// ---------------------------------------------------------------------------
// Lotes (RF3: historial y detalle del lote)
// * "Lote" es la carga de un equipo de esterilización. No existe lote de recepción.
// * Los objetos anidados siguen las relaciones del modelo (lote.equipo,
// * equipo.metodo, item.eventos) para que el back los arme con pydantic.
// ---------------------------------------------------------------------------

export interface MetodoEsterilizacion {
  id: number
  nombre: string
}

export interface Equipo {
  id: number
  nombre: string
  metodo_id: number
  metodo: MetodoEsterilizacion // * el método del lote sale de su equipo
}

// ? En el modelo, programa.metodo_id es provisorio (pendiente de validar con el servicio)
export interface Programa {
  id: number
  nombre: string
  metodo_id: number
}

export interface Etapa {
  id: number
  orden: number
  nombre: string
  area: string
  color: string
}

// * Al operador se lo identifica solo por su número, nunca por el nombre
export interface Operador {
  id: number
  numero_operador: string
}

// ! PROVISORIO: falta confirmar con el servicio qué datos trae el ticket
// ! del equipo (pregunta 8). Todavía no existe en el modelo.
export type ResultadoCiclo = 'aprobado' | 'fallido'

export interface DatosCiclo {
  numero_ciclo: string // N.º de ciclo impreso en el ticket del equipo
  temperatura_c: number | null
  tiempo_min: number | null
  resultado: ResultadoCiclo | null // null mientras el ciclo no terminó
}

// ! PROVISORIO: no existe en el modelo (ver "Reprocesamiento" en docs/DER.md)
export interface Reesterilizacion {
  motivo: string
  lote_nuevo_id: number
  lote_nuevo_numero: number
}

// Una fila de la lista de lotes
export interface LoteResumen {
  id: number
  numero: number // ! se reinicia (01 a 999): puede repetirse, la fecha los distingue
  inicio: string
  fin: string | null
  equipo: Equipo
  resultado: ResultadoCiclo | null // ! provisorio: sale de DatosCiclo
  aireacion_fin_max: string | null // ! provisorio: la mayor aireacion_fin de sus ítems
}

// Historial de un ítem: una fila de la tabla evento_item
export interface EventoItem {
  id: number
  item_id: number
  etapa_id: number
  operador_id: number
  // ! PROVISORIO: la columna todavía no existe en el modelo. Solo tiene valor
  // ! en los eventos de Esterilización: vincula cada intento con su lote.
  lote_id: number | null
  fecha_hora: string
  etapa: Etapa
  operador: Operador
}

// * Una unidad física de material. La etapa actual no se guarda:
// * se deduce de su último evento.
export interface ItemDelLote {
  id: number
  recepcion_id: number
  material_id: number
  metodo_id: number | null
  lote_id: number | null
  entrega_id: number | null
  material: Material
  servicio: Servicio // servicio de origen (item.recepcion.servicio)
  // ! PROVISORIO: solo óxido de etileno. Fin de la aireación de este ítem;
  // ! los días dependen del servicio de origen. null = no lleva aireación.
  aireacion_fin: string | null
  eventos: EventoItem[]
}

export interface LoteDetalle {
  id: number
  numero: number // ! puede repetirse (ver LoteResumen)
  equipo_id: number
  programa_id: number
  operador_id: number
  inicio: string
  fin: string | null
  equipo: Equipo
  programa: Programa
  operador: Operador
  ciclo: DatosCiclo | null // ! provisorio
  reesterilizacion: Reesterilizacion | null // ! provisorio: este lote falló y se reemplazó
  reemplaza_a: { id: number; numero: number } | null // ! provisorio: este es el lote de reemplazo
  items: ItemDelLote[]
}

// Estado que muestra la pantalla. No se guarda: se deduce de fin, ciclo y aireación.
export type EstadoLote = 'en_curso' | 'en_aireacion' | 'aprobado' | 'fallido'