// * Tipos compartidos entre pantallas y servicios.
// * Los nombres copian los del modelo de Lobo (backend/app/models).

export interface Servicio {
  id: number
  nombre: string
  dias_aireacion: number // días de aireación de óxido de etileno según el origen (migración 0007)
}

export interface Material {
  id: number
  nombre: string
  codigo: string | null // en el back es opcional
  seccion?: 'calor' | 'oxido' // catálogo oficial: autoclave/estufa u óxido de etileno
  se_recibe?: boolean // false = solo se entrega (tachado en la planilla de recepción)
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
// * Los parámetros son los programados en el equipo (informe del autoclave,
// * fotos del 13/11/2026). El encabezado del ticket los repite.
// ! PROVISORIO: temperatura_c, tiempo_esterilizacion_min, tiempo_secado_min,
// ! vacio_bar, vapor_bar y pulsos todavía no existen: necesitan la migración 0008.
export interface Programa {
  id: number
  nombre: string
  metodo_id: number
  temperatura_c: number
  tiempo_esterilizacion_min: number
  tiempo_secado_min: number | null // null = sin dato para ese equipo
  vacio_bar: number | null // presión negativa, ej.: -0.75
  vapor_bar: number | null
  pulsos: number | null // pulsos de vapor y vacío
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

// lote.resultado: null mientras el lote está en curso (CHECK ck_lote_resultado_valido)
export type ResultadoLote = 'aprobado' | 'fallido'

// Referencia corta a otro lote (para el vínculo con el reemplazo)
export interface LoteRef {
  id: number
  numero: number
}

// Una fila de la lista de lotes
export interface LoteResumen {
  id: number
  numero: number // se reinicia (1 a 999) y puede repetirse: la fecha los distingue
  inicio: string
  fin: string | null
  equipo: Equipo
  resultado: ResultadoLote | null // lote.resultado
  // * No se guarda: el back la deduce. Es la mayor fecha de fin de aireación de
  // * sus ítems (lote.fin + servicio.dias_aireacion). null si no es óxido de etileno.
  aireacion_fin_max: string | null
}

// Historial de un ítem: una fila de la tabla evento_item
export interface EventoItem {
  id: number
  item_id: number
  etapa_id: number
  operador_id: number
  lote_id: number | null // solo en Esterilización: el lote de cada intento
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
  lote_id: number | null // el lote de su último evento de Esterilización
  entrega_id: number | null
  material: Material
  servicio: Servicio // servicio de origen (item.recepcion.servicio), con dias_aireacion
  eventos: EventoItem[]
}

export interface LoteDetalle {
  id: number
  numero: number // puede repetirse (ver LoteResumen)
  equipo_id: number
  programa_id: number
  operador_id: number
  inicio: string
  fin: string | null
  resultado: ResultadoLote | null
  observacion: string | null // motivo, obligatorio si resultado es 'fallido'
  // ! PROVISORIO: N.º de ciclo impreso en el ticket del equipo. La columna
  // ! lote.numero_ciclo todavía no existe: necesita la migración 0008.
  numero_ciclo: string | null
  equipo: Equipo
  programa: Programa // con sus parámetros: son los "datos del ciclo"
  operador: Operador
  // ! PROVISORIO: el vínculo con el reemplazo no se guarda. El back lo deduce de
  // ! los ítems con dos eventos de Esterilización (uno por lote).
  reemplazado_por: LoteRef | null // este lote falló y su material pasó a este otro
  reemplaza_a: LoteRef | null // este es el lote de reemplazo de uno que falló
  // Ítems que pasaron por el lote: los de sus eventos de Esterilización
  // (evento_item.lote_id), aunque hoy su item.lote_id sea el del lote de reemplazo
  items: ItemDelLote[]
}

// Estado que muestra la pantalla. No se guarda: se deduce de fin, resultado y aireación.
export type EstadoLote = 'en_curso' | 'en_aireacion' | 'aprobado' | 'fallido'
// Operador con sesión iniciada (respuesta de GET /auth/me)
export interface Usuario {
  id: number
  numero_operador: string
  rol: string // 'Administrador principal' | 'Administrador secundario' | 'Operador'
}

// ---------------------------------------------------------------------------
// Usuarios (ABM de operadores, solo administradores)
// ---------------------------------------------------------------------------
export interface Rol {
  id: number
  nombre: string
}

export interface UsuarioAdmin {
  id: number
  numero_operador: string
  rol: string // nombre del rol
  activo: boolean
}