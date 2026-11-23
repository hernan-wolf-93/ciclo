// * Datos de prueba para la pantalla Esterilización: unidades que ya pasaron por
// * Empaque y esperan entrar a un equipo. Vienen agrupadas por servicio de origen,
// * material y método (no son ítems sueltos), como las devolvería
// * GET /avances/pendientes?etapa_orden=4&equipo_id=.
// * Los ids son los de mocks/catalogoOficial.ts (solo materiales con se_recibe === true,
// * y cada material en un servicio que lo tiene en su planilla).
// * Material de sección 'calor' → método 1 (autoclave) o 2 (estufa).
// * Material de sección 'oxido' → método 3 (óxido de etileno).

export interface PendienteDePrueba {
  metodo_id: number
  servicio_id: number
  material_id: number
  cantidad: number
}

export const PENDIENTES_ESTERILIZACION: PendienteDePrueba[] = [
  // Autoclave (calor húmedo)
  { metodo_id: 1, servicio_id: 2, material_id: 6, cantidad: 4 }, // Sala 1 · Instrumental
  { metodo_id: 1, servicio_id: 2, material_id: 4, cantidad: 3 }, // Sala 1 · Camisolines descartables
  { metodo_id: 1, servicio_id: 17, material_id: 6, cantidad: 6 }, // Quirófano · Instrumental
  { metodo_id: 1, servicio_id: 17, material_id: 5, cantidad: 5 }, // Quirófano · Sábanas descartables
  { metodo_id: 1, servicio_id: 16, material_id: 4, cantidad: 2 }, // Neonatología · Camisolines descartables
  { metodo_id: 1, servicio_id: 1, material_id: 7, cantidad: 3 }, // Consultorios Externos · Equipo de curaciones ambulatorio

  // Estufa (calor seco)
  { metodo_id: 2, servicio_id: 14, material_id: 3, cantidad: 4 }, // Guardia Mayor · Gasas vaselinadas
  { metodo_id: 2, servicio_id: 15, material_id: 1, cantidad: 2 }, // UTI · Caja de gasas furacinadas
  { metodo_id: 2, servicio_id: 2, material_id: 3, cantidad: 3 }, // Sala 1 · Gasas vaselinadas

  // Óxido de etileno
  { metodo_id: 3, servicio_id: 16, material_id: 139, cantidad: 3 }, // Neonatología · Cánula CPAP 00
  { metodo_id: 3, servicio_id: 16, material_id: 113, cantidad: 2 }, // Neonatología · Máscaras
  { metodo_id: 3, servicio_id: 15, material_id: 125, cantidad: 1 }, // UTI · Ambú
  { metodo_id: 3, servicio_id: 17, material_id: 119, cantidad: 1 }, // Quirófano · Motor
  { metodo_id: 3, servicio_id: 1, material_id: 104, cantidad: 2 }, // Consultorios Externos · Mallas
]
