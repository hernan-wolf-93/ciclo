import { useEffect, useState } from 'react'
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import { obtenerServicios } from '../services/recepcionService'
import { esLoteCambiado, mensajeDeError, obtenerDisponibles, registrarEntrega } from '../services/entregaService'
import type { FiltrosEntrega } from '../services/entregaService'
import type { EntregaDisponible, Servicio } from '../types'

// ---------------------------------------------------------------------------
// Formatos y claves
// ---------------------------------------------------------------------------

// "1 unidad", "3 unidades"
const unidades = (n: number) => `${n} ${n === 1 ? 'unidad' : 'unidades'}`

// Clave de cada fila: un material de un lote. Ej: "101-37"
// * Es el par que no se puede repetir en dos líneas de la entrega.
const clave = (f: EntregaDisponible) => `${f.lote_id}-${f.material_id}`

// Filtros tal como se mandan a la API (sin espacios de más y sin campos vacíos)
function armarFiltros(servicioId: string | null, loteNumero: string | number, q: string): FiltrosEntrega {
  return {
    servicioId: servicioId === null ? undefined : Number(servicioId),
    loteNumero: typeof loteNumero === 'number' ? loteNumero : undefined,
    q: q.trim() || undefined,
  }
}

// ---------------------------------------------------------------------------
// Pantalla
// ---------------------------------------------------------------------------

export default function Entrega() {
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [servicioId, setServicioId] = useState<string | null>(null) // el Select trabaja con texto

  // Filtros de "2. Buscar"
  const [loteNumero, setLoteNumero] = useState<string | number>('')
  const [q, setQ] = useState('')

  // * Lo que llega de la API, junto con los filtros que se usaron para pedirlo.
  // * Solo se muestra si coinciden con los filtros actuales: así no se mezclan
  // * respuestas viejas si el operador escribe rápido o cambia de servicio.
  const [resultadosDe, setResultadosDe] = useState<{ filtros: string; filas: EntregaDisponible[] } | null>(null)
  const [version, setVersion] = useState(0) // se suma 1 para volver a pedir la lista

  // * Lo elegido, por clave, CON los datos de la fila: el modal puede listarlo
  // * aunque un filtro la oculte. Solo guardamos las que tienen 1 o más.
  const [seleccion, setSeleccion] = useState<Record<string, { fila: EntregaDisponible; cantidad: number }>>({})

  // 4. Quién retira
  const [retira, setRetira] = useState('')
  const [observacion, setObservacion] = useState('')

  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('') // confirmación en verde al registrar

  // Modal de confirmación
  const [confirmando, setConfirmando] = useState(false) // modal abierto
  const [errorModal, setErrorModal] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Al entrar a la pantalla traemos los servicios
  useEffect(() => {
    obtenerServicios()
      .then(setServicios)
      .catch(() => setError('No se pudieron cargar los servicios. Probá de nuevo.'))
  }, [])

  // Trae el material entregable al elegir el servicio, al escribir en los filtros o
  // después de registrar. La espera corta evita pedir una vez por cada tecla.
  useEffect(() => {
    if (servicioId === null) return

    let vigente = true
    const filtros = armarFiltros(servicioId, loteNumero, q)

    const espera = setTimeout(async () => {
      try {
        const filas = await obtenerDisponibles(filtros)
        if (!vigente) return

        setResultadosDe({ filtros: JSON.stringify(filtros), filas })

        // * Actualizamos lo elegido con los datos nuevos, sin pasar de lo entregable.
        // * Si la búsqueda no tiene filtros, trae todo el servicio: lo elegido que ya
        // * no aparece dejó de estar disponible y se saca.
        const sinFiltros = filtros.loteNumero === undefined && filtros.q === undefined
        setSeleccion((anteriores) => {
          const copia: typeof anteriores = {}
          for (const [k, elegido] of Object.entries(anteriores)) {
            const nueva = filas.find((f) => clave(f) === k)
            if (!nueva) {
              if (!sinFiltros) copia[k] = elegido
              continue
            }
            const cantidad = Math.min(elegido.cantidad, nueva.cantidad_entregable)
            if (cantidad > 0) copia[k] = { fila: nueva, cantidad }
          }
          return copia
        })
      } catch {
        if (vigente) setError('No se pudo cargar el material para entregar. Probá de nuevo.')
      }
    }, 300)

    return () => {
      vigente = false
      clearTimeout(espera)
    }
  }, [servicioId, loteNumero, q, version])

  // Solo usamos lo que llegó si es de los filtros actuales
  const filtrosActuales = JSON.stringify(armarFiltros(servicioId, loteNumero, q))
  const llegaron = resultadosDe?.filtros === filtrosActuales
  const filas = llegaron ? resultadosDe.filas : []

  const servicio = servicios.find((s) => String(s.id) === servicioId)
  const elegidos = Object.values(seleccion)
  const totalUnidades = elegidos.reduce((suma, e) => suma + e.cantidad, 0)

  // Al cambiar de servicio borramos lo elegido (una entrega es de UN solo servicio)
  function elegirServicio(valor: string | null) {
    setServicioId(valor)
    setSeleccion({})
    setError('')
  }

  function limpiarFiltros() {
    setLoteNumero('')
    setQ('')
  }

  // Suma o resta unidades de una fila (diferencia = +1 o -1), sin pasar de lo entregable
  function cambiarCantidad(f: EntregaDisponible, diferencia: number) {
    setError('')
    setSeleccion((anteriores) => {
      const nueva = Math.min((anteriores[clave(f)]?.cantidad ?? 0) + diferencia, f.cantidad_entregable)
      const copia = { ...anteriores }

      // Si llega a 0 la sacamos, así no mandamos líneas sin unidades
      if (nueva <= 0) delete copia[clave(f)]
      else copia[clave(f)] = { fila: f, cantidad: nueva }

      return copia
    })
  }

  // Botón "Registrar entrega": valida y abre la confirmación
  function revisar() {
    setAviso('')

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (!servicio) return setError('Elegí el servicio.')
    if (totalUnidades === 0) return setError('Elegí al menos un material para entregar.')

    setError('')
    setErrorModal('')
    setConfirmando(true)
  }

  async function confirmar() {
    if (!servicio) return

    setErrorModal('')
    setEnviando(true)

    try {
      const entrega = await registrarEntrega({
        servicio_id: servicio.id,
        retira: retira.trim() || undefined,
        observacion: observacion.trim() || undefined,
        // Una línea por lote + material. Si la cantidad es menor que la entregable,
        // es una entrega parcial: el resto sigue disponible.
        lineas: elegidos.map((e) => ({
          lote_id: e.fila.lote_id,
          material_id: e.fila.material_id,
          cantidad: e.cantidad,
        })),
      })

      setAviso(`Entrega registrada: ${unidades(entrega.total_items)} a ${servicio.nombre}.`)
      setConfirmando(false)

      // Limpiamos el formulario. El servicio queda elegido y se actualiza su lista.
      setSeleccion({})
      setRetira('')
      setObservacion('')
      limpiarFiltros()
      setVersion((v) => v + 1)
    } catch (e) {
      setErrorModal(mensajeDeError(e))
      // 409: algún lote cambió de estado mientras tanto. Volvemos a pedir la lista.
      if (esLoteCambiado(e)) setVersion((v) => v + 1)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Stack gap="xl" maw={900}>
      <Title order={1}>Registrar entrega</Title>

      {aviso && (
        <Alert color="green" variant="light" withCloseButton onClose={() => setAviso('')}>
          {aviso}
        </Alert>
      )}

      {/* 1. Servicio: una entrega es de un solo servicio */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          1. Servicio
        </Text>
        <Select
          size="lg"
          maw={420}
          placeholder="Buscá el servicio"
          aria-label="Servicio que retira"
          data={servicios.map((s) => ({ value: String(s.id), label: s.nombre }))}
          value={servicioId}
          onChange={elegirServicio}
          searchable
          nothingFoundMessage="No hay servicios con ese nombre"
        />
      </section>

      {/* 2. Buscar: por N.º de lote o por material (nombre o código) */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          2. Buscar
        </Text>

        {servicioId === null ? (
          <Text c="dimmed">Elegí primero el servicio.</Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm" style={{ alignItems: 'end' }}>
            <NumberInput
              size="md"
              label="N.º de lote"
              placeholder="Ej: 12"
              min={1}
              max={999}
              allowDecimal={false}
              allowNegative={false}
              value={loteNumero}
              onChange={setLoteNumero}
            />
            <TextInput
              size="md"
              label="Material o código"
              placeholder="Ej: gasas o G10"
              value={q}
              onChange={(e) => setQ(e.currentTarget.value)}
            />
            <Button size="md" variant="default" onClick={limpiarFiltros}>
              Limpiar filtros
            </Button>
          </SimpleGrid>
        )}
      </section>

      {/* 3. Material para entregar: en el orden que manda la API (urgentes y más antiguos primero) */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          3. Material para entregar
        </Text>

        {servicioId === null ? (
          <Text c="dimmed">Elegí primero el servicio.</Text>
        ) : !llegaron ? (
          <Text c="dimmed">Buscando…</Text>
        ) : filas.length === 0 ? (
          <Text c="dimmed">No hay material entregable con esos filtros.</Text>
        ) : (
          <Stack gap="sm">
            {filas.map((f) => {
              const cantidad = seleccion[clave(f)]?.cantidad ?? 0
              return (
                <Paper
                  key={clave(f)}
                  withBorder
                  p="sm"
                  radius="md"
                  bg={cantidad > 0 ? '#e6f2ec' : 'white'} // se marca verde si va en la entrega
                >
                  <Group justify="space-between" wrap="nowrap">
                    <div>
                      <Group gap="xs">
                        <Text fw={700}>
                          {f.material}
                          {f.codigo && ` (${f.codigo})`}
                        </Text>
                        {f.urgente && <Badge color="red">Urgente</Badge>}
                      </Group>
                      <Text size="sm">
                        Lote N.º {f.lote_numero} · {f.equipo}
                      </Text>
                      <Text size="sm" c="dimmed">
                        entregable: {f.cantidad_entregable}
                      </Text>
                    </div>

                    <Group gap="xs" wrap="nowrap">
                      <ActionIcon
                        size="xl"
                        fz={22}
                        variant="default"
                        disabled={cantidad === 0}
                        onClick={() => cambiarCantidad(f, -1)}
                        aria-label={`Quitar una unidad de ${f.material} del lote ${f.lote_numero}`}
                      >
                        −
                      </ActionIcon>

                      <Text fw={700} size="xl" w={32} ta="center">
                        {cantidad}
                      </Text>

                      <ActionIcon
                        size="xl"
                        fz={22}
                        color="var(--verde)"
                        disabled={cantidad >= f.cantidad_entregable}
                        onClick={() => cambiarCantidad(f, 1)}
                        aria-label={`Agregar una unidad de ${f.material} del lote ${f.lote_numero}`}
                      >
                        +
                      </ActionIcon>
                    </Group>
                  </Group>
                </Paper>
              )
            })}
          </Stack>
        )}

        <Text mt="sm" c="dimmed">
          Total: {unidades(totalUnidades)}
        </Text>
      </section>

      {/* 4. Quién retira: texto libre. El operador que entrega sale de la sesión. */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          4. Quién retira
        </Text>
        <Stack gap="sm" maw={560}>
          <TextInput
            size="md"
            label="Quién retira (opcional)"
            placeholder="Ej: enfermera de turno"
            value={retira}
            onChange={(e) => setRetira(e.currentTarget.value)}
          />
          <Textarea
            size="md"
            autosize
            minRows={2}
            label="Observación"
            placeholder="Cualquier aclaración sobre la entrega (opcional)"
            value={observacion}
            onChange={(e) => setObservacion(e.currentTarget.value)}
          />
        </Stack>
      </section>

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      <Button size="xl" color="var(--verde)" onClick={revisar}>
        Registrar entrega
      </Button>

      <Modal opened={confirmando} onClose={() => setConfirmando(false)} title="Confirmar entrega">
        <Stack gap="md">
          <Text fw={700}>
            Vas a entregar {unidades(totalUnidades)} a {servicio?.nombre}
          </Text>

          <Stack gap={4}>
            {elegidos.map((e) => (
              <Group key={clave(e.fila)} justify="space-between" wrap="nowrap">
                <Text size="sm">
                  {e.fila.material} · Lote N.º {e.fila.lote_numero} ({e.fila.equipo})
                </Text>
                <Text size="sm" fw={700}>
                  {e.cantidad}
                </Text>
              </Group>
            ))}
          </Stack>

          {retira.trim() && <Text size="sm">Retira: {retira.trim()}</Text>}

          {errorModal && (
            <Alert color="red" variant="light">
              {errorModal}
            </Alert>
          )}

          <Group justify="flex-end">
            <Button size="lg" variant="default" onClick={() => setConfirmando(false)}>
              Cancelar
            </Button>
            <Button size="lg" color="var(--verde)" loading={enviando} onClick={confirmar}>
              Confirmar entrega
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
