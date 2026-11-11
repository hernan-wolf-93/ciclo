import { useEffect, useState } from 'react'
import { ActionIcon, Button, Group, Paper, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { obtenerMateriales, obtenerServicios } from '../services/recepcionService'
import type { Material, Servicio } from '../types'

export default function Recepcion() {
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [materiales, setMateriales] = useState<Material[]>([])
  const [servicioId, setServicioId] = useState<number | null>(null)

  // * Cuántas unidades hay de cada material, por id. Ej: { 3: 2, 12: 1 }
  // * Solo guardamos los que tienen 1 o más.
  const [cantidades, setCantidades] = useState<Record<number, number>>({})

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
    </Stack>
  )
}