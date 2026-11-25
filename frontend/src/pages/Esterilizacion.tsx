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
  mensajeDeError,
  obtenerBowieDickHoy,
  obtenerEquipos,
  obtenerLotesEnCurso,
  obtenerPendientes,
  obtenerProgramas,
  obtenerProximoNumero,
  registrarBowieDick,
} from '../services/esterilizacionService'
import type { EquipoDeCarga, LoteResumen, PendienteCarga, Programa, ResultadoLote } from '../types'

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

// Un parámetro del programa con su unidad, o null si el programa no lo tiene
const conUnidad = (valor: number | null, unidad: string) => (valor === null ? null : `${numero(valor)}${unidad}`)

// * El autoclave se reconoce por el nombre de su método, igual que en el back
// * (METODO_CON_BOWIE_DICK en backend/app/services/bowie_dick.py).
const METODO_AUTOCLAVE = 'Calor húmedo'

// Subtítulos de la sección "1. Equipo", por nombre del método (GET /equipos)
const TITULOS_DE_METODO: Record<string, string> = {
  'Calor húmedo': 'Autoclaves',
  'Calor seco': 'Estufas',
  'Óxido de etileno': 'Óxido de etileno',
}

// Clave de cada línea de la carga: un material de un servicio. Ej: "17-6"
const clave = (p: PendienteCarga) => `${p.servicio_id}-${p.material_id}`

// ---------------------------------------------------------------------------
// Pantalla
// ---------------------------------------------------------------------------

export default function Esterilizacion() {
  const [equipos, setEquipos] = useState<EquipoDeCarga[]>([])
  const [equipoId, setEquipoId] = useState<number | null>(null)
  const [programaId, setProgramaId] = useState<number | null>(null)

  // * Lo que llega de la API para el equipo elegido. Guardamos de qué equipo es,
  // * así nunca se mezclan las listas si el operador toca dos equipos rápido.
  const [programasDe, setProgramasDe] = useState<{ equipoId: number; programas: Programa[] } | null>(null)
  const [pendientesDe, setPendientesDe] = useState<{ equipoId: number; pendientes: PendienteCarga[] } | null>(null)
  const [propuestoDe, setPropuestoDe] = useState<{ equipoId: number; numero: number } | null>(null)
  const [bowieDickDe, setBowieDickDe] = useState<{ equipoId: number; aprobado: boolean } | null>(null)

  // * Cuántas unidades se cargan de cada línea, por clave. Ej: { "17-6": 2 }
  // * Solo guardamos las que tienen 1 o más.
  const [cantidades, setCantidades] = useState<Record<string, number>>({})

  // * null = el operador no lo tocó: se muestra el propuesto
  const [numeroEditado, setNumeroEditado] = useState<string | number | null>(null)

  const [enCurso, setEnCurso] = useState<LoteResumen[]>([])
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('') // confirmación en verde (lote creado o cerrado, Bowie-Dick registrado)

  // Modal de cierre
  const [cerrando, setCerrando] = useState<LoteResumen | null>(null)
  const [resultado, setResultado] = useState<'' | ResultadoLote>('')
  const [numeroCiclo, setNumeroCiclo] = useState('')
  const [observacion, setObservacion] = useState('')
  const [errorCierre, setErrorCierre] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  // Modal del control Bowie-Dick
  const [registrandoBowieDick, setRegistrandoBowieDick] = useState(false) // modal abierto
  const [resultadoBowieDick, setResultadoBowieDick] = useState<'' | ResultadoLote>('')
  const [cicloBowieDick, setCicloBowieDick] = useState('')
  const [observacionBowieDick, setObservacionBowieDick] = useState('')
  const [errorBowieDick, setErrorBowieDick] = useState('')
  const [guardandoBowieDick, setGuardandoBowieDick] = useState(false)

  // Al entrar a la pantalla traemos los equipos y los ciclos en curso
  useEffect(() => {
    obtenerEquipos()
      .then(setEquipos)
      .catch((e) => setError(mensajeDeError(e)))
    obtenerLotesEnCurso()
      .then(setEnCurso)
      .catch((e) => setError(mensajeDeError(e)))
  }, [])

  function actualizarEnCurso() {
    obtenerLotesEnCurso()
      .then(setEnCurso)
      .catch((e) => setError(mensajeDeError(e)))
  }

  // Pendientes y número propuesto del equipo (se piden al elegirlo y después de crear o cerrar un lote)
  function cargarCargaDelEquipo(id: number) {
    obtenerPendientes(id)
      .then((lista) => setPendientesDe({ equipoId: id, pendientes: lista }))
      .catch((e) => setError(mensajeDeError(e)))
    obtenerProximoNumero(id)
      .then((n) => setPropuestoDe({ equipoId: id, numero: n }))
      .catch((e) => setError(mensajeDeError(e)))
  }

  // Si el autoclave tiene hoy un Bowie-Dick aprobado (el último de hoy es el que cuenta)
  function consultarBowieDick(id: number) {
    obtenerBowieDickHoy(id)
      .then((estado) => setBowieDickDe({ equipoId: id, aprobado: estado.aprobado_hoy }))
      .catch((e) => setError(mensajeDeError(e)))
  }

  // Al elegir un equipo borramos lo cargado antes y traemos SUS datos
  function elegirEquipo(e: EquipoDeCarga) {
    setEquipoId(e.id)
    setProgramaId(null)
    setCantidades({})
    setNumeroEditado(null)
    setError('')

    obtenerProgramas(e.id)
      .then((lista) => setProgramasDe({ equipoId: e.id, programas: lista }))
      .catch((err) => setError(mensajeDeError(err)))
    cargarCargaDelEquipo(e.id)

    // Estufas y óxido de etileno no llevan Bowie-Dick: no se consulta nada
    if (e.metodo === METODO_AUTOCLAVE) consultarBowieDick(e.id)
  }

  // Solo usamos lo que llegó si es del equipo elegido
  const programas = programasDe?.equipoId === equipoId ? programasDe.programas : []
  const pendientes = pendientesDe?.equipoId === equipoId ? pendientesDe.pendientes : []
  const propuesto = propuestoDe?.equipoId === equipoId ? propuestoDe.numero : null
  const bowieDickAprobado = bowieDickDe?.equipoId === equipoId ? bowieDickDe.aprobado : null // null = no se sabe todavía
  const numeroLote = numeroEditado ?? propuesto ?? ''

  const equipo = equipos.find((e) => e.id === equipoId)
  const programa = programas.find((p) => p.id === programaId)

  // * En el autoclave no se puede crear el lote sin el Bowie-Dick aprobado de hoy
  // * (mientras se consulta, tampoco). El back lo vuelve a controlar.
  const esAutoclave = equipo?.metodo === METODO_AUTOCLAVE
  const faltaBowieDick = esAutoclave && bowieDickAprobado !== true

  // Equipos agrupados por método, en el orden de sus ids
  const gruposDeEquipos: { metodoId: number; titulo: string; equipos: EquipoDeCarga[] }[] = []
  for (const e of [...equipos].sort((a, b) => a.metodo_id - b.metodo_id)) {
    const grupo = gruposDeEquipos.find((g) => g.metodoId === e.metodo_id)
    if (grupo) grupo.equipos.push(e)
    else gruposDeEquipos.push({ metodoId: e.metodo_id, titulo: TITULOS_DE_METODO[e.metodo] ?? e.metodo, equipos: [e] })
  }

  // Pendientes agrupados por servicio de origen
  const porServicio: { servicioId: number; servicio: string; lineas: PendienteCarga[] }[] = []
  for (const p of pendientes) {
    const grupo = porServicio.find((g) => g.servicioId === p.servicio_id)
    if (grupo) grupo.lineas.push(p)
    else porServicio.push({ servicioId: p.servicio_id, servicio: p.servicio, lineas: [p] })
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
    if (faltaBowieDick) return setError('Registrá primero el control Bowie-Dick de hoy.')
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
      // Cada par servicio + material es una sola línea, como pide la API.
      const lineas = pendientes
        .filter((p) => (cantidades[clave(p)] ?? 0) > 0)
        .map((p) => ({ servicio_id: p.servicio_id, material_id: p.material_id, cantidad: cantidades[clave(p)] }))

      const lote = await crearLote({ equipo_id: equipoId, programa_id: programaId, numero: n, lineas })

      setAviso(
        `Lote N.º ${lote.numero} creado en ${equipo.nombre} con ${lote.total_items} ${
          lote.total_items === 1 ? 'unidad' : 'unidades'
        }. Cuando termine el ciclo, cerralo desde Ciclos en curso.`,
      )

      // Limpiamos el formulario. El equipo queda elegido y se actualizan
      // sus pendientes y el número propuesto.
      setProgramaId(null)
      setCantidades({})
      setNumeroEditado(null)
      cargarCargaDelEquipo(equipoId)
      actualizarEnCurso()
    } catch (e) {
      setError(mensajeDeError(e)) // 404 o 422: muestra el detail del back
    } finally {
      setEnviando(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Control Bowie-Dick
  // ---------------------------------------------------------------------------

  function abrirBowieDick() {
    setRegistrandoBowieDick(true)
    setResultadoBowieDick('')
    setCicloBowieDick('')
    setObservacionBowieDick('')
    setErrorBowieDick('')
  }

  async function confirmarBowieDick() {
    if (!equipo) return
    if (resultadoBowieDick === '') return setErrorBowieDick('Indicá si el control salió aprobado o fallido.')
    if (resultadoBowieDick === 'fallido' && !observacionBowieDick.trim()) {
      return setErrorBowieDick('Si el control falló, la observación es obligatoria.')
    }

    setErrorBowieDick('')
    setGuardandoBowieDick(true)

    try {
      await registrarBowieDick(equipo.id, {
        resultado: resultadoBowieDick,
        numero_ciclo: cicloBowieDick.trim() || undefined,
        observacion: observacionBowieDick.trim() || undefined,
      })

      setAviso(`Bowie-Dick de ${equipo.nombre} registrado como ${resultadoBowieDick}.`)
      setRegistrandoBowieDick(false)
      setError('')
      consultarBowieDick(equipo.id) // el último de hoy es el que cuenta: preguntamos de nuevo
    } catch (e) {
      setErrorBowieDick(mensajeDeError(e))
    } finally {
      setGuardandoBowieDick(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Cierre del ciclo
  // ---------------------------------------------------------------------------

  function abrirCierre(lote: LoteResumen) {
    setCerrando(lote)
    setResultado('')
    setNumeroCiclo('')
    setObservacion('')
    setErrorCierre('')
  }

  async function confirmarCierre() {
    if (!cerrando) return
    if (resultado === '') return setErrorCierre('Indicá si el lote salió aprobado o fallido.')

    // * La API pide el N.º de ciclo como entero de 1 en adelante (obligatorio).
    // * Lo limitamos a enteros que JavaScript maneja sin perder dígitos.
    const ciclo = numeroCiclo.trim()
    if (ciclo === '') return setErrorCierre('Indicá el N.º de ciclo que imprime el ticket.')
    const n = Number(ciclo)
    if (!/^\d+$/.test(ciclo) || n < 1 || !Number.isSafeInteger(n)) {
      return setErrorCierre('El N.º de ciclo tiene que ser un número entero mayor que 0, sin puntos ni letras.')
    }
    if (resultado === 'fallido' && !observacion.trim()) {
      return setErrorCierre('Si el lote falló, la observación es obligatoria.')
    }

    setErrorCierre('')
    setConfirmando(true)

    try {
      const cerrado = await cerrarLote(cerrando.id, {
        numero_ciclo: n,
        resultado,
        observacion: observacion.trim() || undefined,
      })

      setAviso(`Lote N.º ${cerrado.numero} cerrado como ${cerrado.resultado}.`)
      setCerrando(null)
      actualizarEnCurso()
      // Si falló, su material vuelve a quedar pendiente: refrescamos la carga del equipo elegido
      if (equipoId !== null) cargarCargaDelEquipo(equipoId)
    } catch (e) {
      setErrorCierre(mensajeDeError(e)) // 404, 409 o 422: muestra el detail del back
    } finally {
      setConfirmando(false)
    }
  }

  // Parámetros del programa: los que son null no se muestran
  const datosDelCiclo = programa
    ? [
        { etiqueta: 'Temperatura', valor: conUnidad(programa.temperatura_c, ' °C') },
        { etiqueta: 'Tiempo de esterilización', valor: conUnidad(programa.tiempo_esterilizacion_min, ' min') },
        { etiqueta: 'Secado', valor: conUnidad(programa.tiempo_secado_min, ' min') },
        { etiqueta: 'Desgasificación', valor: conUnidad(programa.tiempo_desgasificacion_min, ' min') },
        { etiqueta: 'Vacío', valor: conUnidad(programa.vacio_bar, ' bar') },
        { etiqueta: 'Vapor', valor: conUnidad(programa.vapor_bar, ' bar') },
        { etiqueta: 'Pulsos', valor: conUnidad(programa.pulsos, '') },
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

      {/* Ciclos en curso: solo si hay alguno. GET /lotes?en_curso=true no trae el programa. */}
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
                    Lote N.º {l.numero} · {l.equipo.nombre} · inicio {diaHora(l.inicio)}
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
          {gruposDeEquipos.map((g) => (
            <div key={g.metodoId}>
              <Text fw={700} c="dimmed" mb="xs">
                {g.titulo}
              </Text>
              <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
                {g.equipos.map((e) => (
                  <Button
                    key={e.id}
                    size="lg"
                    h="auto"
                    py="md"
                    color="var(--gris)"
                    variant={equipoId === e.id ? 'filled' : 'default'}
                    onClick={() => elegirEquipo(e)}
                    styles={{ label: { whiteSpace: 'normal' } }}
                  >
                    {e.nombre}
                  </Button>
                ))}
              </SimpleGrid>
            </div>
          ))}
        </Stack>

        {/* Autoclave sin el Bowie-Dick aprobado de hoy */}
        {esAutoclave && bowieDickAprobado === false && (
          <Alert color="yellow" variant="light" mt="md" title="Este autoclave no tiene el control Bowie-Dick de hoy.">
            <Stack gap="sm" align="flex-start">
              <Text size="sm">
                Hasta que haya un Bowie-Dick aprobado hoy no se puede crear el lote. Si el último control de hoy
                falló, hay que repetirlo.
              </Text>
              <Button size="md" color="var(--gris)" onClick={abrirBowieDick}>
                Registrar Bowie-Dick
              </Button>
            </Stack>
          </Alert>
        )}
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
            {datosDelCiclo.length === 0 ? (
              <Text c="dimmed">Este programa no tiene parámetros cargados.</Text>
            ) : (
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
            )}
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
              <div key={g.servicioId}>
                <Text fw={700} c="dimmed" mb="xs">
                  {g.servicio}
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
                            <Text fw={700}>{p.material}</Text>
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
                              aria-label={`Quitar una unidad de ${p.material} de ${p.servicio}`}
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
                              aria-label={`Agregar una unidad de ${p.material} de ${p.servicio}`}
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

      <Button size="xl" color="var(--gris)" loading={enviando} disabled={faltaBowieDick} onClick={crear}>
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
            withAsterisk
            placeholder="Ej: 1189"
            inputMode="numeric"
            value={numeroCiclo}
            onChange={(e) => {
              setNumeroCiclo(e.currentTarget.value)
              setErrorCierre('')
            }}
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

      <Modal
        opened={registrandoBowieDick}
        onClose={() => setRegistrandoBowieDick(false)}
        title={equipo ? `Control Bowie-Dick de ${equipo.nombre}` : 'Control Bowie-Dick'}
      >
        <Stack gap="md">
          <SegmentedControl
            size="lg"
            fullWidth
            value={resultadoBowieDick}
            onChange={(valor) => {
              setResultadoBowieDick(valor as ResultadoLote)
              setErrorBowieDick('')
            }}
            color={resultadoBowieDick === 'fallido' ? 'red' : 'var(--verde)'}
            data={[
              { label: 'Aprobado', value: 'aprobado' },
              { label: 'Fallido', value: 'fallido' },
            ]}
          />

          <TextInput
            size="md"
            label="N.º de ciclo"
            placeholder="Opcional. Ej: 1188"
            inputMode="numeric"
            maxLength={20}
            value={cicloBowieDick}
            onChange={(e) => setCicloBowieDick(e.currentTarget.value)}
          />

          <Textarea
            size="md"
            autosize
            minRows={2}
            label="Observación"
            withAsterisk={resultadoBowieDick === 'fallido'}
            placeholder={
              resultadoBowieDick === 'fallido' ? 'Ej: la hoja no viró de forma pareja' : 'Opcional'
            }
            maxLength={1000}
            value={observacionBowieDick}
            onChange={(e) => {
              setObservacionBowieDick(e.currentTarget.value)
              setErrorBowieDick('')
            }}
          />

          {errorBowieDick && (
            <Alert color="red" variant="light">
              {errorBowieDick}
            </Alert>
          )}

          <Button size="lg" color="var(--gris)" loading={guardandoBowieDick} onClick={confirmarBowieDick}>
            Registrar Bowie-Dick
          </Button>
        </Stack>
      </Modal>
    </Stack>
  )
}
