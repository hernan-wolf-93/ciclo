import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Alert, Anchor, Button, Paper, PasswordInput, Text, TextInput, Title } from '@mantine/core'
import { isAxiosError } from 'axios'
import { useAuth } from '../auth/useAuth'
import { recuperarContrasena } from '../services/authService'

// Pantalla pública: el operador cambia su clave con el código que le dio un administrador
export default function RecuperarContrasena() {
  const { usuario } = useAuth()
  const navegar = useNavigate()
  const [numero, setNumero] = useState('')
  const [codigo, setCodigo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [repetida, setRepetida] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Si ya hay sesión, no tiene sentido recuperar la contraseña
  if (usuario) return <Navigate to="/" replace />

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setError('')

    // * Validamos de arriba hacia abajo y avisamos lo primero que falte
    if (numero.trim() === '' || codigo.trim() === '' || contrasena === '' || repetida === '')
      return setError('Completá todos los campos.')
    if (contrasena.length < 8) return setError('La contraseña nueva debe tener al menos 8 caracteres.')
    if (contrasena !== repetida) return setError('Las dos contraseñas no coinciden.')

    setEnviando(true)
    try {
      // El back acepta el código en minúsculas y con espacios: lo mandamos tal cual
      await recuperarContrasena(numero.trim(), codigo, contrasena)
      navegar('/login', {
        replace: true,
        state: { aviso: 'Contraseña cambiada. Ingresá con tu clave nueva.' },
      })
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 400) {
        // 400: número, código o vencimiento incorrectos. El back explica cuál.
        const detalle = err.response.data?.detail
        setError(typeof detalle === 'string' ? detalle : 'El código no es válido.')
      } else if (isAxiosError(err) && err.response?.status === 422) {
        setError('Revisá los datos: la contraseña debe tener entre 8 y 128 caracteres.')
      } else if (isAxiosError(err) && !err.response) {
        setError('No se pudo conectar con el servidor. Avisá al administrador.')
      } else {
        setError('Ocurrió un error inesperado. Probá de nuevo.')
      }
      setEnviando(false)
    }
  }

  return (
    <Paper maw={380} mx="auto" mt={80} p="xl" withBorder component="form" onSubmit={enviar}>
      <Title order={2} mb="md">
        Olvidé mi contraseña
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Pedile un código de recuperación a un administrador. Te lo va a dar en persona y vence a
        los 30 minutos.
      </Text>
      {error && (
        <Alert color="red" mb="md" role="alert">
          {error}
        </Alert>
      )}
      <TextInput
        label="N.º de operador"
        inputMode="numeric"
        value={numero}
        // Solo dejamos escribir números
        onChange={(e) => setNumero(e.currentTarget.value.replace(/\D/g, ''))}
        autoFocus
        mb="sm"
      />
      <TextInput
        label="Código"
        value={codigo}
        // Se muestra en mayúsculas, como lo anota el administrador
        onChange={(e) => setCodigo(e.currentTarget.value.toUpperCase())}
        autoComplete="off"
        mb="sm"
      />
      <PasswordInput
        label="Contraseña nueva (mínimo 8 caracteres)"
        value={contrasena}
        onChange={(e) => setContrasena(e.currentTarget.value)}
        autoComplete="new-password"
        mb="sm"
      />
      <PasswordInput
        label="Repetir contraseña nueva"
        value={repetida}
        onChange={(e) => setRepetida(e.currentTarget.value)}
        autoComplete="new-password"
        mb="lg"
      />
      <Button type="submit" fullWidth loading={enviando}>
        Cambiar contraseña
      </Button>
      <Anchor component={Link} to="/login" size="sm" display="block" ta="center" mt="md">
        Volver al ingreso
      </Anchor>
    </Paper>
  )
}
