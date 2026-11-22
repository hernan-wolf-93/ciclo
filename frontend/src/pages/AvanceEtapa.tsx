import { useEffect, useState } from 'react'
import { ActionIcon, Alert, Button, Checkbox, Group, Loader, Paper, SimpleGrid, Stack, Text, Textarea, Title } from '@mantine/core'
import { mensajeDeError, obtenerMateriales, registrarAvance } from '../services/avanceService'
import type { AvanceRegistrado, EtapaAvance, Material } from '../types'

// * Una misma pantalla para las dos etapas: /lavado (área sucia, rojo) y
// * /empaque (área limpia, azul). El operador que firma sale del token.
const ETAPAS: Record<EtapaAvance, { titulo: string; color: string; fondo: string; anterior: string }> = {
  2: { titulo: 'Lavado y secado', color: 'var(--rojo)', fondo: '#fdecea', anterior: 'Recepción' },
  3: { titulo: 'Empaque y rotulación', color: 'var(--azul)', fondo: '#e7eef8', anterior: 'Lavado y secado' },
}

export default function AvanceEtapa({ etapa }: { etapa: EtapaAvance }) {
  const { titulo, color, fondo, anterior } = ETAPAS[etapa]
  const esLavado = etapa === 2

  const [materiales, setMateriales] = useState<Material[]>([])
  const [cargando, setCargando] = useState(true)

  // * Cuántas unidades de cada material, por id. Solo los que tienen 1 o más.
  const [cantidades, setCantidades] = useState<Record<number, number>>({})

  // * Solo en Lavado: material que no se lava, solo se desinfecta (ej.: cajas de ortopedia)
  const [soloDesinfeccion, setSoloDesinfeccion] = useState(false)
  const [observacion, setObservacion] = useState('')

  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [registrado, setRegistrado] = useState<AvanceRegistrado | null>(null)

  // TODO: cuando exista GET /avances/pendientes, mostrar solo lo que espera en la
  // etapa anterior, con su cantidad (obtenerPendientes en avanceService.ts).
  useEffect(() => {
    obtenerMateriales()
      .then(setMateriales)
      .catch((e) => setError(mensajeDeError(e)))
      .finally(() => setCargando(false))
  }, [])

  // Suma o resta unidades de un material (diferencia = +1 o -1)
  function cambiarCantidad(materialId: number, diferencia: number) {
    setCantidades((anteriores) => {
      const nueva = (anteriores[materialId] ?? 0) + diferencia
      const copia = { ...anteriores }
      if (nueva <= 0) delete copia[materialId]
      else copia[materialId] = nueva
      return copia
    })
  }

  const totalUnidades = Object.values(cantidades).reduce((suma, c) => suma + c, 0)

  async function confirmar() {
    setRegistrado(null)

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (totalUnidades === 0) return setError('Cargá al menos un material.')
    if (soloDesinfeccion && observacion.trim() === '')
      return setError('Si solo se desinfecta, escribí una observación (por ej., qué caja es).')

    setError('')
    setEnviando(true)

    try {
      const resultado = await registrarAvance({
        etapa_orden: etapa,
        // Pasamos de { 3: 2, 12: 1 } a [{ material_id: 3, cantidad: 2 }, ...]
        items: Object.entries(cantidades).map(([id, cantidad]) => ({ material_id: Number(id), cantidad })),
        solo_desinfeccion: esLavado && soloDesinfeccion,
        observacion: observacion.trim() || undefined,
      })
      setRegistrado(resultado)

      // Limpiamos para la próxima carga
      setCantidades({})
      setSoloDesinfeccion(false)
      setObservacion('')
    } catch (e) {
      setError(mensajeDeError(e))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Stack gap="xl" maw={900}>
      <Title order={1}>{titulo}</Title>

      <Alert color="gray" variant="light">
        Cargá las unidades que pasan de {anterior} a {titulo}. Por ahora se muestran todos los
        materiales: si se piden más unidades de las que esperan, el sistema avisa cuántas hay.
      </Alert>

      {/* 1. Materiales: cada uno con botones − y + */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          1. Material
        </Text>

        {cargando ? (
          <Group justify="center" p="lg">
            <Loader />
          </Group>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
            {materiales.map((m) => {
              const cantidad = cantidades[m.id] ?? 0
              return (
                <Paper key={m.id} withBorder p="sm" radius="md" bg={cantidad > 0 ? fondo : 'white'}>
                  <Group justify="space-between" wrap="nowrap">
                    <Text fw={700}>
                      {m.nombre}
                      {m.codigo && (
                        <Text span c="dimmed" fw={400}>
                          {' '}
                          ({m.codigo})
                        </Text>
                      )}
                    </Text>

                    <Group gap="xs" wrap="nowrap">
                      <ActionIcon
                        size="xl"
                        fz={22}
                        variant="default"
                        disabled={cantidad === 0}
                        onClick={() => cambiarCantidad(m.id, -1)}
                        aria-label={`Quitar una unidad de ${m.nombre}`}
                      >
                        −
                      </ActionIcon>
                      <Text fw={700} size="xl" w={32} ta="center">
                        {cantidad}
                      </Text>
                      <ActionIcon
                        size="xl"
                        fz={22}
                        color={color}
                        onClick={() => cambiarCantidad(m.id, 1)}
                        aria-label={`Agregar una unidad de ${m.nombre}`}
                      >
                        +
                      </ActionIcon>
                    </Group>
                  </Group>
                </Paper>
              )
            })}
          </SimpleGrid>
        )}

        <Text mt="sm" c="dimmed">
          Total: {totalUnidades} {totalUnidades === 1 ? 'unidad' : 'unidades'}
        </Text>
      </section>

      {/* 2. Solo en Lavado: la excepción de solo desinfección, con observación obligatoria */}
      {esLavado && (
        <section>
          <Text fw={700} size="lg" mb="sm">
            2. Excepción
          </Text>
          <Checkbox
            size="md"
            color={color}
            label="Solo desinfección (por ej., cajas de ortopedia)"
            checked={soloDesinfeccion}
            onChange={(e) => {
              setSoloDesinfeccion(e.currentTarget.checked)
              setError('')
            }}
          />
          {soloDesinfeccion && (
            <Textarea
              mt="md"
              size="md"
              autosize
              minRows={2}
              label="Observación (obligatoria)"
              placeholder="Ej.: caja de ortopedia, llegó lavada del servicio"
              value={observacion}
              onChange={(e) => setObservacion(e.currentTarget.value)}
            />
          )}
        </section>
      )}

      {/* TODO: en Empaque, elegir el método de esterilización por línea antes de empacar
          (lo pidió la jefa del servicio). Se agrega cuando Lobo ajuste POST /avances. */}
      {!esLavado && (
        <Alert color="gray" variant="light">
          El método de esterilización de cada material se va a elegir en esta pantalla cuando
          el sistema lo admita.
        </Alert>
      )}

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      {registrado && (
        <Alert
          color="green"
          variant="light"
          title="Avance registrado"
          withCloseButton
          onClose={() => setRegistrado(null)}
        >
          {registrado.total_items} {registrado.total_items === 1 ? 'ítem pasó' : 'ítems pasaron'} a {titulo}
          {registrado.solo_desinfeccion ? ' (solo desinfección)' : ''}.
        </Alert>
      )}

      <Button size="xl" color={color} loading={enviando} onClick={confirmar}>
        Pasar a {titulo}
      </Button>
    </Stack>
  )
}
