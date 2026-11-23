import { useEffect, useState } from 'react'
import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import {
  cerrarLote,
  crearLote,
  obtenerEquipos,
  obtenerLotesEnCurso,
  obtenerPendientes,
  obtenerProgramas,
  obtenerProximoNumero,
} from '../services/esterilizacionService'
import type { Equipo, LoteAbierto, PendienteCarga, Programa, ResultadoLote } from '../types'

// ---------------------------------------------------------------------------
// Formatos
// ---------------------------------------------------------------------------

// "22/11 14:05" (siempre en 24 h)
function diaHora(iso: string) {
  const fecha = new Date(iso)
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const hora = fecha.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
  return `${dia}/${mes} ${hora}`
}

// Números con coma decimal, como en el panel del equipo: "-0,75"
const numero = (n: number) => n.toLocaleString('es-AR', { maximumFractionDigits: 2 })

// El texto del error que lanza el servicio
const mensajeDeError = (e: unknown, otro: string) => (e instanceof Error ? e.message : otro)

// Subtítulos de la sección "1. Equipo", por método
const GRUPOS_DE_EQUIPOS = [
  { metodoId: 1, titulo: 'Autoclaves' },
  { metodoId: 2, titulo: 'Estufas' },
  { metodoId: 3, titulo: 'Óxido de etileno' },
]

// Clave de cada línea de la carga: un material de un servicio. Ej: "17-6"
const clave = (p: PendienteCarga) => `${p.servicio.id}-${p.material.id}`

// ---------------------------------------------------------------------------
// Pantalla
// ---------------------------------------------------------------------------

export default function Esterilizacion() {
  const [equipos, setEquipos] = useState<Equipo[]>([])
  const [equipoId, setEquipoId] = useState<number | null>(null)
  const [programaId, setProgramaId] = useState<number | null>(null)

  // * Lo que llega de la API para el equipo elegido. Guardamos de qué equipo es,
  // * así nunca se mezclan las listas si el operador toca dos equipos rápido.
  const [programasDe, setProgramasDe] = useState<{ equipoId: number; programas: Programa[] } | null>(null)
  const [pendientesDe, setPendientesDe] = useState<{ equipoId: number; pendientes: PendienteCarga[] } | null>(null)
  const [propuestoDe, setPropuestoDe] = useState<{ equipoId: number; numero: number } | null>(null)

  // * Cuántas unidades se cargan de cada línea, por clave. Ej: { "17-6": 2 }
  // * Solo guardamos las que tienen 1 o más.
  const [cantidades, setCantidades] = useState<Record<string, number>>({})

  // * null = el operador no lo tocó: se muestra el propuesto
  const [numeroEditado, setNumeroEditado] = useState<string | number | null>(null)

  const [enCurso, setEnCurso] = useState<LoteAbierto[]>([])
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('') // confirmación en verde (lote creado o cerrado)

  // Modal de cierre
  const [cerrando, setCerrando] = useState<LoteAbierto | null>(null)
  const [resultado, setResultado] = useState<'' | ResultadoLote>('')
  const [numeroCiclo, setNumeroCiclo] = useState('')
  const [observacion, setObservacion] = useState('')
  const [errorCierre, setErrorCierre] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  // Al entrar a la pantalla traemos los equipos y los ciclos en curso
  useEffect(() => {
    obtenerEquipos()
      .then(setEquipos)
      .catch((e) => setError(mensajeDeError(e, 'No se pudieron traer los equipos.')))
    obtenerLotesEnCurso()
      .then(setEnCurso)
      .catch((e) => setError(mensajeDeError(e, 'No se pudieron traer los ciclos en curso.')))
  }, [])

  function actualizarEnCurso() {
    obtenerLotesEnCurso()
      .then(setEnCurso)
      .catch((e) => setError(mensajeDeError(e, 'No se pudieron traer los ciclos en curso.')))
  }

  // Pendientes y número propuesto del equipo (se piden al elegirlo y después de crear un lote)
  function cargarCargaDelEquipo(id: number) {
    obtenerPendientes(id)
      .then((lista) => setPendientesDe({ equipoId: id, pendientes: lista }))
      .catch((e) => setError(mensajeDeError(e, 'No se pudo traer el material pendiente.')))
    obtenerProximoNumero(id)
      .then((n) => setPropuestoDe({ equipoId: id, numero: n }))
      .catch((e) => setError(mensajeDeError(e, 'No se pudo proponer el número de lote.')))
  }

  // Al elegir un equipo borramos lo cargado antes y traemos SUS datos
  function elegirEquipo(id: number) {
    setEquipoId(id)
    setProgramaId(null)
    setCantidades({})
    setNumeroEditado(null)
    setError('')

    obtenerProgramas(id)
      .then((lista) => setProgramasDe({ equipoId: id, programas: lista }))
      .catch((e) => setError(mensajeDeError(e, 'No se pudieron traer los programas.')))
    cargarCargaDelEquipo(id)
  }

  // Solo usamos lo que llegó si es del equipo elegido
  const programas = programasDe?.equipoId === equipoId ? programasDe.programas : []
  const pendientes = pendientesDe?.equipoId === equipoId ? pendientesDe.pendientes : []
  const propuesto = propuestoDe?.equipoId === equipoId ? propuestoDe.numero : null
  const numeroLote = numeroEditado ?? propuesto ?? ''

  const equipo = equipos.find((e) => e.id === equipoId)
  const programa = programas.find((p) => p.id === programaId)

  // Pendientes agrupados por servicio de origen
  const porServicio: { servicio: PendienteCarga['servicio']; lineas: PendienteCarga[] }[] = []
  for (const p of pendientes) {
    const grupo = porServicio.find((g) => g.servicio.id === p.servicio.id)
    if (grupo) grupo.lineas.push(p)
    else porServicio.push({ servicio: p.servicio, lineas: [p] })
  }

  // Suma o resta unidades de una línea (diferencia = +1 o -1), sin pasar de lo disponible
  function cambiarCantidad(p: PendienteCarga, diferencia: number) {
    setCantidades((anteriores) => {
      const nueva = Math.min((anteriores[clave(p)] ?? 0) + diferencia, p.cantidad)
      const copia = { ...anteriores }

      // Si llega a 0 la sacamos, así no mandamos líneas sin unidades
      if (nueva <= 0) delete copia[clave(p)]
      else copia[clave(p)] = nueva

      return copia
    })
  }

  const totalUnidades = pendientes.reduce((suma, p) => suma + (cantidades[clave(p)] ?? 0), 0)

  async function crear() {
    setAviso('')

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (equipoId === null || !equipo) return setError('Elegí el equipo.')
    if (programaId === null) return setError('Elegí el programa.')
    if (totalUnidades === 0) return setError('Cargá al menos un paquete.')
    const n = Number(numeroLote)
    if (numeroLote === '' || !Number.isInteger(n) || n < 1 || n > 999) {
      return setError('Indicá un número de lote de 1 a 999.')
    }

    setError('')
    setEnviando(true)

    try {
      // Pasamos de { "17-6": 2 } a [{ servicio_id: 17, material_id: 6, cantidad: 2 }, ...]
      const lineas = pendientes
        .filter((p) => (cantidades[clave(p)] ?? 0) > 0)
        .map((p) => ({ servicio_id: p.servicio.id, material_id: p.material.id, cantidad: cantidades[clave(p)] }))

      const lote = await crearLote({ equipo_id: equipoId, programa_id: programaId, numero: n, lineas })

      setAviso(
        `Lote N.º ${lote.numero} creado en ${equipo.nombre}. Cuando termine el ciclo, cerralo desde Ciclos en curso.`,
      )

      // Limpiamos el formulario. El equipo queda elegido y se actualizan
      // sus pendientes y el número propuesto.
      setProgramaId(null)
      setCantidades({})
      setNumeroEditado(null)
      cargarCargaDelEquipo(equipoId)
      actualizarEnCurso()
    } catch (e) {
      setError(mensajeDeError(e, 'No se pudo crear el lote. Probá de nuevo.'))
    } finally {
      setEnviando(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Cierre del ciclo
  // ---------------------------------------------------------------------------

  function abrirCierre(lote: LoteAbierto) {
    setCerrando(lote)
    setResultado('')
    setNumeroCiclo('')
    setObservacion('')
    setErrorCierre('')
  }

  async function confirmarCierre() {
    if (!cerrando) return
    if (resultado === '') return setErrorCierre('Indicá si el lote salió aprobado o fallido.')

    setErrorCierre('')
    setConfirmando(true)

    try {
      await cerrarLote(cerrando.id, {
        resultado,
        numero_ciclo: numeroCiclo.trim() || undefined,
        observacion: observacion.trim() || undefined,
      })

      setAviso(`Lote N.º ${cerrando.numero} cerrado como ${resultado === 'aprobado' ? 'aprobado' : 'fallido'}.`)
      setCerrando(null)
      actualizarEnCurso()
    } catch (e) {
      setErrorCierre(mensajeDeError(e, 'No se pudo cerrar el ciclo. Probá de nuevo.'))
    } finally {
      setConfirmando(false)
    }
  }

  // Parámetros del programa: los que son null no se muestran
  const datosDelCiclo = programa
    ? [
        { etiqueta: 'Temperatura', valor: `${numero(programa.temperatura_c)} °C` },
        { etiqueta: 'Tiempo de esterilización', valor: `${numero(programa.tiempo_esterilizacion_min)} min` },
        { etiqueta: 'Secado', valor: programa.tiempo_secado_min !== null ? `${numero(programa.tiempo_secado_min)} min` : null },
        { etiqueta: 'Vacío', valor: programa.vacio_bar !== null ? `${numero(programa.vacio_bar)} bar` : null },
        { etiqueta: 'Vapor', valor: programa.vapor_bar !== null ? `${numero(programa.vapor_bar)} bar` : null },
        { etiqueta: 'Pulsos', valor: programa.pulsos !== null ? numero(programa.pulsos) : null },
      ].filter((d) => d.valor !== null)
    : []

  return (
    <Stack gap="xl" maw={900}>
      <Title order={1}>Esterilización</Title>

      {aviso && (
        <Alert color="green" variant="light" withCloseButton onClose={() => setAviso('')}>
          {aviso}
        </Alert>
      )}

      {/* Ciclos en curso: solo si hay alguno */}
      {enCurso.length > 0 && (
        <section>
          <Text fw={700} size="lg" mb="sm">
            Ciclos en curso
          </Text>
          <Stack gap="sm">
            {enCurso.map((l) => (
              <Paper key={l.id} withBorder p="md" radius="md">
                <Group justify="space-between">
                  <Text fw={700}>
                    Lote N.º {l.numero} · {l.equipo.nombre} · {l.programa.nombre} · inicio {diaHora(l.inicio)}
                  </Text>
                  <Button size="md" color="var(--gris)" onClick={() => abrirCierre(l)}>
                    Cerrar ciclo
                  </Button>
                </Group>
              </Paper>
            ))}
          </Stack>
        </section>
      )}

      {/* 1. Equipo: botones grandes, agrupados por método */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          1. Equipo
        </Text>
        <Stack gap="md">
          {GRUPOS_DE_EQUIPOS.map((g) => {
            const delGrupo = equipos.filter((e) => e.metodo_id === g.metodoId)
            if (delGrupo.length === 0) return null
            return (
              <div key={g.metodoId}>
                <Text fw={700} c="dimmed" mb="xs">
                  {g.titulo}
                </Text>
                <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
                  {delGrupo.map((e) => (
                    <Button
                      key={e.id}
                      size="lg"
                      h="auto"
                      py="md"
                      color="var(--gris)"
                      variant={equipoId === e.id ? 'filled' : 'default'}
                      onClick={() => elegirEquipo(e.id)}
                      styles={{ label: { whiteSpace: 'normal' } }}
                    >
                      {e.nombre}
                    </Button>
                  ))}
                </SimpleGrid>
              </div>
            )
          })}
        </Stack>
      </section>

      {/* 2. Programa: sus parámetros son los datos del ciclo (no se cargan a mano) */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          2. Programa
        </Text>

        {equipoId === null ? (
          <Text c="dimmed">Elegí primero el equipo.</Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
            {programas.map((p) => (
              <Button
                key={p.id}
                size="lg"
                h="auto"
                py="md"
                color="var(--gris)"
                variant={programaId === p.id ? 'filled' : 'default'}
                onClick={() => {
                  setProgramaId(p.id)
                  setError('')
                }}
                styles={{ label: { whiteSpace: 'normal' } }}
              >
                {p.nombre}
              </Button>
            ))}
          </SimpleGrid>
        )}

        {programa && (
          <Paper withBorder p="md" radius="md" mt="md" bg="#f1f3f5">
            <Text fw={700} mb="xs">
              Datos del ciclo (salen del programa)
            </Text>
            <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
              {datosDelCiclo.map((d) => (
                <div key={d.etiqueta}>
                  <Text size="sm" c="dimmed">
                    {d.etiqueta}
                  </Text>
                  <Text fw={700} size="lg">
                    {d.valor}
                  </Text>
                </div>
              ))}
            </SimpleGrid>
          </Paper>
        )}
      </section>

      {/* 3. Paquetes de la carga: lo que espera para el método del equipo */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          3. Paquetes de la carga
        </Text>

        {equipoId === null ? (
          <Text c="dimmed">Elegí primero el equipo.</Text>
        ) : pendientesDe?.equipoId === equipoId && pendientes.length === 0 ? (
          <Text c="dimmed">No hay material pendiente para este método.</Text>
        ) : (
          <Stack gap="lg">
            {porServicio.map((g) => (
              <div key={g.servicio.id}>
                <Text fw={700} c="dimmed" mb="xs">
                  {g.servicio.nombre}
                </Text>
                <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                  {g.lineas.map((p) => {
                    const cantidad = cantidades[clave(p)] ?? 0
                    return (
                      <Paper
                        key={clave(p)}
                        withBorder
                        p="sm"
                        radius="md"
                        bg={cantidad > 0 ? '#e9ecef' : 'white'} // se marca gris si va en la carga
                      >
                        <Group justify="space-between" wrap="nowrap">
                          <div>
                            <Text fw={700}>{p.material.nombre}</Text>
                            <Text size="sm" c="dimmed">
                              disponibles: {p.cantidad}
                            </Text>
                          </div>

                          <Group gap="xs" wrap="nowrap">
                            <ActionIcon
                              size="xl"
                              fz={22}
                              variant="default"
                              disabled={cantidad === 0}
                              onClick={() => cambiarCantidad(p, -1)}
                              aria-label={`Quitar una unidad de ${p.material.nombre} de ${p.servicio.nombre}`}
                            >
                              −
                            </ActionIcon>

                            <Text fw={700} size="xl" w={32} ta="center">
                              {cantidad}
                            </Text>

                            <ActionIcon
                              size="xl"
                              fz={22}
                              color="var(--gris)"
                              disabled={cantidad >= p.cantidad}
                              onClick={() => cambiarCantidad(p, 1)}
                              aria-label={`Agregar una unidad de ${p.material.nombre} de ${p.servicio.nombre}`}
                            >
                              +
                            </ActionIcon>
                          </Group>
                        </Group>
                      </Paper>
                    )
                  })}
                </SimpleGrid>
              </div>
            ))}
          </Stack>
        )}

        <Text mt="sm" c="dimmed">
          Total: {totalUnidades} {totalUnidades === 1 ? 'unidad' : 'unidades'}
        </Text>
      </section>

      {/* 4. Número de lote: lo propone el sistema y el operador puede corregirlo */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          4. Número de lote
        </Text>
        <NumberInput
          size="lg"
          maw={240}
          min={1}
          max={999}
          allowDecimal={false}
          allowNegative={false}
          clampBehavior="strict"
          value={numeroLote}
          onChange={(valor) => {
            setNumeroEditado(valor)
            setError('')
          }}
          description={propuesto !== null ? `Propuesto: ${propuesto}. Podés corregirlo.` : undefined}
          inputWrapperOrder={['label', 'input', 'description', 'error']}
        />
      </section>

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      <Button size="xl" color="var(--gris)" loading={enviando} onClick={crear}>
        Crear lote
      </Button>

      <Modal
        opened={cerrando !== null}
        onClose={() => setCerrando(null)}
        title={cerrando ? `Cerrar ciclo del lote N.º ${cerrando.numero}` : ''}
      >
        <Stack gap="md">
          <SegmentedControl
            size="lg"
            fullWidth
            value={resultado}
            onChange={(valor) => {
              setResultado(valor as ResultadoLote)
              setErrorCierre('')
            }}
            color={resultado === 'fallido' ? 'red' : 'var(--verde)'}
            data={[
              { label: 'Aprobado', value: 'aprobado' },
              { label: 'Fallido', value: 'fallido' },
            ]}
          />

          <TextInput
            size="md"
            label="N.º de ciclo (el que imprime el ticket)"
            placeholder="Opcional. Ej: 1189"
            inputMode="numeric"
            value={numeroCiclo}
            onChange={(e) => setNumeroCiclo(e.currentTarget.value)}
          />

          <Textarea
            size="md"
            autosize
            minRows={2}
            label="Observación"
            withAsterisk={resultado === 'fallido'}
            placeholder={
              resultado === 'fallido'
                ? 'Ej: el indicador químico no viró'
                : 'Cualquier aclaración sobre el ciclo (opcional)'
            }
            value={observacion}
            onChange={(e) => {
              setObservacion(e.currentTarget.value)
              setErrorCierre('')
            }}
          />

          {errorCierre && (
            <Alert color="red" variant="light">
              {errorCierre}
            </Alert>
          )}

          <Button size="lg" color="var(--gris)" loading={confirmando} onClick={confirmarCierre}>
            Confirmar cierre
          </Button>
        </Stack>
      </Modal>
    </Stack>
  )
}
