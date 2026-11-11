import { useEffect, useState } from 'react'
import { ActionIcon, Alert, Button, Checkbox, Group, Paper, SegmentedControl, SimpleGrid, Stack, Text, Textarea, TextInput, Title } from '@mantine/core'
import { obtenerMateriales, obtenerServicios, registrarRecepcion } from '../services/recepcionService'
import type { Material, RecepcionCreada, Servicio } from '../types'

export default function Recepcion() {
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [materiales, setMateriales] = useState<Material[]>([])
  const [servicioId, setServicioId] = useState<number | null>(null)

  // * Cuántas unidades hay de cada material, por id. Ej: { 3: 2, 12: 1 }
  // * Solo guardamos los que tienen 1 o más.
  const [cantidades, setCantidades] = useState<Record<number, number>>({})

  // * Control de piezas: arranca vacío para que el operador lo elija sí o sí
  const [piezas, setPiezas] = useState<'' | 'completo' | 'falta'>('')
  const [observacion, setObservacion] = useState('')
  // * Si falta una pieza, el operador confirma que avisó al servicio de origen
  const [avisado, setAvisado] = useState(false)

  // ? Cuando esté el login, el operador sale de la sesión y este campo se va
  const [operador, setOperador] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [registrada, setRegistrada] = useState<RecepcionCreada | null>(null)

  // Al entrar a la pantalla traemos los catálogos (por ahora, del mock)
  useEffect(() => {
    obtenerServicios().then(setServicios)
    obtenerMateriales().then(setMateriales)
  }, [])

  // Suma o resta unidades de un material (diferencia = +1 o -1)
  function cambiarCantidad(materialId: number, diferencia: number) {
    setCantidades((anteriores) => {
      const nueva = (anteriores[materialId] ?? 0) + diferencia
      const copia = { ...anteriores }

      // Si llega a 0 lo sacamos, así no mandamos materiales sin unidades
      if (nueva <= 0) delete copia[materialId]
      else copia[materialId] = nueva

      return copia
    })
  }

  const totalUnidades = Object.values(cantidades).reduce((suma, c) => suma + c, 0)

  async function registrar() {
    setRegistrada(null)

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (servicioId === null) return setError('Elegí el servicio de origen.')
    if (totalUnidades === 0) return setError('Cargá al menos un material.')
    if (piezas === '') return setError('Indicá si el material llegó completo o si falta una pieza.')
    // ! Si Salica dice que la observación no es obligatoria, borrar la línea de abajo
    if (piezas === 'falta' && observacion.trim() === '') return setError('Escribí qué pieza falta.')
    if (operador === '') return setError('Ingresá tu N.º de operador.')
    if (piezas === 'falta' && !avisado) return setError('Confirmá que le avisaste al servicio de origen.')

    setError('')
    setEnviando(true)

    try {
      // Pasamos de { 3: 2, 12: 1 } a [{ material_id: 3, cantidad: 2 }, ...]
      const items = Object.entries(cantidades).map(([id, cantidad]) => ({
        material_id: Number(id),
        cantidad,
      }))

      const resultado = await registrarRecepcion({
        servicio_id: servicioId,
        operador,
        items,
        completo: piezas === 'completo',
        observacion: observacion.trim() || undefined,
        servicio_avisado: piezas === 'falta' ? avisado : undefined,
      })

      setRegistrada(resultado)

      // Limpiamos el formulario para la próxima carga.
      // El operador queda, porque suele ser la misma persona cargando varias.
      setServicioId(null)
      setCantidades({})
      setPiezas('')
      setObservacion('')
      setAvisado(false)
    } catch {
      setError('No se pudo registrar la recepción. Probá de nuevo.')
    } finally {
      setEnviando(false)
    }
  }

  // Para mostrar el nombre del servicio en la confirmación
  const servicioRegistrado = servicios.find((s) => s.id === registrada?.servicio_id)

  return (
    <Stack gap="xl" maw={900}>
      <Title order={1}>Registrar recepción</Title>

      {/* 1. Servicio de origen: botones grandes, fáciles de tocar */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          1. Servicio de origen
        </Text>
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
          {servicios.map((s) => (
            <Button
              key={s.id}
              size="lg"
              h="auto"
              py="md"
              color="var(--rojo)"
              variant={servicioId === s.id ? 'filled' : 'default'}
              onClick={() => setServicioId(s.id)}
              styles={{ label: { whiteSpace: 'normal' } }} // para que "Unidad de Terapia Intensiva" no se corte
            >
              {s.nombre}
            </Button>
          ))}
        </SimpleGrid>
      </section>

      {/* 2. Material: cada uno con botones − y + */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          2. Material recibido
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
          {materiales.map((m) => {
            const cantidad = cantidades[m.id] ?? 0

            return (
              <Paper
                key={m.id}
                withBorder
                p="sm"
                radius="md"
                bg={cantidad > 0 ? '#fdecea' : 'white'} // se marca rosadito si tiene unidades
              >
                <Group justify="space-between" wrap="nowrap">
                  <Text fw={700}>{m.nombre}</Text>

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
                      color="var(--rojo)"
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

        <Text mt="sm" c="dimmed">
          Total: {totalUnidades} {totalUnidades === 1 ? 'unidad' : 'unidades'}
        </Text>
      </section>

      {/* 3. Control de piezas */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          3. Control de piezas
        </Text>

        <SegmentedControl
          size="lg"
          fullWidth
          value={piezas}
          onChange={(valor) => setPiezas(valor as 'completo' | 'falta')}
          color={piezas === 'falta' ? 'orange' : 'var(--verde)'}
          data={[
            { label: 'Completo', value: 'completo' },
            { label: 'Falta una pieza', value: 'falta' },
          ]}
        />

        {/* Si falta algo, el texto pide que se aclare qué */}
        <Textarea
          mt="md"
          size="md"
          autosize
          minRows={2}
          label={piezas === 'falta' ? '¿Qué pieza falta?' : 'Observación (opcional)'}
          placeholder={
            piezas === 'falta'
              ? 'Ej: falta una pinza de la caja cesárea'
              : 'Cualquier aclaración sobre el material recibido'
          }
          value={observacion}
          onChange={(e) => setObservacion(e.currentTarget.value)}
        />
        {/* Solo aparece si falta una pieza: deja registrado que el servicio ya sabe */}
        {piezas === 'falta' && (
          <Checkbox
            mt="md"
            size="md"
            color="orange"
            label="Avisé al servicio de origen que el material llegó incompleto"
            checked={avisado}
            onChange={(e) => {
              setAvisado(e.currentTarget.checked)
              setError('')
            }}
          />
        )}
      </section>

      {/* 4. Operador */}
      <section>
        <Text fw={700} size="lg" mb="sm">
          4. Operador
        </Text>
        <TextInput
          size="lg"
          maw={240}
          label="N.º de operador"
          placeholder="Ej: 1234"
          inputMode="numeric"
          value={operador}
          // Solo dejamos escribir números
          onChange={(e) => setOperador(e.currentTarget.value.replace(/\D/g, ''))}
        />
      </section>

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      {/* TODO (Salica): mostrar la hora en 24 h → agregar hour12: false y cambiar el "." final por " h." */}
      {registrada && (
        <Alert
          color="green"
          variant="light"
          title={`Recepción N.º ${registrada.id} registrada`}
          withCloseButton
          onClose={() => setRegistrada(null)}
        >
          {registrada.total_items} {registrada.total_items === 1 ? 'unidad' : 'unidades'} de{' '}
          {servicioRegistrado?.nombre} a las{' '}
          {new Date(registrada.fecha_hora).toLocaleTimeString('es-AR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
          .
        </Alert>
      )}

      <Button size="xl" color="var(--rojo)" loading={enviando} onClick={registrar}>
        Registrar recepción
      </Button>
    </Stack>
  )
}