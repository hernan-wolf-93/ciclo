import type { Material, Servicio } from '../types'

// * Mismos servicios que la migración 0004 del back
export const SERVICIOS: Servicio[] = [
  { id: 1, nombre: 'Quirófano' },
  { id: 2, nombre: 'Neonatología' },
  { id: 3, nombre: 'Guardia' },
  { id: 4, nombre: 'Pediatría' },
  { id: 5, nombre: 'Consultorios' },
  { id: 6, nombre: 'Aguilares' },
  { id: 7, nombre: 'Monteros' },
  { id: 8, nombre: 'Otro' },
  { id: 9, nombre: 'Unidad de Terapia Intensiva' },
]

// ? Los materiales todavía no están cargados en el back (la rama de Lobo
// ? solo agrega la columna código). Uso los del cartel del depósito.
export const MATERIALES: Material[] = [
  { id: 1, codigo: 'G', nombre: 'Gasa simple' },
  { id: 2, codigo: 'GD', nombre: 'Gasa doble' },
  { id: 3, codigo: 'P', nombre: 'Ponchito' },
  { id: 4, codigo: 'VP', nombre: 'Venda pediatrica' },
  { id: 5, codigo: 'VT', nombre: 'Venda traumatologica' },
  { id: 6, codigo: 'PMQ', nombre: 'Paño marino quirurgico' },
  { id: 7, codigo: 'VQ', nombre: 'Venda quirofano' },
  { id: 8, codigo: 'AQ', nombre: 'Aposito quirurgico' },
  { id: 9, codigo: 'A', nombre: 'Aposito' },
  { id: 10, codigo: 'PM', nombre: 'Paño marino' },
  { id: 11, codigo: 'G10', nombre: 'Gasa x10 quirofano' },
  { id: 12, codigo: null, nombre: 'Caja cesárea' },
  { id: 13, codigo: null, nombre: 'Equipo de ropa' },
  { id: 14, codigo: null, nombre: 'Bolsa hidrófilo' },
  { id: 15, codigo: null, nombre: 'Caja histerectomía' },
]