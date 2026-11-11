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
}

// Lo que devuelve el back al registrar
export interface RecepcionCreada {
  id: number
  servicio_id: number
  fecha_hora: string
  total_items: number
}