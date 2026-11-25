import { MATERIALES_OFICIALES, SERVICIOS_OFICIALES } from './catalogoOficial'
import type { EntregaDisponible } from '../types'

// * Material listo para entregar (GET /entregas/disponibles). Datos de prueba: los
// * reemplaza la API de Lobo. Los servicios y materiales salen del catálogo oficial.
// ? El catálogo oficial todavía no tiene códigos: los de acá son de prueba.

// Lotes aprobados con material en Almacén. El N.º de lote se repite entre equipos
// (el 12 está en Autoclave 1 y en Estufa 1): por eso cada fila trae su lote_id.
// * El lote_id crece con el tiempo: un id menor es un lote más antiguo.
const LOTES_APROBADOS: Record<number, { numero: number; equipo: string }> = {
  101: { numero: 12, equipo: 'Autoclave 1' },
  102: { numero: 12, equipo: 'Estufa 1' },
  103: { numero: 11, equipo: 'Óxido de etileno 1' },
  104: { numero: 14, equipo: 'Autoclave 1' },
}

// Busca el servicio y el material por nombre, así los ids coinciden con el catálogo oficial
function fila(
  loteId: number,
  servicio: string,
  material: string,
  codigo: string,
  cantidad: number,
  urgente = false,
): EntregaDisponible {
  const s = SERVICIOS_OFICIALES.find((x) => x.nombre === servicio)
  const m = MATERIALES_OFICIALES.find((x) => x.nombre === material)
  if (!s || !m) throw new Error(`Mock de entregas: no existe "${servicio}" o "${material}" en el catálogo`)

  return {
    lote_id: loteId,
    lote_numero: LOTES_APROBADOS[loteId].numero,
    equipo: LOTES_APROBADOS[loteId].equipo,
    servicio_id: s.id,
    servicio: s.nombre,
    urgente,
    material_id: m.id,
    material: m.nombre,
    codigo,
    cantidad_entregable: cantidad,
  }
}

export const ENTREGAS_DISPONIBLES: EntregaDisponible[] = [
  // Sala 7: las gasas x 10 están en dos lotes distintos (12 y 14 de Autoclave 1)
  fila(101, 'Sala 7', 'Gasas x 10', 'G10', 6),
  fila(104, 'Sala 7', 'Gasas x 10', 'G10', 4, true),
  fila(104, 'Sala 7', 'Set de punción lumbar', 'SPL', 2, true),
  fila(103, 'Sala 7', 'Mangueras de oxígeno', 'MO', 3),

  // UTI
  fila(101, 'UTI', 'Apósito común', 'AC', 5),
  fila(102, 'UTI', 'Instrumental', 'INS', 2),
  fila(103, 'UTI', 'Ambú completo', 'AMB', 1, true),

  // Neonatología
  fila(103, 'Neonatología', 'Cánula CPAP 01', 'CP01', 4, true),
  fila(101, 'Neonatología', 'Mamaderas', 'MAM', 10),
  fila(102, 'Neonatología', 'Pulpitos', 'PUL', 3),

  // Consultorios Externos
  fila(101, 'Consultorios Externos', 'Paños marinos', 'PM', 8),
  fila(102, 'Consultorios Externos', 'Caja de dermatología n.º 1', 'CD1', 1),
]
