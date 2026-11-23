import type { Material, Servicio } from '../types'

// * Los primeros 9 servicios de la base, con los nombres y datos de la migración 0010
// * (docs/RESPUESTAS-SERVICIO.md). "Otro" quedó inactivo en la base.
export const SERVICIOS: Servicio[] = [
  { id: 1, nombre: 'Quirófano', dias_aireacion: 3, externo: false },
  { id: 2, nombre: 'Neonatología', dias_aireacion: 10, externo: false },
  { id: 3, nombre: 'Guardia Mayor', dias_aireacion: 3, externo: false },
  { id: 4, nombre: 'Pediatría', dias_aireacion: 7, externo: false },
  { id: 5, nombre: 'Consultorios Externos', dias_aireacion: 3, externo: false },
  { id: 6, nombre: 'Aguilares', dias_aireacion: 3, externo: true },
  { id: 7, nombre: 'Monteros', dias_aireacion: 3, externo: true },
  { id: 8, nombre: 'Otro', dias_aireacion: 3, externo: false },
  { id: 9, nombre: 'Unidad de Terapia Intensiva', dias_aireacion: 3, externo: false },
]

// ? Los materiales todavía no están cargados en el back (la rama de Lobo
// ? solo agrega la columna código). Uso los del cartel del depósito.
export const MATERIALES: Material[] = [
  { id: 1, codigo: 'G', nombre: 'Gasa simple' },
  { id: 2, codigo: 'GD', nombre: 'Gasa doble' },
  { id: 3, codigo: 'P', nombre: 'Ponchito' },
  { id: 4, codigo: 'VP', nombre: 'Venda pediátrica' },
  { id: 5, codigo: 'VT', nombre: 'Venda traumatológica' },
  { id: 6, codigo: 'PMQ', nombre: 'Paño marino quirúrgico' },
  { id: 7, codigo: 'VQ', nombre: 'Venda quirófano' },
  { id: 8, codigo: 'AQ', nombre: 'Apósito quirúrgico' },
  { id: 9, codigo: 'A', nombre: 'Apósito' },
  { id: 10, codigo: 'PM', nombre: 'Paño marino' },
  { id: 11, codigo: 'G10', nombre: 'Gasa x10 quirófano' },
  { id: 12, codigo: null, nombre: 'Caja cesárea' },
  { id: 13, codigo: null, nombre: 'Equipo de ropa' },
  { id: 14, codigo: null, nombre: 'Bolsa hidrófilo' },
  { id: 15, codigo: null, nombre: 'Caja histerectomía' },
]