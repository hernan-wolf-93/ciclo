import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Collapse,
  Group,
  Loader,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { buscarLotes, obtenerTablero } from '../services/tableroService'
import { obtenerAvisos } from '../services/avisosService'
import type { Aviso, FilaTablero, LoteResumen } from '../types'
import styles from './Tablero.module.css'

// * Tablero de material en curso (RF7 y RF6). Cada fila es una recepción con algún
// * ítem que todavía no llegó a Entrega. Antes de Esterilización se sigue cada ítem;
// * el N.º de lote aparece recién desde esa etapa. Sin franja de color.

// Etapas y área de cada una: mismas que la migración 0002 (etapa.color)
const ETAPAS = [
  { orden: 1, nombre: 'Recepción', area: 'rojo' },
  { orden: 2, nombre: 'Lavado y secado', area: 'rojo' },
  { orden: 3, nombre: 'Empaque y rotulación', area: 'azul' },
  { orden: 4, nombre: 'Esterilización', area: 'gris' },
  { orden: 5, nombre: 'Almacén estéril', area: 'verde' },
  { orden: 6, nombre: 'Entrega', area: 'verde' },
] as const

const nombreEtapa = (orden: number) => ETAPAS.find((e) => e.orden === orden)?.nombre ?? `Etapa ${orden}`

type Filtro = 'todos' | 'urgentes' | 'externos'

// Marca de una fila del tablero con avisos en el panel "Requieren atención"
interface MarcaAvisos {
  cantidad: number
  color: 'red' | 'orange' | 'green'
}

// Cada cuánto se vuelven a pedir el tablero y los avisos sin recargar la página
const ACTUALIZAR_CADA_MS = 2 * 60 * 1000

// "14:05" (24 h)
const hora = (fecha: Date) => fecha.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

// "22/11 09:40" (24 h)
function diaHora(iso: string) {
  const fecha = new Date(iso)
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const hora = fecha.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
  return `${dia}/${mes} ${hora}`
}

// Para buscar sin importar mayúsculas ni tildes
const normalizar = (texto: string) =>
  texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

// Si lo escrito es un número de 1 a 999, se busca como N.º de lote
function comoNumeroDeLote(texto: string): number | null {
  const limpio = texto.trim()
  if (!/^\d{1,3}$/.test(limpio)) return null
  const numero = Number(limpio)
  return numero >= 1 ? numero : null
}

export default function Tablero() {
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [busqueda, setBusqueda] = useState('')
  const [filas, setFilas] = useState<FilaTablero[]>([])
  const [lotesBuscados, setLotesBuscados] = useState<LoteResumen[] | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [recargas, setRecargas] = useState(0)
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [actualizado, setActualizado] = useState<Date | null>(null)

  const numeroLote = comoNumeroDeLote(busqueda)

  // Avisos de material detenido o listo para retirar (GET /avisos), al entrar y al actualizar.
  // Si fallan, el tablero se sigue mostrando: el panel simplemente no aparece.
  useEffect(() => {
    let vigente = true
    obtenerAvisos()
      .then((lista) => {
        if (!vigente) return
        setAvisos(lista)
        setActualizado(new Date())
      })
      .catch(() => {
        if (vigente) setAvisos([])
      })
    return () => {
      vigente = false
    }
  }, [recargas])

  // Actualización automática: cada 2 minutos, solo mientras la pestaña está a la vista.
  // Al volver a la pestaña, si ya pasó ese tiempo, se actualiza enseguida.
  // No muestra el cargando: los datos se reemplazan sin que la pantalla salte.
  useEffect(() => {
    let ultima = Date.now()
    const actualizar = () => {
      ultima = Date.now()
      setRecargas((n) => n + 1)
    }
    const intervalo = setInterval(() => {
      if (document.visibilityState === 'visible') actualizar()
    }, ACTUALIZAR_CADA_MS)
    const alVolver = () => {
      if (document.visibilityState === 'visible' && Date.now() - ultima >= ACTUALIZAR_CADA_MS) actualizar()
    }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      clearInterval(intervalo)
      document.removeEventListener('visibilitychange', alVolver)
    }
  }, [])

  // Cuántos avisos tiene cada recepción y de qué color va su marca:
  // rojo si alguno es grave, naranja si alguno está detenido, verde si solo hay listos para retirar
  const avisosPorRecepcion = new Map<number, MarcaAvisos>()
  for (const aviso of avisos) {
    const actual = avisosPorRecepcion.get(aviso.recepcion_id) ?? { cantidad: 0, color: 'green' }
    const color =
      actual.color === 'red' || aviso.gravedad === 'alta'
        ? 'red'
        : actual.color === 'orange' || aviso.tipo === 'detenido'
          ? 'orange'
          : 'green'
    avisosPorRecepcion.set(aviso.recepcion_id, { cantidad: actual.cantidad + 1, color })
  }

  // Trae el tablero al entrar, al cambiar el filtro o al buscar un N.º de lote.
  // La espera corta evita pedir una vez por cada tecla.
  useEffect(() => {
    let vigente = true
    const espera = setTimeout(async () => {
      try {
        let lotes: LoteResumen[] | null = null
        if (numeroLote !== null) {
          lotes = await buscarLotes(numeroLote)
          if (lotes.length === 0) {
            if (vigente) {
              setFilas([])
              setLotesBuscados(lotes)
              setError('')
            }
            return
          }
        }
        const datos = await obtenerTablero({
          urgente: filtro === 'urgentes' ? true : undefined,
          externo: filtro === 'externos' ? true : undefined,
          lote_ids: lotes?.map((l) => l.id),
        })
        if (vigente) {
          setFilas(datos)
          setLotesBuscados(lotes)
          setError('')
        }
      } catch {
        if (vigente) setError('No se pudo cargar el tablero. Probá de nuevo.')
      } finally {
        if (vigente) setCargando(false)
      }
    }, 300)

    return () => {
      vigente = false
      clearTimeout(espera)
    }
  }, [filtro, numeroLote, recargas])

  function cambiarFiltro(valor: string) {
    setFiltro(valor as Filtro)
    setCargando(true)
  }

  function cambiarBusqueda(valor: string) {
    // Solo se vuelve a pedir al servidor si cambia el N.º de lote buscado
    if (comoNumeroDeLote(valor) !== numeroLote) setCargando(true)
    setBusqueda(valor)
  }

  // Búsqueda por texto (servicio o material): se filtra lo que ya está cargado
  const texto = numeroLote === null ? normalizar(busqueda.trim()) : ''
  const visibles = texto
    ? filas.filter(
        (f) =>
          normalizar(f.servicio.nombre).includes(texto) ||
          f.materiales.some((m) => normalizar(m.nombre).includes(texto) || normalizar(m.codigo ?? '') === texto),
      )
    : filas

  return (
    <Stack gap="xl" maw={1200}>
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={1}>Tablero</Title>
          <Text c="dimmed">Material en curso por recepción. Lo urgente aparece primero.</Text>
        </div>
        <Stack gap={4} align="flex-end">
          <Button
            size="md"
            variant="default"
            onClick={() => {
              setCargando(true)
              setRecargas((n) => n + 1)
            }}
          >
            Actualizar
          </Button>
          {actualizado && (
            <Text size="xs" c="dimmed">
              Actualizado a las {hora(actualizado)} · se actualiza solo cada 2 min
            </Text>
          )}
        </Stack>
      </Group>

      <PanelAtencion avisos={avisos} />

      <Group align="flex-end" gap="lg">
        <div>
          <SegmentedControl
            size="md"
            value={filtro}
            onChange={cambiarFiltro}
            data={[
              { label: 'Todos', value: 'todos' },
              { label: 'Urgentes', value: 'urgentes' },
              // Hospitales de otras localidades, Área Programática y sanatorios (servicio.externo)
              { label: 'Centros externos', value: 'externos' },
            ]}
          />
        </div>
        <TextInput
          size="md"
          w={360}
          label="Buscar"
          placeholder="N.º de lote, servicio o material"
          value={busqueda}
          onChange={(e) => cambiarBusqueda(e.currentTarget.value)}
        />
      </Group>

      {/* Búsqueda por N.º de lote: el número se repite (es por equipo) */}
      {numeroLote !== null && lotesBuscados && !cargando && (
        <Alert color={lotesBuscados.length === 0 ? 'yellow' : 'blue'} variant="light">
          {lotesBuscados.length === 0 ? (
            <>No hay lotes con el N.º {numeroLote}.</>
          ) : (
            <Group justify="space-between">
              <Text size="sm">
                {lotesBuscados.length === 1 ? 'Lote' : `${lotesBuscados.length} lotes`} N.º {numeroLote}:{' '}
                {lotesBuscados.map((l) => `${l.equipo.nombre} (${diaHora(l.inicio)})`).join(' · ')}.
                {visibles.length === 0 && ' Sus ítems ya no están en curso.'}
              </Text>
              <Button component={Link} to={`/lotes?numero=${numeroLote}`} size="xs" variant="light">
                Ver en Lotes
              </Button>
            </Group>
          )}
        </Alert>
      )}

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      {cargando ? (
        <Group justify="center" p="xl">
          <Loader />
        </Group>
      ) : visibles.length === 0 ? (
        !error && (numeroLote === null || (lotesBuscados?.length ?? 0) === 0) && (
          <Text c="dimmed">
            {busqueda.trim() ? 'No hay material en curso que coincida con la búsqueda.' : 'No hay material en curso.'}
          </Text>
        )
      ) : (
        <Stack gap="md">
          <Text c="dimmed" size="sm">
            {visibles.length} {visibles.length === 1 ? 'recepción en curso' : 'recepciones en curso'}
          </Text>
          {visibles.map((fila) => (
            <FilaRecepcion key={fila.recepcion_id} fila={fila} avisos={avisosPorRecepcion.get(fila.recepcion_id)} />
          ))}
        </Stack>
      )}
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// Una recepción con su recorrido por las 6 etapas
// ---------------------------------------------------------------------------

function FilaRecepcion({
  fila,
  avisos,
}: {
  fila: FilaTablero
  avisos: MarcaAvisos | undefined
}) {
  const [abierta, setAbierta] = useState(false)

  return (
    <Paper withBorder radius="md" p="md" className={fila.urgente ? styles.urgente : undefined}>
      <Group justify="space-between" align="flex-start" mb="sm">
        <div>
          <Group gap="xs">
            {fila.urgente && (
              <Badge color="red" variant="filled">
                Urgente
              </Badge>
            )}
            <Text fw={700} size="lg">
              {fila.servicio.nombre}
            </Text>
            {/* Marca de la fila: tiene avisos en el panel "Requieren atención" (color en avisosPorRecepcion) */}
            {avisos && (
              <Badge color={avisos.color} variant="light">
                ⚠ {avisos.cantidad} {avisos.cantidad === 1 ? 'aviso' : 'avisos'}
              </Badge>
            )}
          </Group>
          <Text c="dimmed" size="sm">
            Recepción N.º {fila.recepcion_id} · {diaHora(fila.fecha_hora)} h · {fila.total_items}{' '}
            {fila.total_items === 1 ? 'ítem' : 'ítems'}
          </Text>
        </div>

        {/* El N.º de lote aparece recién desde Esterilización */}
        <Group gap="xs">
          {fila.lotes.map((lote) => (
            <Badge key={lote.id} size="lg" variant="light" color={lote.resultado === 'fallido' ? 'red' : 'gray'}>
              Lote {String(lote.numero).padStart(2, '0')} · {lote.equipo}
              {lote.resultado === 'fallido' ? ' · fallido' : ''}
            </Badge>
          ))}
        </Group>
      </Group>

      {/* Recorrido: cuántos ítems hay hoy en cada etapa, con el color de su área (RF6) */}
      <div className={styles.recorrido}>
        {ETAPAS.map((etapa) => {
          const cantidad = fila.por_etapa[String(etapa.orden)] ?? 0
          return (
            <div
              key={etapa.orden}
              className={cantidad > 0 ? `${styles.etapa} ${styles.conItems}` : styles.etapa}
              style={{ ['--area' as string]: `var(--${etapa.area})` }}
              title={`${etapa.nombre}: ${cantidad} ${cantidad === 1 ? 'ítem' : 'ítems'}`}
            >
              <span className={styles.nombreEtapa}>{etapa.nombre}</span>
              <span className={styles.cantidad}>{cantidad}</span>
            </div>
          )
        })}
      </div>

      <Button variant="subtle" size="compact-sm" mt="xs" onClick={() => setAbierta((a) => !a)}>
        {abierta ? 'Ocultar materiales' : 'Ver materiales'}
      </Button>

      {abierta && (
        <Table mt="xs" verticalSpacing={4} fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Material</Table.Th>
              <Table.Th>Etapa actual</Table.Th>
              <Table.Th ta="right">Unidades</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {fila.materiales.map((m) => (
              <Table.Tr key={`${m.material_id}-${m.etapa_orden}`}>
                <Table.Td>
                  {m.nombre}
                  {m.codigo ? ` (${m.codigo})` : ''}
                </Table.Td>
                <Table.Td>{nombreEtapa(m.etapa_orden)}</Table.Td>
                <Table.Td ta="right">{m.cantidad}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Paper>
  )
}

// ---------------------------------------------------------------------------
// Panel "Requieren atención": avisos de GET /avisos, ya ordenados por el servidor.
// Rojo = grave (llegó al doble de su umbral o el lote falló); naranja = pasó su umbral.
// Plegable, con resumen y filtros por tipo y por servicio (se filtra en la pantalla).
// TODO (necesitan migración, otra tarjeta): marcar un aviso como visto o resuelto,
// umbrales editables desde la pantalla e historial de avisos.
// ---------------------------------------------------------------------------

type FiltroAviso = 'todos' | 'detenido' | 'listo_para_retirar'

const CLAVE_PLEGADO = 'ciclo_panel_atencion_plegado'

// El estado plegado es una comodidad de cada navegador: si no se puede leer, abierto
function leerPlegado(): boolean {
  try {
    return localStorage.getItem(CLAVE_PLEGADO) === '1'
  } catch {
    return false
  }
}

function guardarPlegado(plegado: boolean) {
  try {
    localStorage.setItem(CLAVE_PLEGADO, plegado ? '1' : '0')
  } catch {
    // sin almacenamiento: se recuerda solo mientras la pantalla está abierta
  }
}

const plural = (n: number, uno: string, varios: string) => `${n} ${n === 1 ? uno : varios}`

function PanelAtencion({ avisos }: { avisos: Aviso[] }) {
  const [plegado, setPlegado] = useState(leerPlegado)
  const [tipo, setTipo] = useState<FiltroAviso>('todos')
  const [servicioId, setServicioId] = useState<string | null>(null)

  if (avisos.length === 0) return null

  const graves = avisos.filter((a) => a.gravedad === 'alta').length
  const medios = avisos.filter((a) => a.gravedad === 'media').length
  const listosTotal = avisos.filter((a) => a.tipo === 'listo_para_retirar').length

  // Servicios que tienen avisos, para el filtro
  const servicios = [...new Map(avisos.map((a) => [a.servicio.id, a.servicio.nombre])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1], 'es'))
    .map(([id, nombre]) => ({ value: String(id), label: nombre }))
  // Si el servicio elegido ya no tiene avisos (tras actualizar), el filtro no se aplica
  const servicioVigente = servicios.some((s) => s.value === servicioId) ? servicioId : null

  const visibles = avisos.filter(
    (a) => (tipo === 'todos' || a.tipo === tipo) && (servicioVigente === null || String(a.servicio.id) === servicioVigente),
  )
  const detenidos = visibles.filter((a) => a.tipo === 'detenido')
  const listos = visibles.filter((a) => a.tipo === 'listo_para_retirar')

  const alternar = () => {
    setPlegado((actual) => {
      guardarPlegado(!actual)
      return !actual
    })
  }

  return (
    <Paper withBorder radius="md" p="md" className={graves > 0 ? styles.panelAtencionGrave : styles.panelAtencion}>
      <Group justify="space-between" wrap="wrap">
        <Group gap="sm">
          <Text fw={700} size="lg">
            Requieren atención ({avisos.length})
          </Text>
          {graves > 0 && (
            <Badge color="red" variant="filled">
              {plural(graves, 'grave', 'graves')}
            </Badge>
          )}
          {medios > 0 && (
            <Badge color="orange" variant="light">
              {plural(medios, 'pasó su tiempo', 'pasaron su tiempo')}
            </Badge>
          )}
          {listosTotal > 0 && (
            <Badge color="green" variant="light">
              {plural(listosTotal, 'listo para retirar', 'listos para retirar')}
            </Badge>
          )}
        </Group>
        <Button variant="subtle" size="compact-md" onClick={alternar} aria-expanded={!plegado}>
          {plegado ? 'Mostrar' : 'Ocultar'}
        </Button>
      </Group>

      <Collapse expanded={!plegado}>
        <Group mt="md" gap="md" align="flex-end">
          <SegmentedControl
            value={tipo}
            onChange={(valor) => setTipo(valor as FiltroAviso)}
            data={[
              { value: 'todos', label: 'Todos' },
              { value: 'detenido', label: 'Detenidos' },
              { value: 'listo_para_retirar', label: 'Listos para retirar' },
            ]}
          />
          <Select
            placeholder="Todos los servicios"
            aria-label="Filtrar los avisos por servicio"
            data={servicios}
            value={servicioVigente}
            onChange={setServicioId}
            clearable
            searchable
            w={260}
          />
        </Group>

        <Stack gap="md" mt="md">
          {detenidos.length > 0 && (
            <GrupoAvisos
              titulo="Material detenido"
              color={detenidos.some((a) => a.gravedad === 'alta') ? 'red' : 'orange'}
              avisos={detenidos}
            />
          )}
          {listos.length > 0 && <GrupoAvisos titulo="Listo para retirar" color="green" avisos={listos} />}
          {visibles.length === 0 && <Text c="dimmed">No hay avisos con ese filtro.</Text>}
        </Stack>
      </Collapse>
    </Paper>
  )
}

function GrupoAvisos({ titulo, color, avisos }: { titulo: string; color: string; avisos: Aviso[] }) {
  const conGravedad = avisos.some((a) => a.gravedad !== null)
  return (
    <div>
      <Badge color={color} variant="filled" mb={6}>
        {titulo}
      </Badge>
      <Table verticalSpacing={4} fz="sm">
        <Table.Thead>
          <Table.Tr>
            {conGravedad && <Table.Th>Gravedad</Table.Th>}
            <Table.Th>Servicio</Table.Th>
            <Table.Th>Material</Table.Th>
            <Table.Th>Etapa</Table.Th>
            <Table.Th>Motivo</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {avisos.map((a) => (
            <Table.Tr
              key={`${a.tipo}-${a.recepcion_id}-${a.material.id}-${a.etapa_orden}-${a.lote?.id ?? 0}`}
              className={a.gravedad === 'alta' ? styles.avisoGrave : undefined}
            >
              {conGravedad && (
                <Table.Td>
                  {a.gravedad === 'alta' ? (
                    <Badge color="red" variant="filled" size="sm">
                      Grave
                    </Badge>
                  ) : (
                    <Badge color="orange" variant="light" size="sm">
                      Pasó su tiempo
                    </Badge>
                  )}
                </Table.Td>
              )}
              <Table.Td>
                {a.servicio.nombre}
                <Text span c="dimmed" fz="xs">
                  {' '}
                  · Recepción N.º {a.recepcion_id}
                </Text>
              </Table.Td>
              <Table.Td>
                {a.material.nombre} × {a.cantidad}
              </Table.Td>
              <Table.Td>{nombreEtapa(a.etapa_orden)}</Table.Td>
              <Table.Td>{a.motivo}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  )
}
