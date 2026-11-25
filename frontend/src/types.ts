// * Tipos compartidos entre pantallas y servicios.
// * Los nombres copian los del modelo de Lobo (backend/app/models).

export interface Servicio {
  id: number
  nombre: string
  dias_aireacion: number // días de aireación de óxido de etileno según el origen (migración 0007)
  externo?: boolean // centro externo (migración 0010); solo viene con ?incluir_inactivos=true (ver ServicioAdmin)
}

export interface Material {
  id: number
  nombre: string
  codigo: string | null // en el back es opcional
  seccion?: 'calor' | 'oxido' // catálogo oficial: autoclave/estufa u óxido de etileno
  se_recibe?: boolean // false = solo se entrega (tachado en la planilla de recepción)
  nombre_alternativo?: string | null // GET /materiales: nombre técnico o de cirugía
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
  requiere_aireacion: boolean // true solo en óxido de etileno (migración 0010)
  vencimiento_dias: number | null // provisorio: 90, 90 y 365
}

export interface Equipo {
  id: number
  nombre: string
  metodo_id: number
  metodo: MetodoEsterilizacion // * el método del lote sale de su equipo
}

// * Parámetros del panel del equipo (migración 0010, docs/RESPUESTAS-SERVICIO.md).
// * El encabezado del ticket los repite. Todos opcionales: el programa P de la estufa
// * no tiene valores fijos.
export interface Programa {
  id: number
  nombre: string
  metodo_id: number
  temperatura_c: number | null
  tiempo_esterilizacion_min: number | null
  tiempo_secado_min: number | null
  tiempo_desgasificacion_min: number | null // óxido de etileno: dentro del equipo, no es la aireación
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
  numero_ciclo: string | null // contador del equipo (lote.numero_ciclo, migración 0010)
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

// ---------------------------------------------------------------------------
// Pantalla de Esterilización: armar la carga de un equipo y cerrar el ciclo
// * El operador sale de la sesión y los datos del ciclo, del programa elegido.
// ---------------------------------------------------------------------------

// GET /avances/pendientes?etapa_orden=4&equipo_id=: unidades listas para cargar,
// por servicio de origen y material (no ítems sueltos)
export interface PendienteCarga {
  servicio: Servicio
  material: Material
  cantidad: number
}

// Una línea de la carga: cuántas unidades de un material de un servicio
export interface LineaLote {
  servicio_id: number
  material_id: number
  cantidad: number
}

// Lo que la pantalla manda en POST /lotes
export interface NuevoLote {
  equipo_id: number
  programa_id: number
  numero: number // de 1 a 999: el sistema lo propone y el operador puede corregirlo
  lineas: LineaLote[]
}

// Lo que devuelve POST /lotes (201)
export interface LoteCreado {
  id: number
  numero: number
  equipo_id: number
  inicio: string
}

// Lo que la pantalla manda en POST /lotes/{id}/cierre
export interface CierreLote {
  resultado: ResultadoLote
  numero_ciclo?: string // el que imprime el ticket de la máquina (opcional)
  observacion?: string // obligatoria si resultado es 'fallido'
}

// Un lote en curso (resultado null), para la sección "Ciclos en curso"
export interface LoteAbierto {
  id: number
  numero: number
  inicio: string
  equipo: Equipo
  programa: Programa
}
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

// ---------------------------------------------------------------------------
// Catálogos (ABM de servicios y materiales, solo administradores)
// * Vienen de GET /servicios y GET /materiales con ?incluir_inactivos=true.
// ---------------------------------------------------------------------------
export interface ServicioAdmin {
  id: number
  nombre: string
  externo: boolean // centro externo: otro hospital, área programática o sanatorio
  dias_aireacion: number // 0 a 365
  activo: boolean
}

export interface MaterialAdmin {
  id: number
  nombre: string
  codigo: string | null // en mayúsculas y sin espacios
  nombre_alternativo: string | null
  activo: boolean
}

// Respuesta de POST /operadores/{id}/codigo-recuperacion.
// ! Se muestra una sola vez: no se guarda en ningún lado.
export interface CodigoRecuperacion {
  codigo: string
  vence: string // fecha y hora ISO
}

// ---------------------------------------------------------------------------
// Avance de lavado y empaque (RF4). Contrato de POST /avances (schemas/avance.py).
// ---------------------------------------------------------------------------

// 2 = Lavado y secado, 3 = Empaque y rotulación (orden de la etapa, migración 0002)
export type EtapaAvance = 2 | 3

export interface LineaAvance {
  material_id: number
  cantidad: number
  // Obligatorio en Empaque (cada método lleva otro envoltorio); en Lavado no va.
  // Un mismo material puede ir en dos líneas con métodos distintos.
  metodo_id?: number
}

// Método de esterilización (GET /metodos)
export interface Metodo {
  id: number
  nombre: string
}

export interface NuevoAvance {
  etapa_orden: EtapaAvance
  items: LineaAvance[]
  solo_desinfeccion: boolean // solo en Lavado; obliga a escribir observación
  observacion?: string
}

// Lo que devuelve POST /avances (201)
export interface AvanceRegistrado {
  etapa_orden: EtapaAvance
  total_items: number
  solo_desinfeccion: boolean
}

// GET /avances/pendientes?etapa_orden=N: unidades que esperan pasar a esa etapa, por
// servicio de origen y material. La pantalla las suma por material, porque el avance
// toma los ítems más antiguos del material sin mirar el servicio.
export interface Pendiente {
  servicio_id: number
  servicio: string
  material_id: number
  material: string
  cantidad: number
}

// ---------------------------------------------------------------------------
// Tablero de material en curso (RF7 y RF6). Contrato de GET /tablero (schemas/tablero.py).
// * Cada fila es una recepción con algún ítem que todavía no llegó a Entrega.
// * El lote aparece recién desde Esterilización.
// ---------------------------------------------------------------------------

export interface MaterialEnCurso {
  material_id: number
  nombre: string
  codigo: string | null
  etapa_orden: number // 1 a 6, deducida del último evento de cada ítem
  cantidad: number
}

// Último lote de esterilización de ítems de la fila (si hubo reesterilización, el último)
export interface LoteDeFila {
  id: number
  numero: number // se repite: de 1 a 999 y por equipo
  equipo: string
  resultado: ResultadoLote | null
}

export interface FilaTablero {
  recepcion_id: number
  fecha_hora: string
  urgente: boolean
  servicio: { id: number; nombre: string }
  total_items: number
  por_etapa: Record<string, number> // claves "1" a "6": ítems en cada etapa
  materiales: MaterialEnCurso[]
  lotes: LoteDeFila[]
}

export interface FiltrosTablero {
  urgente?: boolean
  lote_ids?: number[]
  externo?: boolean // centros externos (servicio.externo, migración 0010)
}

// ---------------------------------------------------------------------------
// Avisos de material detenido (RF4 y RF7). Contrato de GET /avisos (schemas/aviso.py).
// * Los umbrales son provisorios (backend/app/services/reglas_avisos.py).
// ---------------------------------------------------------------------------

export interface Aviso {
  tipo: 'detenido' | 'listo_para_retirar'
  recepcion_id: number
  servicio: { id: number; nombre: string }
  material: { id: number; nombre: string; codigo: string | null }
  cantidad: number
  etapa_orden: number
  lote: { id: number; numero: number; equipo: string } | null
  desde: string
  minutos_transcurridos: number // calculado en el servidor
  umbral_minutos: number | null // null en "listo para retirar"
  // Solo en "detenido": alta si lleva el doble de su umbral (o el lote falló). Provisorio.
  gravedad: 'alta' | 'media' | null
  motivo: string // texto listo para mostrar
}