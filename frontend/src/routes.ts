// Pantallas de la aplicación. Cada una tiene su área de color (si corresponde).
// Azul (área limpia: empaque) queda definido en index.css para cuando
// se agregue una pantalla de empaque.
export type Area = 'rojo' | 'azul' | 'gris' | 'verde'

export interface Pantalla {
  path: string
  label: string
  area?: Area
  franja?: string
}

export const pantallas: Pantalla[] = [
  { path: '/', label: 'Tablero' },
  {
    path: '/recepcion',
    label: 'Recepción',
    area: 'rojo',
    franja: 'Área sucia: recepción y control',
  },
  {
    path: '/esterilizacion',
    label: 'Esterilización',
    area: 'gris',
    franja: 'Esterilización',
  },
  { path: '/lotes', label: 'Lotes' },
  {
    path: '/entrega',
    label: 'Entrega',
    area: 'verde',
    franja: 'Área verde: entrega por ventanilla',
  },
]
