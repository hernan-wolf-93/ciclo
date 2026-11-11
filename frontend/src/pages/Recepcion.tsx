import { useEffect, useState } from 'react'
import { Button, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { obtenerServicios } from '../services/recepcionService'
import type { Servicio } from '../types'

export default function Recepcion() {
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [servicioId, setServicioId] = useState<number | null>(null)

  // Al entrar a la pantalla traemos los servicios (por ahora, del mock)
  useEffect(() => {
    obtenerServicios().then(setServicios)
  }, [])

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
    </Stack>
  )
}