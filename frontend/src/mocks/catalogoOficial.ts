import type { Material, Servicio } from '../types'

// * Catálogo OFICIAL de materiales, armado con las planillas de recepción del servicio
// * (versión 06, marzo 2025). Excel de referencia: Materiales_oficiales_Ciclo.xlsx.
// * Es provisorio: lo reemplaza la API cuando Lobo cargue el catálogo (migración 0008/0009).
// ? Los servicios son los 17 de las planillas. Falta confirmar con la jefa si son
// ? servicios distintos y cómo se agrupan. El catálogo del back tiene 9.
// ? Neonatología (10 días) y Guardia Pediátrica (7 días) los confirmó el servicio; el resto, 3.
// ! En las planillas, lo tachado se ENTREGA pero NO se recibe: tiene se_recibe = false
// ! y Recepción no lo muestra. Entrega sí lo va a mostrar.

type Codigo = 'CE' | 'S1' | 'S2' | 'S5' | 'S6' | 'S7' | 'A2' | 'A3' | 'A4' | 'UTPR' | 'GP' | 'SIA' | 'ENF' | 'GM' | 'UTI' | 'NEO' | 'QUI'

const SERVICIOS_BASE: { codigo: Codigo; nombre: string; dias_aireacion: number }[] = [
  { codigo: 'CE', nombre: 'Consultorios Externos', dias_aireacion: 3 },
  { codigo: 'S1', nombre: 'Sala 1', dias_aireacion: 3 },
  { codigo: 'S2', nombre: 'Sala 2', dias_aireacion: 3 },
  { codigo: 'S5', nombre: 'Sala 5', dias_aireacion: 3 },
  { codigo: 'S6', nombre: 'Sala 6', dias_aireacion: 3 },
  { codigo: 'S7', nombre: 'Sala 7', dias_aireacion: 3 },
  { codigo: 'A2', nombre: 'Ala 2', dias_aireacion: 3 },
  { codigo: 'A3', nombre: 'Ala 3', dias_aireacion: 3 },
  { codigo: 'A4', nombre: 'Ala 4 Ginecología', dias_aireacion: 3 },
  { codigo: 'UTPR', nombre: 'U.T.P.R.', dias_aireacion: 3 },
  { codigo: 'GP', nombre: 'Guardia Pediátrica', dias_aireacion: 7 },
  { codigo: 'SIA', nombre: 'SIA', dias_aireacion: 3 },
  { codigo: 'ENF', nombre: 'Enfermería', dias_aireacion: 3 },
  { codigo: 'GM', nombre: 'Guardia Mayor', dias_aireacion: 3 },
  { codigo: 'UTI', nombre: 'UTI', dias_aireacion: 3 },
  { codigo: 'NEO', nombre: 'Neonatología', dias_aireacion: 10 },
  { codigo: 'QUI', nombre: 'Quirófano', dias_aireacion: 3 },
]

export const SERVICIOS_OFICIALES: Servicio[] = SERVICIOS_BASE.map((s, i) => ({
  id: i + 1,
  nombre: s.nombre,
  dias_aireacion: s.dias_aireacion,
}))

// Servicios que comparten la lista básica de las planillas
const ESTANDAR: Codigo[] = ['S1', 'S2', 'S5', 'S6', 'S7', 'A2', 'A3', 'A4', 'UTPR', 'GP', 'SIA', 'ENF']

type Seccion = 'calor' | 'oxido'

// Cada grupo: sección, si se recibe, en qué servicios aparece y los nombres de los materiales
const GRUPOS: [Seccion, boolean, Codigo[], string[]][] = [
  ['calor', true, [...ESTANDAR, 'CE', 'GM', 'UTI', 'QUI'], [
    'Caja de gasas furacinadas',
    'Compresas descartables',
  ]],
  ['calor', true, [...ESTANDAR, 'GM', 'UTI'], [
    'Gasas vaselinadas',
  ]],
  ['calor', true, [...ESTANDAR, 'CE', 'GM', 'UTI', 'NEO', 'QUI'], [
    'Camisolines descartables',
    'Sábanas descartables',
    'Instrumental',
  ]],
  ['calor', true, [...ESTANDAR, 'CE', 'GM', 'UTI'], [
    'Equipo de curaciones ambulatorio',
  ]],
  ['calor', true, [...ESTANDAR, 'CE', 'GM', 'UTI', 'NEO'], [
    'Caja de cirugía hasta 20 p.',
  ]],
  ['calor', true, [...ESTANDAR, 'NEO'], [
    'Set de canalización',
  ]],
  ['calor', true, [...ESTANDAR, 'CE', 'NEO'], [
    'Tambores',
  ]],
  ['calor', true, ['S6', 'QUI'], [
    'Equipos descartables',
  ]],
  ['calor', true, ['CE'], [
    'Instrumental odontológico',
    'Caja de dermatología n.º 1',
    'Caja de dermatología n.º 2',
    'Caja de dermatología n.º 3',
    'Caja de dermatología n.º 4',
    'Caja de dermatología n.º 5',
    'Caja de dermatología n.º 6',
    'Lápiz de electrobisturí',
    'Bolsa de hidrófilo Monteros',
    'Bolsa de área operativa Concep.',
  ]],
  ['calor', true, ['S7'], [
    'Set de punción lumbar',
  ]],
  ['calor', true, ['S6'], [
    'Caja de cirugía hasta 50 p.',
    'Caja de ortopedia',
    'Guías',
  ]],
  ['calor', true, ['A2', 'A3', 'A4', 'UTPR'], [
    'Equipo de ropa de parto',
    'Caja de U.T.P.R.',
  ]],
  ['calor', true, ['GM', 'UTI'], [
    'Set de punción',
    'Set de vía central',
  ]],
  ['calor', true, ['QUI'], [
    'Equipos de ropa',
  ]],
  ['calor', true, ['NEO'], [
    'Mamaderas',
    'Tapas',
    'Tetinas',
    'Compresas de hemocultivo',
    'Compresas de urocultivo',
    'Compresas para llave',
    'Compresas para lactario',
    'Compresas de tela',
    'Sábanas de tela',
    'Nidos',
    'Kit percutáneo',
    'Kit quirófano',
    'Kit prematuro',
    'Tupper para leche',
    'Botellas',
    'Canalización n.º 1',
    'Canalización n.º 2',
    'Canalización n.º 3',
    'Canalización n.º 4',
    'Pulpitos',
  ]],
  ['calor', false, [...ESTANDAR, 'CE', 'GM', 'UTI'], [
    'Torundas',
    'Gasas x 5',
    'Gasas dobles',
    'Paños marinos',
  ]],
  ['calor', false, ['CE', 'S7', 'GP', 'SIA', 'ENF', 'NEO'], [
    'Ponchitos',
  ]],
  ['calor', false, [...ESTANDAR, 'CE', 'UTI'], [
    'Gasas x 10',
  ]],
  ['calor', false, [...ESTANDAR, 'CE'], [
    'Gasas VP',
  ]],
  ['calor', false, [...ESTANDAR, 'CE', 'GM', 'UTI', 'NEO', 'QUI'], [
    'Apósito común',
  ]],
  ['calor', false, ['CE', 'A2', 'A4', 'UTPR', 'ENF'], [
    'Apósito s/parto',
  ]],
  ['calor', false, ['CE', 'S7', 'GP', 'SIA', 'ENF'], [
    'Vendas pediátricas',
  ]],
  ['calor', false, [...ESTANDAR, 'CE', 'GM', 'UTI', 'QUI'], [
    'Vendas traumatológicas',
    'Vendas torácicas',
  ]],
  ['calor', false, ['A2', 'A3', 'A4', 'UTPR'], [
    'Bolsa de parto',
  ]],
  ['calor', false, [...ESTANDAR, 'CE', 'GM', 'UTI', 'NEO'], [
    'Hilos 100 x u.',
    'Hilos 70 x u.',
    'Hilos 40 x u.',
    'Hilos 30 x u.',
  ]],
  ['calor', false, ['QUI'], [
    'Tira de gasa',
    'Apósitos quirúrgicos',
    'Vendas quirófano',
    'Hilos 100 paq. x unid.',
    'Hilos 70 paq. x unid.',
    'Hilos 40 paq. x unid.',
    'Hilos 30 paq. x unid.',
    'Paq. Quirófano (2G x 10)',
    'Compresa de gasa x unidad',
  ]],
  ['oxido', false, [...ESTANDAR, 'CE', 'GM', 'UTI'], [
    'Tanzas x unidad',
  ]],
  ['oxido', false, ['QUI'], [
    'Tanzas 0,25',
    'Tanzas 0,40',
  ]],
  ['oxido', true, ['CE'], [
    'Equipo de punción 4 p.',
    'Set de punción 3 p.',
    'Agujas de punción 3 p.',
    'Bolsa de filtro',
    'Aguja de punción medular',
    'Filtro de glóbulos rojos',
    'Filtro de plaquetas',
    'Set de traqueotomía percutánea',
    'Introductor de cánula n.º 7',
    'Introductor de cánula n.º 8',
    'Dilatadores urología',
    'Guía urología',
    'Agujas p/ Slim',
    'Cable',
    'Punzón',
    'Catéter doble lumen p/ hemodiálisis',
    'Catéter',
    'Dilatador',
    'Set de agujas',
    'Jeringa de AMEU completa',
    'AMEU',
    'AMEU común',
    'AMEU p/ biopsia',
    'Tupper',
  ]],
  ['oxido', true, ['CE', 'S5'], [
    'Mallas',
  ]],
  ['oxido', true, ['S7'], [
    'Tubos endotraqueales',
    'Micro nebulizador',
  ]],
  ['oxido', true, ['S7', 'NEO'], [
    'Mangueras de oxígeno',
    'Circuito de alto flujo',
    'Cánula de alto flujo',
    'Cánula infantil',
    'Cánula neonatal',
  ]],
  ['oxido', true, ['S7', 'UTI'], [
    'Mangueras de aspiración',
  ]],
  ['oxido', true, ['S7', 'UTI', 'NEO'], [
    'Máscaras',
    'Carcasas',
  ]],
  ['oxido', true, ['S6'], [
    'Sierra oscilante (con llaves y sierras)',
    'Set de punción ósea',
    'Agujas',
  ]],
  ['oxido', true, ['S6', 'GM', 'QUI'], [
    'Clavijas',
    'Motor',
  ]],
  ['oxido', true, ['S6', 'QUI'], [
    'Maquitas con cable',
    'Maquitas con baterías',
    'Instrumental (óxido de etileno)',
  ]],
  ['oxido', true, ['GM', 'UTI'], [
    'Guía de intubación',
  ]],
  ['oxido', true, ['GM'], [
    'Cánula de Mayo',
  ]],
  ['oxido', true, ['UTI'], [
    'Ambú',
    'Ambú completo',
    'Set de aspiración',
    'Gomas NBZ',
    'Cánulas CPAP',
  ]],
  ['oxido', true, ['NEO'], [
    'Gomas cortas',
    'Gomas largas',
    'Ambú prematuro',
    'Cánula nasal',
    'Tercer trans',
    'Adaptadores',
    'Mandriles',
    'Sábanas plásticas',
    'Vasos CPAP',
    'Cánula CPAP 00',
    'Cánula CPAP 01',
    'Cánula CPAP 02',
    'Cánula CPAP 03',
    'Circuito CPAP',
    'Circuito HALO',
    'Mangueras de incubadora',
    'Set de ARM',
    'Set de ARM alta frecuencia',
    'Sensor de flujo',
    'Snorkel',
    'Neo Puff',
    'Sistema humidificador',
    'Domos',
  ]],
  ['oxido', true, ['QUI'], [
    'Lápiz de electrobisturí',
    'Gomas aspirativas',
    'Cánulas de aspiración',
    'Drenaje tubular',
    'Bolsas rojas',
    'Sierra y hojas (marciano)',
    'Laparoscopia: Cable de hook',
    'Laparoscopia: Fibra óptica',
    'Laparoscopia: Manguera de neumoperitoneo',
    'Laparoscopia: Óptica',
    'Laparoscopia: Aguja de Veress',
    'Laparoscopia: Trocar umbilical de 10 mm',
    'Laparoscopia: Trocar de 10 mm con punzón',
    'Laparoscopia: Trocar de 5 mm con punzón',
    'Laparoscopia: Reductor',
    'Laparoscopia: Tijera',
    'Laparoscopia: Graspin',
    'Laparoscopia: Merilan',
    'Laparoscopia: Pinza cocodrilo',
    'Laparoscopia: Clipadora',
    'Laparoscopia: Cánula de aspiración (laparoscopia)',
    'Laparoscopia: Mangas',
  ]],
]

// Se arma la lista plana de materiales y, aparte, qué materiales tiene cada servicio
export const MATERIALES_OFICIALES: (Material & { seccion: Seccion; se_recibe: boolean })[] = []
export const MATERIALES_POR_SERVICIO: Record<number, number[]> = {}

for (const [seccion, se_recibe, codigos, nombres] of GRUPOS) {
  for (const nombre of nombres) {
    const id = MATERIALES_OFICIALES.length + 1
    MATERIALES_OFICIALES.push({ id, nombre, codigo: null, seccion, se_recibe })
    for (const codigo of codigos) {
      const servicioId = SERVICIOS_BASE.findIndex((s) => s.codigo === codigo) + 1
      MATERIALES_POR_SERVICIO[servicioId] = [...(MATERIALES_POR_SERVICIO[servicioId] ?? []), id]
    }
  }
}