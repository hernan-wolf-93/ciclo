// Pantallas de la aplicación. Cada una tiene su área de color (si corresponde).
export type Area = 'rojo' | 'azul' | 'gris' | 'verde'

export interface Pantalla {
  path: string
  label: string
  area?: Area
  franja?: string
  soloAdmin?: boolean // solo la ven los administradores
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
    path: '/lavado',
    label: 'Lavado',
    area: 'rojo',
    franja: 'Área sucia: lavado y secado',
  },
  {
    path: '/empaque',
    label: 'Empaque',
    area: 'azul',
    franja: 'Área limpia: empaque y rotulación',
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
  { path: '/catalogos', label: 'Catálogos', soloAdmin: true },
  { path: '/usuarios', label: 'Usuarios', soloAdmin: true },
]
