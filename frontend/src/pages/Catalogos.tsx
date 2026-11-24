import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  SegmentedControl,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useAuth } from '../auth/useAuth'
import {
  crearMaterial,
  crearServicio,
  listarMaterialesAdmin,
  listarServiciosAdmin,
  mensajeDeError,
  modificarMaterial,
  modificarServicio,
} from '../services/catalogosService'
import type { MaterialAdmin, ServicioAdmin } from '../types'

// * ABM de servicios y materiales (tarjeta 5, RF1). Solo administradores.
// * La baja es lógica: el registro deja de aparecer en Recepción, Lavado y Empaque,
// * pero se conserva con su historial y se puede reactivar.

type FiltroEstado = 'activos' | 'bajas' | 'todos'

// Para buscar sin distinguir mayúsculas ni tildes
const normalizar = (texto: string) =>
  texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function coincide(busqueda: string, ...campos: (string | null)[]) {
  const buscado = normalizar(busqueda.trim())
  return !buscado || campos.some((c) => c !== null && normalizar(c).includes(buscado))
}

function pasaEstado(filtro: FiltroEstado, activo: boolean) {
  return filtro === 'todos' || (filtro === 'activos') === activo
}

// Búsqueda y filtro de estado, iguales en las dos pestañas
function Filtros({
  busqueda,
  onBusqueda,
  estado,
  onEstado,
  ayuda,
}: {
  busqueda: string
  onBusqueda: (valor: string) => void
  estado: FiltroEstado
  onEstado: (valor: FiltroEstado) => void
  ayuda: string
}) {
  return (
    <Group align="flex-end">
      <TextInput
        label="Buscar"
        placeholder={ayuda}
        value={busqueda}
        onChange={(e) => onBusqueda(e.currentTarget.value)}
        style={{ flex: 1, minWidth: 220 }}
      />
      <SegmentedControl
        value={estado}
        onChange={(valor) => onEstado(valor as FiltroEstado)}
        data={[
          { value: 'activos', label: 'Activos' },
          { value: 'bajas', label: 'Dados de baja' },
          { value: 'todos', label: 'Todos' },
        ]}
      />
    </Group>
  )
}

function EstadoBadge({ activo }: { activo: boolean }) {
  return <Badge color={activo ? 'green' : 'gray'}>{activo ? 'Activo' : 'De baja'}</Badge>
}

// ---------------------------------------------------------------------------
// Servicios
// ---------------------------------------------------------------------------

// Alta y edición: vive dentro del Modal, así se limpia solo al cerrarlo
function FormServicio({ inicial, onGuardado }: { inicial?: ServicioAdmin; onGuardado: () => void }) {
  const [nombre, setNombre] = useState(inicial?.nombre ?? '')
  const [externo, setExterno] = useState(inicial?.externo ?? false)
  const [dias, setDias] = useState<number | string>(inicial?.dias_aireacion ?? 3)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const guardar = async () => {
    if (!nombre.trim()) {
      setError('Completá el nombre del servicio.')
      return
    }
    if (typeof dias !== 'number' || !Number.isInteger(dias) || dias < 0 || dias > 365) {
      setError('Los días de aireación tienen que ser un número entero entre 0 y 365.')
      return
    }
    setEnviando(true)
    try {
      if (inicial) {
        await modificarServicio(inicial.id, { nombre: nombre.trim(), externo, dias_aireacion: dias })
      } else {
        await crearServicio({ nombre: nombre.trim(), externo, dias_aireacion: dias })
      }
      onGuardado()
    } catch (e) {
      setError(mensajeDeError(e))
      setEnviando(false)
    }
  }

  return (
    <Stack>
      {error && <Alert color="red">{error}</Alert>}
      <TextInput label="Nombre" value={nombre} onChange={(e) => setNombre(e.currentTarget.value)} />
      <Switch
        label="Centro externo (otro hospital, área programática o sanatorio)"
        checked={externo}
        onChange={(e) => setExterno(e.currentTarget.checked)}
      />
      <NumberInput
        label="Días de aireación (óxido de etileno)"
        description="Neonatología 10; Pediatría y Guardia Pediátrica 7; el resto 3."
        value={dias}
        onChange={setDias}
        min={0}
        max={365}
        allowDecimal={false}
        allowNegative={false}
      />
      <Button onClick={guardar} loading={enviando}>
        {inicial ? 'Guardar cambios' : 'Crear servicio'}
      </Button>
    </Stack>
  )
}

function PestanaServicios() {
  const [servicios, setServicios] = useState<ServicioAdmin[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState<FiltroEstado>('activos')
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [editando, setEditando] = useState<ServicioAdmin | null>(null)
  const [recarga, setRecarga] = useState(0)

  // Se pide la lista completa una vez (y tras cada cambio); el filtro es local
  useEffect(() => {
    let vigente = true
    listarServiciosAdmin()
      .then((lista) => {
        if (!vigente) return
        setServicios(lista)
        setError(null)
      })
      .catch((e) => vigente && setError(mensajeDeError(e)))
      .finally(() => vigente && setCargando(false))
    return () => {
      vigente = false
    }
  }, [recarga])

  const cargar = () => setRecarga((n) => n + 1)

  const cambiarEstado = async (s: ServicioAdmin) => {
    const pregunta = s.activo
      ? `¿Querés dar de baja el servicio "${s.nombre}"? Deja de aparecer en las pantallas de operación; su historial se conserva.`
      : `¿Querés reactivar el servicio "${s.nombre}"?`
    if (!window.confirm(pregunta)) return
    try {
      await modificarServicio(s.id, { activo: !s.activo })
      cargar()
    } catch (e) {
      setError(mensajeDeError(e))
    }
  }

  const visibles = servicios.filter((s) => pasaEstado(estado, s.activo) && coincide(busqueda, s.nombre))

  return (
    <Stack>
      <Group justify="space-between">
        <Text c="dimmed">
          Los nombres reales de los sanatorios privados se cargan acá al instalar el sistema.
        </Text>
        <Button onClick={() => setAltaAbierta(true)}>Nuevo servicio</Button>
      </Group>

      <Filtros
        busqueda={busqueda}
        onBusqueda={setBusqueda}
        estado={estado}
        onEstado={setEstado}
        ayuda="Nombre del servicio"
      />

      {error && <Alert color="red">{error}</Alert>}

      {cargando ? (
        <Loader />
      ) : (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nombre</Table.Th>
              <Table.Th>Externo</Table.Th>
              <Table.Th>Días de aireación</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th>Acciones</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {visibles.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>{s.nombre}</Table.Td>
                <Table.Td>{s.externo ? 'Sí' : 'No'}</Table.Td>
                <Table.Td>{s.dias_aireacion}</Table.Td>
                <Table.Td>
                  <EstadoBadge activo={s.activo} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="default" onClick={() => setEditando(s)}>
                      Editar
                    </Button>
                    <Button
                      size="xs"
                      variant="light"
                      color={s.activo ? 'red' : 'green'}
                      onClick={() => cambiarEstado(s)}
                    >
                      {s.activo ? 'Dar de baja' : 'Reactivar'}
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {!cargando && visibles.length === 0 && <Text c="dimmed">No hay servicios con ese filtro.</Text>}

      <Modal opened={altaAbierta} onClose={() => setAltaAbierta(false)} title="Nuevo servicio">
        <FormServicio
          onGuardado={() => {
            setAltaAbierta(false)
            cargar()
          }}
        />
      </Modal>

      <Modal opened={editando !== null} onClose={() => setEditando(null)} title="Editar servicio">
        {editando && (
          <FormServicio
            inicial={editando}
            onGuardado={() => {
              setEditando(null)
              cargar()
            }}
          />
        )}
      </Modal>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// Materiales
// ---------------------------------------------------------------------------

function FormMaterial({ inicial, onGuardado }: { inicial?: MaterialAdmin; onGuardado: () => void }) {
  const [nombre, setNombre] = useState(inicial?.nombre ?? '')
  const [codigo, setCodigo] = useState(inicial?.codigo ?? '')
  const [alternativo, setAlternativo] = useState(inicial?.nombre_alternativo ?? '')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const guardar = async () => {
    if (!nombre.trim()) {
      setError('Completá el nombre del material.')
      return
    }
    // Vacío = sin código / sin nombre alternativo (el back también lo normaliza)
    const datos = {
      nombre: nombre.trim(),
      codigo: codigo.trim() || null,
      nombre_alternativo: alternativo.trim() || null,
    }
    setEnviando(true)
    try {
      if (inicial) await modificarMaterial(inicial.id, datos)
      else await crearMaterial(datos)
      onGuardado()
    } catch (e) {
      setError(mensajeDeError(e))
      setEnviando(false)
    }
  }

  return (
    <Stack>
      {error && <Alert color="red">{error}</Alert>}
      <TextInput label="Nombre" value={nombre} onChange={(e) => setNombre(e.currentTarget.value)} />
      <TextInput
        label="Código (opcional)"
        description="Hasta 10 caracteres. Se guarda en mayúsculas y sin espacios."
        value={codigo}
        onChange={(e) => setCodigo(e.currentTarget.value)}
      />
      <TextInput
        label="Nombre alternativo (opcional)"
        description="Nombre técnico o de cirugía."
        value={alternativo}
        onChange={(e) => setAlternativo(e.currentTarget.value)}
      />
      <Button onClick={guardar} loading={enviando}>
        {inicial ? 'Guardar cambios' : 'Crear material'}
      </Button>
    </Stack>
  )
}

function PestanaMateriales() {
  const [materiales, setMateriales] = useState<MaterialAdmin[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState<FiltroEstado>('activos')
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [editando, setEditando] = useState<MaterialAdmin | null>(null)
  const [recarga, setRecarga] = useState(0)

  useEffect(() => {
    let vigente = true
    listarMaterialesAdmin()
      .then((lista) => {
        if (!vigente) return
        setMateriales(lista)
        setError(null)
      })
      .catch((e) => vigente && setError(mensajeDeError(e)))
      .finally(() => vigente && setCargando(false))
    return () => {
      vigente = false
    }
  }, [recarga])

  const cargar = () => setRecarga((n) => n + 1)

  const cambiarEstado = async (m: MaterialAdmin) => {
    const pregunta = m.activo
      ? `¿Querés dar de baja el material "${m.nombre}"? Deja de aparecer en Recepción, Lavado y Empaque; su historial se conserva.`
      : `¿Querés reactivar el material "${m.nombre}"?`
    if (!window.confirm(pregunta)) return
    try {
      await modificarMaterial(m.id, { activo: !m.activo })
      cargar()
    } catch (e) {
      setError(mensajeDeError(e))
    }
  }

  const visibles = materiales.filter(
    (m) => pasaEstado(estado, m.activo) && coincide(busqueda, m.nombre, m.codigo, m.nombre_alternativo),
  )

  return (
    <Stack>
      <Group justify="flex-end">
        <Button onClick={() => setAltaAbierta(true)}>Nuevo material</Button>
      </Group>

      <Filtros
        busqueda={busqueda}
        onBusqueda={setBusqueda}
        estado={estado}
        onEstado={setEstado}
        ayuda="Nombre, código o nombre alternativo"
      />

      {error && <Alert color="red">{error}</Alert>}

      {cargando ? (
        <Loader />
      ) : (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Código</Table.Th>
              <Table.Th>Nombre</Table.Th>
              <Table.Th>Nombre alternativo</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th>Acciones</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {visibles.map((m) => (
              <Table.Tr key={m.id}>
                <Table.Td>{m.codigo ?? '—'}</Table.Td>
                <Table.Td>{m.nombre}</Table.Td>
                <Table.Td>{m.nombre_alternativo ?? '—'}</Table.Td>
                <Table.Td>
                  <EstadoBadge activo={m.activo} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="default" onClick={() => setEditando(m)}>
                      Editar
                    </Button>
                    <Button
                      size="xs"
                      variant="light"
                      color={m.activo ? 'red' : 'green'}
                      onClick={() => cambiarEstado(m)}
                    >
                      {m.activo ? 'Dar de baja' : 'Reactivar'}
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {!cargando && visibles.length === 0 && <Text c="dimmed">No hay materiales con ese filtro.</Text>}

      <Modal opened={altaAbierta} onClose={() => setAltaAbierta(false)} title="Nuevo material">
        <FormMaterial
          onGuardado={() => {
            setAltaAbierta(false)
            cargar()
          }}
        />
      </Modal>

      <Modal opened={editando !== null} onClose={() => setEditando(null)} title="Editar material">
        {editando && (
          <FormMaterial
            inicial={editando}
            onGuardado={() => {
              setEditando(null)
              cargar()
            }}
          />
        )}
      </Modal>
    </Stack>
  )
}

export default function Catalogos() {
  const { usuario } = useAuth()

  // Esta pantalla es solo para administradores
  if (usuario?.rol === 'Operador') return <Navigate to="/" replace />

  return (
    <Stack>
      <Title order={2}>Catálogos</Title>
      <Tabs defaultValue="servicios">
        <Tabs.List>
          <Tabs.Tab value="servicios">Servicios</Tabs.Tab>
          <Tabs.Tab value="materiales">Materiales</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="servicios" pt="md">
          <PestanaServicios />
        </Tabs.Panel>
        <Tabs.Panel value="materiales" pt="md">
          <PestanaMateriales />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
