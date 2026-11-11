import { useEffect, useRef, useState } from 'react'
import { Alert, Badge, Button, Group, Loader, Paper, SimpleGrid, Stack, Table, Text, TextInput, Timeline, Title } from '@mantine/core'
import { obtenerLote, obtenerLotes } from '../services/lotesService'
import type { EstadoLote, ItemDelLote, LoteDetalle, LoteResumen, ResultadoCiclo } from '../types'
import styles from './Lotes.module.css'

// ---------------------------------------------------------------------------
// Formatos
// ---------------------------------------------------------------------------

// "12/11/2026 14:05" (siempre en 24 h)
function fechaHora(iso: string) {
  const fecha = new Date(iso)
  const dia = fecha.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  return `${dia} ${hora(iso)}`
}

// "06/11 14:05" para la línea de tiempo (a mano: sin año, es-AR no respeta el 2-digit del día)
function diaHora(iso: string) {
  const fecha = new Date(iso)
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  return `${dia}/${mes} ${hora(iso)}`
}

function hora(iso: string) {
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
}

// ! El número de lote va del 01 al 999 y se reinicia: lo mostramos con dos cifras
const numeroLote = (n: number) => String(n).padStart(2, '0')

// ---------------------------------------------------------------------------
// Estado del lote: no se guarda, se deduce
// ---------------------------------------------------------------------------

const ESTADOS: Record<EstadoLote, { texto: string; color: string }> = {
  en_curso: { texto: 'En curso', color: 'blue' },
  en_aireacion: { texto: 'En aireación', color: 'orange' },
  aprobado: { texto: 'Aprobado', color: 'green' },
  fallido: { texto: 'Fallido', color: 'red' },
}

function deducirEstado(
  fin: string | null,
  resultado: ResultadoCiclo | null,
  aireacionFin: string | null, // la mayor de sus ítems
  ahora: number,
): EstadoLote {
  // Sin fin o sin resultado del ticket, el ciclo todavía no terminó
  if (fin === null || resultado === null) return 'en_curso'
  if (resultado === 'fallido') return 'fallido'
  // Sigue en aireación mientras algún ítem no la haya cumplido
  if (aireacionFin !== null && new Date(aireacionFin).getTime() > ahora) return 'en_aireacion'
  return 'aprobado'
}

function mayorAireacion(items: ItemDelLote[]): string | null {
  const fines = items.map((i) => i.aireacion_fin).filter((f): f is string => f !== null).sort()
  return fines.length > 0 ? fines[fines.length - 1] : null
}

// ---------------------------------------------------------------------------
// Pantalla
// ---------------------------------------------------------------------------

export default function Lotes() {
  const [busqueda, setBusqueda] = useState('')
  const [lotes, setLotes] = useState<LoteResumen[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  const [detalle, setDetalle] = useState<LoteDetalle | null>(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)

  // Hora de referencia para saber si la aireación ya se cumplió
  const [ahora] = useState(() => Date.now())

  // Para bajar hasta el detalle cuando se elige un lote
  const detalleRef = useRef<HTMLDivElement>(null)

  // Cada vez que cambia la búsqueda pedimos la lista (por ahora, al mock)
  useEffect(() => {
    // Si el operador sigue escribiendo, descartamos la respuesta vieja
    let vigente = true
    const numero = busqueda === '' ? undefined : Number(busqueda)

    obtenerLotes(numero)
      .then((resultado) => {
        if (vigente) setLotes(resultado)
      })
      .catch(() => {
        if (vigente) setError('No se pudo cargar la lista de lotes. Probá de nuevo.')
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })

    return () => {
      vigente = false
    }
  }, [busqueda])

  function cambiarBusqueda(valor: string) {
    // Solo números, como mucho 3 cifras (01 a 999)
    const limpio = valor.replace(/\D/g, '').slice(0, 3)
    if (limpio === busqueda) return
    setBusqueda(limpio)
    setCargando(true)
    setError('')
  }

  async function seleccionar(id: number) {
    setCargandoDetalle(true)
    setError('')

    try {
      setDetalle(await obtenerLote(id))
      requestAnimationFrame(() => detalleRef.current?.scrollIntoView({ behavior: 'smooth' }))
    } catch {
      setError('No se pudo cargar el detalle del lote. Probá de nuevo.')
    } finally {
      setCargandoDetalle(false)
    }
  }

  return (
    <Stack gap="xl" maw={1100}>
      <Title order={1}>Lotes</Title>

      {/* Búsqueda por número de lote */}
      <Group align="flex-end">
        <TextInput
          size="lg"
          w={240}
          label="Buscar por N.º de lote"
          placeholder="Ej: 12"
          inputMode="numeric"
          value={busqueda}
          onChange={(e) => cambiarBusqueda(e.currentTarget.value)}
        />
        {busqueda !== '' && (
          <Button size="lg" variant="default" onClick={() => cambiarBusqueda('')}>
            Ver todos
          </Button>
        )}
      </Group>

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      {/* Lista de lotes */}
      <Paper withBorder radius="md" p="md">
        {cargando ? (
          <Group justify="center" p="lg">
            <Loader />
          </Group>
        ) : lotes.length === 0 ? (
          <Text c="dimmed">
            {busqueda === '' ? 'Todavía no hay lotes.' : `No hay lotes con el N.º ${numeroLote(Number(busqueda))}.`}
          </Text>
        ) : (
          <>
            {/* El número se repite: si hay varios, la fecha dice cuál es cuál */}
            {busqueda !== '' && lotes.length > 1 && (
              <Text mb="sm" c="dimmed">
                Hay {lotes.length} lotes con el N.º {numeroLote(Number(busqueda))}. Fijate la fecha para elegir.
              </Text>
            )}

            <Table.ScrollContainer minWidth={600}>
              <Table highlightOnHover verticalSpacing="sm" fz="md">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>N.º</Table.Th>
                    <Table.Th>Equipo</Table.Th>
                    <Table.Th>Método</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Resultado</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {lotes.map((l) => {
                    const estado = ESTADOS[deducirEstado(l.fin, l.resultado, l.aireacion_fin, ahora)]
                    const elegido = detalle?.id === l.id

                    return (
                      <Table.Tr
                        key={l.id}
                        className={elegido ? `${styles.fila} ${styles.elegida}` : styles.fila}
                        tabIndex={0}
                        aria-selected={elegido}
                        onClick={() => seleccionar(l.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') seleccionar(l.id)
                        }}
                      >
                        <Table.Td fw={700}>{numeroLote(l.numero)}</Table.Td>
                        <Table.Td>{l.equipo.nombre}</Table.Td>
                        {/* El método del lote sale de su equipo */}
                        <Table.Td>{l.equipo.metodo.nombre}</Table.Td>
                        <Table.Td>{fechaHora(l.inicio)}</Table.Td>
                        <Table.Td>
                          <Badge size="lg" variant="light" color={estado.color}>
                            {estado.texto}
                          </Badge>
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </>
        )}
      </Paper>

      {/* Detalle del lote elegido */}
      {/* Mientras carga otro lote dejamos el anterior a la vista (atenuado), así la página no salta */}
      <div ref={detalleRef} className={cargandoDetalle ? styles.cargando : undefined}>
        {detalle ? (
          <DetalleLote lote={detalle} ahora={ahora} onVerLote={seleccionar} />
        ) : cargandoDetalle ? (
          <Group justify="center" p="lg">
            <Loader />
          </Group>
        ) : (
          !cargando &&
          lotes.length > 0 && <Text c="dimmed">Tocá un lote de la lista para ver su detalle.</Text>
        )}
      </div>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// Detalle
// ---------------------------------------------------------------------------

interface DetalleLoteProps {
  lote: LoteDetalle
  ahora: number
  onVerLote: (id: number) => void
}

function DetalleLote({ lote, ahora, onVerLote }: DetalleLoteProps) {
  const estado = ESTADOS[deducirEstado(lote.fin, lote.ciclo?.resultado ?? null, mayorAireacion(lote.items), ahora)]
  const { ciclo, reesterilizacion, reemplaza_a } = lote

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>
          Lote N.º {numeroLote(lote.numero)}{' '}
          <Text span c="dimmed" fz="lg" fw={400}>
            del {fechaHora(lote.inicio)}
          </Text>
        </Title>
        <Badge size="xl" variant="light" color={estado.color}>
          {estado.texto}
        </Badge>
      </Group>

      {/* Reesterilización: este lote falló y su material pasó a otro */}
      {reesterilizacion && (
        <Alert color="red" variant="light" title="Lote fallido: el material se volvió a esterilizar">
          <Text>Motivo: {reesterilizacion.motivo}</Text>
          <Text>Lote nuevo: N.º {numeroLote(reesterilizacion.lote_nuevo_numero)}</Text>
          <Button mt="sm" color="red" variant="light" onClick={() => onVerLote(reesterilizacion.lote_nuevo_id)}>
            Ver lote N.º {numeroLote(reesterilizacion.lote_nuevo_numero)}
          </Button>
        </Alert>
      )}

      {/* Y al revés: este es el lote de reemplazo de uno que falló */}
      {reemplaza_a && (
        <Alert color="blue" variant="light" title={`Reemplaza al lote N.º ${numeroLote(reemplaza_a.numero)}, que falló`}>
          <Button color="blue" variant="light" onClick={() => onVerLote(reemplaza_a.id)}>
            Ver lote N.º {numeroLote(reemplaza_a.numero)}
          </Button>
        </Alert>
      )}

      <Paper withBorder radius="md" p="md">
        <Text fw={700} size="lg" mb="sm">
          Datos del lote
        </Text>
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="md">
          <Dato etiqueta="Equipo" valor={lote.equipo.nombre} />
          <Dato etiqueta="Método" valor={lote.equipo.metodo.nombre} />
          <Dato etiqueta="Programa" valor={lote.programa.nombre} />
          <Dato etiqueta="Operador" valor={`N.º ${lote.operador.numero_operador}`} />
          <Dato etiqueta="Inicio" valor={fechaHora(lote.inicio)} />
          <Dato etiqueta="Fin" valor={lote.fin ? fechaHora(lote.fin) : 'En curso'} />
        </SimpleGrid>
      </Paper>

      {/* ! Provisorio: falta confirmar con el servicio qué datos trae el ticket */}
      <Paper withBorder radius="md" p="md">
        <Text fw={700} size="lg" mb="sm">
          Datos del ciclo
        </Text>
        {ciclo ? (
          <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
            <Dato etiqueta="N.º de ciclo (ticket)" valor={ciclo.numero_ciclo} />
            <Dato etiqueta="Temperatura" valor={ciclo.temperatura_c !== null ? `${ciclo.temperatura_c} °C` : '—'} />
            <Dato etiqueta="Tiempo" valor={ciclo.tiempo_min !== null ? `${ciclo.tiempo_min} min` : '—'} />
            <Dato
              etiqueta="Resultado"
              valor={ciclo.resultado ? ESTADOS[ciclo.resultado].texto : 'Pendiente'}
            />
          </SimpleGrid>
        ) : (
          <Text c="dimmed">Todavía no se cargó el ticket del equipo.</Text>
        )}
      </Paper>

      <section>
        <Text fw={700} size="lg" mb="sm">
          Materiales del lote ({lote.items.length})
        </Text>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          {lote.items.map((i) => (
            <ItemConHistorial key={i.id} item={i} lote={lote} ahora={ahora} />
          ))}
        </SimpleGrid>
      </section>
    </Stack>
  )
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <Text size="sm" c="dimmed">
        {etiqueta}
      </Text>
      <Text fw={700}>{valor}</Text>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Un ítem con su línea de tiempo (el historial es del ítem, no del lote)
// ---------------------------------------------------------------------------

interface ItemConHistorialProps {
  item: ItemDelLote
  lote: LoteDetalle
  ahora: number
}

function ItemConHistorial({ item, lote, ahora }: ItemConHistorialProps) {
  // Ordenados por hora: la API no tiene por qué devolverlos en orden
  const eventos = [...item.eventos].sort((a, b) => a.fecha_hora.localeCompare(b.fecha_hora))
  // La etapa actual no se guarda: es la del último evento
  const ultimo = eventos.length > 0 ? eventos[eventos.length - 1] : null

  return (
    <Paper withBorder radius="md" p="md">
      <Group justify="space-between" align="flex-start" mb="xs">
        <div>
          <Text fw={700} size="lg">
            {item.material.nombre}
            {item.material.codigo && (
              <Text span c="dimmed" fw={400}>
                {' '}
                ({item.material.codigo})
              </Text>
            )}
          </Text>
          <Text c="dimmed">Origen: {item.servicio.nombre}</Text>
        </div>
        <Badge size="lg" variant="outline" color="gray">
          {ultimo ? ultimo.etapa.nombre : 'Sin eventos'}
        </Badge>
      </Group>

      <Aireacion item={item} lote={lote} ahora={ahora} />

      {/* El ítem pasó por este lote fallido, pero hoy está en el de reemplazo */}
      {lote.reesterilizacion && item.lote_id !== lote.id && (
        <Text c="red" fw={500} mb="xs">
          Reesterilizado en el lote N.º {numeroLote(lote.reesterilizacion.lote_nuevo_numero)}
        </Text>
      )}

      <Timeline active={eventos.length - 1} bulletSize={18} lineWidth={2} mt="md" className={styles.historial}>
        {eventos.map((e) => (
          <Timeline.Item key={e.id} title={e.etapa.nombre}>
            <Text size="sm" c="dimmed">
              {diaHora(e.fecha_hora)} h · Operador N.º {e.operador.numero_operador}
            </Text>
          </Timeline.Item>
        ))}
      </Timeline>
    </Paper>
  )
}

// ! Provisorio: la aireación es por ítem y sus días dependen del servicio de origen
function Aireacion({ item, lote, ahora }: ItemConHistorialProps) {
  if (item.aireacion_fin === null || lote.fin === null) return null

  const fin = new Date(item.aireacion_fin).getTime()
  const dias = Math.round((fin - new Date(lote.fin).getTime()) / 86_400_000)
  const cumplida = fin <= ahora

  return (
    <Text c={cumplida ? 'green' : 'orange'} fw={500} mb="xs">
      {cumplida
        ? `Aireación cumplida (${dias} días) el ${fechaHora(item.aireacion_fin)} h`
        : `En aireación hasta el ${fechaHora(item.aireacion_fin)} h (${dias} días)`}
    </Text>
  )
}
