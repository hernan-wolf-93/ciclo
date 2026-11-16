import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Alert, Button, Paper, PasswordInput, TextInput, Title } from '@mantine/core'
import { isAxiosError } from 'axios'
import { useAuth } from '../auth/useAuth'

export default function Login() {
  const { usuario, iniciarSesion } = useAuth()
  const navegar = useNavigate()
  const [numero, setNumero] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Si ya hay sesión, no tiene sentido ver el login
  if (usuario) return <Navigate to="/" replace />

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (numero.trim() === '') return setError('Ingresá tu N.º de operador.')
    if (contrasena === '') return setError('Ingresá tu contraseña.')

    setEnviando(true)
    try {
      const yo = await iniciarSesion(numero.trim(), contrasena)
      // Según el rol: el operador va directo a cargar recepciones; los administradores, al tablero
      navegar(yo.rol === 'Operador' ? '/recepcion' : '/', { replace: true })
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setError('N.º de operador o contraseña incorrectos.')
      } else if (isAxiosError(err) && !err.response) {
        setError('No se pudo conectar con el servidor. Avisá al administrador.')
      } else {
        setError('Ocurrió un error inesperado. Probá de nuevo.')
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Paper maw={380} mx="auto" mt={80} p="xl" withBorder component="form" onSubmit={enviar}>
      <Title order={2} mb="md">
        Ciclo — Ingreso
      </Title>
      {error && (
        <Alert color="red" mb="md" role="alert">
          {error}
        </Alert>
      )}
      <TextInput
        label="N.º de operador"
        inputMode="numeric"
        value={numero}
        onChange={(e) => setNumero(e.currentTarget.value.replace(/\D/g, ''))}
        autoFocus
        mb="sm"
      />
      <PasswordInput
        label="Contraseña"
        value={contrasena}
        onChange={(e) => setContrasena(e.currentTarget.value)}
        mb="lg"
      />
      <Button type="submit" fullWidth loading={enviando}>
        Ingresar
      </Button>
    </Paper>
  )
}