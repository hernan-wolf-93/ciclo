import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Badge, Button, Group, Loader, Paper, SegmentedControl, Stack, Table, Text, TextInput, Title } from '@mantine/core'
import { buscarLotes, obtenerTablero } from '../services/tableroService'
import type { FilaTablero, LoteResumen } from '../types'
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

  const numeroLote = comoNumeroDeLote(busqueda)

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
      </Group>

      <Group align="flex-end" gap="lg">
        <div>
          <SegmentedControl
            size="md"
            value={filtro}
            onChange={cambiarFiltro}
            data={[
              { label: 'Todos', value: 'todos' },
              { label: 'Urgentes', value: 'urgentes' },
              // TODO: falta el dato en servicio para saber cuáles son externos (pedido a Lobo)
              // y confirmar con el servicio qué significa: probablemente centros de otras
              // localidades, como Aguilares y Monteros.
              { label: 'Centros externos', value: 'externos', disabled: true },
            ]}
          />
          <Text size="xs" c="dimmed" mt={4}>
            Centros externos: pendiente, falta el dato en el sistema.
          </Text>
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
            <FilaRecepcion key={fila.recepcion_id} fila={fila} />
          ))}
        </Stack>
      )}
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// Una recepción con su recorrido por las 6 etapas
// ---------------------------------------------------------------------------

function FilaRecepcion({ fila }: { fila: FilaTablero }) {
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
