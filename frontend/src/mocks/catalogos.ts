import type { Material, Servicio } from '../types'

// * Mismos servicios que la migración 0004 del back.
// * dias_aireacion (migración 0007): 3 por defecto.
// ? Neonatología 10 y Pediatría 7 los confirmó la jefa del servicio, pero en la
// ? base todavía están en 3: el DER los prevé en la migración 0008.
export const SERVICIOS: Servicio[] = [
  { id: 1, nombre: 'Quirófano', dias_aireacion: 3 },
  { id: 2, nombre: 'Neonatología', dias_aireacion: 10 },
  { id: 3, nombre: 'Guardia', dias_aireacion: 3 },
  { id: 4, nombre: 'Pediatría', dias_aireacion: 7 },
  { id: 5, nombre: 'Consultorios', dias_aireacion: 3 },
  { id: 6, nombre: 'Aguilares', dias_aireacion: 3 },
  { id: 7, nombre: 'Monteros', dias_aireacion: 3 },
  { id: 8, nombre: 'Otro', dias_aireacion: 3 },
  { id: 9, nombre: 'Unidad de Terapia Intensiva', dias_aireacion: 3 },
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