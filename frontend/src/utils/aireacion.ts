import type { Equipo, Servicio } from '../types'

// * La aireación no se guarda: se deduce (ver "Datos que no se guardan" en docs/DER.md).
// * Fin de aireación de un ítem = lote.fin + servicio.dias_aireacion de su servicio de origen.
// * Solo la llevan los métodos con metodo_esterilizacion.requiere_aireacion (migración 0010).

export function llevaAireacion(equipo: Equipo): boolean {
  return equipo.metodo.requiere_aireacion
}

// null si el lote no lleva aireación o todavía no terminó
export function finAireacion(equipo: Equipo, finLote: string | null, servicio: Servicio): string | null {
  if (!llevaAireacion(equipo) || finLote === null) return null

  const fecha = new Date(finLote)
  fecha.setDate(fecha.getDate() + servicio.dias_aireacion)
  return fecha.toISOString()
}

// La aireación del lote termina cuando termina la del último de sus ítems
export function finAireacionLote(equipo: Equipo, finLote: string | null, servicios: Servicio[]): string | null {
  const fines = servicios
    .map((s) => finAireacion(equipo, finLote, s))
    .filter((f): f is string => f !== null)
    .sort()
  return fines.length > 0 ? fines[fines.length - 1] : null
}
