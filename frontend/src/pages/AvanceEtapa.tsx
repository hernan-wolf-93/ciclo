import { useEffect, useRef, useState } from 'react'
import {
  ActionIcon,
  Alert,
  Button,
  Checkbox,
  Group,
  Loader,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Title,
} from '@mantine/core'
import {
  mensajeDeError,
  obtenerMateriales,
  obtenerMetodos,
  obtenerPendientes,
  registrarAvance,
} from '../services/avanceService'
import type { AvanceRegistrado, EtapaAvance, Metodo, Pendiente } from '../types'

// * Una misma pantalla para las dos etapas: /lavado (área sucia, rojo) y
// * /empaque (área limpia, azul). El operador que firma sale del token.
// * Solo se muestra el material que espera en la etapa anterior (GET /avances/pendientes).
const ETAPAS: Record<EtapaAvance, { titulo: string; color: string; fondo: string; anterior: string }> = {
  2: { titulo: 'Lavado y secado', color: 'var(--rojo)', fondo: '#fdecea', anterior: 'Recepción' },
  3: { titulo: 'Empaque y rotulación', color: 'var(--azul)', fondo: '#e7eef8', anterior: 'Lavado y secado' },
}

// Material que espera, con la suma de todos los servicios de origen: el avance toma
// los ítems más antiguos del material sin mirar el servicio.
interface Disponible {
  material_id: number
  nombre: string
  cantidad: number
}

// Lo que se carga. En Lavado, una línea por material y sin método.
// En Empaque, una línea por material y método (el mismo material puede ir en dos).
interface Linea {
  clave: number // solo para React
  material_id: number
  metodo_id: number | null
  cantidad: number
}

function sumarPorMaterial(pendientes: Pendiente[]): Disponible[] {
  const porMaterial = new Map<number, Disponible>()
  for (const p of pendientes) {
    const actual = porMaterial.get(p.material_id)
    if (actual) actual.cantidad += p.cantidad
    else porMaterial.set(p.material_id, { material_id: p.material_id, nombre: p.material, cantidad: p.cantidad })
  }
  return [...porMaterial.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
}

// Tras recargar los pendientes, lo cargado no puede pasar de lo que espera ahora
function ajustarALoDisponible(lineas: Linea[], disponibles: Disponible[]): Linea[] {
  const tope = new Map(disponibles.map((d) => [d.material_id, d.cantidad]))
  const usado = new Map<number, number>()
  const resultado: Linea[] = []
  for (const l of lineas) {
    const resto = (tope.get(l.material_id) ?? 0) - (usado.get(l.material_id) ?? 0)
    const cantidad = Math.min(l.cantidad, resto)
    if (cantidad <= 0) continue
    usado.set(l.material_id, (usado.get(l.material_id) ?? 0) + cantidad)
    resultado.push({ ...l, cantidad })
  }
  return resultado
}

// Botones − cantidad + de una línea. El + se deshabilita al llegar a lo que espera.
function Contador({
  cantidad,
  nombre,
  color,
  puedeSumar,
  onRestar,
  onSumar,
}: {
  cantidad: number
  nombre: string
  color: string
  puedeSumar: boolean
  onRestar: () => void
  onSumar: () => void
}) {
  return (
    <Group gap="xs" wrap="nowrap">
      <ActionIcon
        size="xl"
        fz={22}
        variant="default"
        disabled={cantidad === 0}
        onClick={onRestar}
        aria-label={`Quitar una unidad de ${nombre}`}
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
        disabled={!puedeSumar}
        onClick={onSumar}
        aria-label={`Agregar una unidad de ${nombre}`}
      >
        +
      </ActionIcon>
    </Group>
  )
}

export default function AvanceEtapa({ etapa }: { etapa: EtapaAvance }) {
  const { titulo, color, fondo, anterior } = ETAPAS[etapa]
  const esLavado = etapa === 2

  const [disponibles, setDisponibles] = useState<Disponible[]>([])
  const [codigos, setCodigos] = useState<Record<number, string | null>>({})
  const [metodos, setMetodos] = useState<Metodo[]>([])
  const [cargando, setCargando] = useState(true)
  const [recarga, setRecarga] = useState(0)

  const [lineas, setLineas] = useState<Linea[]>([])
  const proximaClave = useRef(1)

  // * Solo en Lavado: material que no se lava, solo se desinfecta (ej.: cajas de ortopedia)
  const [soloDesinfeccion, setSoloDesinfeccion] = useState(false)
  const [observacion, setObservacion] = useState('')

  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [marcarSinMetodo, setMarcarSinMetodo] = useState(false)
  const [registrado, setRegistrado] = useState<AvanceRegistrado | null>(null)

  // Pendientes de la etapa: al entrar y después de cada avance (o de un rechazo)
  useEffect(() => {
    let vigente = true
    obtenerPendientes(etapa)
      .then((pendientes) => {
        if (!vigente) return
        const nuevos = sumarPorMaterial(pendientes)
        setDisponibles(nuevos)
        setLineas((actuales) => ajustarALoDisponible(actuales, nuevos))
      })
      .catch((e) => vigente && setError(mensajeDeError(e)))
      .finally(() => vigente && setCargando(false))
    return () => {
      vigente = false
    }
  }, [etapa, recarga])

  // El código del material es solo informativo: si falla, se muestra sin código
  useEffect(() => {
    obtenerMateriales()
      .then((lista) => setCodigos(Object.fromEntries(lista.map((m) => [m.id, m.codigo]))))
      .catch(() => setCodigos({}))
  }, [])

  useEffect(() => {
    if (esLavado) return
    obtenerMetodos()
      .then(setMetodos)
      .catch((e) => setError(mensajeDeError(e)))
  }, [esLavado])

  const recargarPendientes = () => {
    setCargando(true)
    setRecarga((n) => n + 1)
  }

  const usadoDe = (materialId: number) =>
    lineas.filter((l) => l.material_id === materialId).reduce((suma, l) => suma + l.cantidad, 0)

  const agregarLinea = (materialId: number) => {
    const clave = proximaClave.current++
    setLineas((actuales) => [...actuales, { clave, material_id: materialId, metodo_id: null, cantidad: 1 }])
  }

  // Suma o resta unidades de una línea (diferencia = +1 o -1). En 0 la línea se quita.
  const cambiarCantidad = (clave: number, diferencia: number) => {
    setLineas((actuales) =>
      actuales
        .map((l) => (l.clave === clave ? { ...l, cantidad: l.cantidad + diferencia } : l))
        .filter((l) => l.cantidad > 0),
    )
  }

  const elegirMetodo = (clave: number, metodoId: number | null) => {
    setLineas((actuales) => actuales.map((l) => (l.clave === clave ? { ...l, metodo_id: metodoId } : l)))
    setError('')
  }

  const totalUnidades = lineas.reduce((suma, l) => suma + l.cantidad, 0)

  async function confirmar() {
    setRegistrado(null)

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (totalUnidades === 0) return setError('Cargá al menos un material.')
    if (!esLavado && lineas.some((l) => l.metodo_id === null)) {
      setMarcarSinMetodo(true)
      return setError('Elegí el método de esterilización de cada línea de Empaque.')
    }
    if (soloDesinfeccion && observacion.trim() === '')
      return setError('Si solo se desinfecta, escribí una observación (por ej., qué caja es).')

    setError('')
    setEnviando(true)

    try {
      const resultado = await registrarAvance({
        etapa_orden: etapa,
        items: lineas.map((l) =>
          esLavado
            ? { material_id: l.material_id, cantidad: l.cantidad }
            : { material_id: l.material_id, cantidad: l.cantidad, metodo_id: l.metodo_id ?? undefined },
        ),
        solo_desinfeccion: esLavado && soloDesinfeccion,
        observacion: observacion.trim() || undefined,
      })
      setRegistrado(resultado)

      // Limpiamos para la próxima carga
      setLineas([])
      setMarcarSinMetodo(false)
      setSoloDesinfeccion(false)
      setObservacion('')
    } catch (e) {
      // Puede que otro operador haya avanzado esos ítems: se muestra el motivo y se recarga
      setError(mensajeDeError(e))
    } finally {
      setEnviando(false)
      recargarPendientes()
    }
  }

  // + de una línea; en Lavado, si el material todavía no tiene línea, la crea
  const sumar = (linea: Linea | undefined, materialId: number) =>
    linea ? cambiarCantidad(linea.clave, 1) : agregarLinea(materialId)

  return (
    <Stack gap="xl" maw={900}>
      <Title order={1}>{titulo}</Title>

      <Text c="dimmed">
        Cargá las unidades que pasan de {anterior} a {titulo}. Se muestra solo el material que espera
        en {anterior}, con la cantidad disponible.
        {!esLavado && ' Elegí el método de esterilización de cada línea: cada método lleva otro envoltorio.'}
      </Text>

      {/* 1. Materiales que esperan */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          1. Material
        </Text>

        {cargando && disponibles.length === 0 ? (
          <Group justify="center" p="lg">
            <Loader />
          </Group>
        ) : disponibles.length === 0 ? (
          <Alert color="gray" variant="light">
            No hay material esperando para esta etapa.
          </Alert>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: esLavado ? 2 : 1, md: esLavado ? 3 : 2 }} spacing="sm">
            {disponibles.map((d) => {
              const delMaterial = lineas.filter((l) => l.material_id === d.material_id)
              const usado = usadoDe(d.material_id)
              const quedan = d.cantidad - usado
              const codigo = codigos[d.material_id]
              return (
                <Paper key={d.material_id} withBorder p="sm" radius="md" bg={usado > 0 ? fondo : 'white'}>
                  <Group justify="space-between" wrap="nowrap" align="flex-start">
                    <div>
                      <Text fw={700}>
                        {d.nombre}
                        {codigo && (
                          <Text span c="dimmed" fw={400}>
                            {' '}
                            ({codigo})
                          </Text>
                        )}
                      </Text>
                      <Text size="sm" c="dimmed">
                        Esperando: {d.cantidad}
                      </Text>
                    </div>
                    {esLavado && (
                      <Contador
                        cantidad={delMaterial[0]?.cantidad ?? 0}
                        nombre={d.nombre}
                        color={color}
                        puedeSumar={quedan > 0}
                        onRestar={() => delMaterial[0] && cambiarCantidad(delMaterial[0].clave, -1)}
                        onSumar={() => sumar(delMaterial[0], d.material_id)}
                      />
                    )}
                  </Group>

                  {/* Empaque: una línea por método */}
                  {!esLavado && (
                    <Stack gap="xs" mt="sm">
                      {delMaterial.map((l) => {
                        const usadosPorOtras = new Set(
                          delMaterial.filter((o) => o.clave !== l.clave).map((o) => o.metodo_id),
                        )
                        return (
                          <Group key={l.clave} justify="space-between" wrap="nowrap">
                            <Select
                              size="md"
                              placeholder="Elegí el método"
                              aria-label={`Método de esterilización de ${d.nombre}`}
                              data={metodos
                                .filter((m) => !usadosPorOtras.has(m.id))
                                .map((m) => ({ value: String(m.id), label: m.nombre }))}
                              value={l.metodo_id === null ? null : String(l.metodo_id)}
                              onChange={(v) => elegirMetodo(l.clave, v === null ? null : Number(v))}
                              error={marcarSinMetodo && l.metodo_id === null ? 'Falta el método' : undefined}
                              style={{ flex: 1 }}
                            />
                            <Contador
                              cantidad={l.cantidad}
                              nombre={d.nombre}
                              color={color}
                              puedeSumar={quedan > 0}
                              onRestar={() => cambiarCantidad(l.clave, -1)}
                              onSumar={() => cambiarCantidad(l.clave, 1)}
                            />
                          </Group>
                        )
                      })}
                      <Group>
                        <Button
                          variant="light"
                          color={color}
                          disabled={quedan <= 0 || delMaterial.length >= metodos.length}
                          onClick={() => agregarLinea(d.material_id)}
                        >
                          {delMaterial.length === 0 ? 'Cargar con un método' : 'Agregar otro método'}
                        </Button>
                      </Group>
                    </Stack>
                  )}
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
      {esLavado && disponibles.length > 0 && (
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

      {disponibles.length > 0 && (
        <Button size="xl" color={color} loading={enviando} onClick={confirmar}>
          Pasar a {titulo}
        </Button>
      )}
    </Stack>
  )
}
