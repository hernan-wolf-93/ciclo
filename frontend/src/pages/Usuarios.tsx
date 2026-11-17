import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Switch,
  Table,
  TextInput,
  Title,
} from '@mantine/core'
import { useAuth } from '../auth/useAuth'
import {
  crearUsuario,
  listarRoles,
  listarUsuarios,
  mensajeDeError,
  modificarUsuario,
} from '../services/operadoresService'
import type { Rol, UsuarioAdmin } from '../types'

// Formulario de alta: vive dentro del Modal, así se limpia solo al cerrarlo
function FormAlta({ roles, onCreado }: { roles: Rol[]; onCreado: () => void }) {
  const [numero, setNumero] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [rolId, setRolId] = useState<string | null>(roles.length === 1 ? String(roles[0].id) : null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const enviar = async () => {
    if (!numero.trim() || !contrasena || !rolId) {
      setError('Completá el N.º de operador, la contraseña y el rol.')
      return
    }
    setEnviando(true)
    try {
      await crearUsuario({
        numero_operador: numero.trim(),
        contrasena,
        rol_id: Number(rolId),
      })
      onCreado()
    } catch (e) {
      setError(mensajeDeError(e))
      setEnviando(false)
    }
  }

  return (
    <Stack>
      {error && <Alert color="red">{error}</Alert>}
      <TextInput
        label="N.º de operador"
        value={numero}
        onChange={(e) => setNumero(e.currentTarget.value)}
      />
      <PasswordInput
        label="Contraseña (mínimo 8 caracteres)"
        value={contrasena}
        onChange={(e) => setContrasena(e.currentTarget.value)}
      />
      <Select
        label="Rol"
        data={roles.map((r) => ({ value: String(r.id), label: r.nombre }))}
        value={rolId}
        onChange={setRolId}
      />
      <Button onClick={enviar} loading={enviando}>
        Crear usuario
      </Button>
    </Stack>
  )
}

// Formulario de edición: solo se puede cambiar el rol
function FormEdicion({
  usuario,
  roles,
  onGuardado,
}: {
  usuario: UsuarioAdmin
  roles: Rol[]
  onGuardado: () => void
}) {
  const actual = roles.find((r) => r.nombre === usuario.rol)
  const [rolId, setRolId] = useState<string | null>(actual ? String(actual.id) : null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const guardar = async () => {
    if (!rolId) return
    setEnviando(true)
    try {
      await modificarUsuario(usuario.id, { rol_id: Number(rolId) })
      onGuardado()
    } catch (e) {
      setError(mensajeDeError(e))
      setEnviando(false)
    }
  }

  return (
    <Stack>
      {error && <Alert color="red">{error}</Alert>}
      <TextInput label="N.º de operador" value={usuario.numero_operador} disabled />
      <Select
        label="Rol"
        data={roles.map((r) => ({ value: String(r.id), label: r.nombre }))}
        value={rolId}
        onChange={setRolId}
      />
      <Button onClick={guardar} loading={enviando}>
        Guardar cambios
      </Button>
    </Stack>
  )
}

export default function Usuarios() {
  const { usuario } = useAuth()
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([])
  const [roles, setRoles] = useState<Rol[]>([])
  const [verBajas, setVerBajas] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [altaAbierta, setAltaAbierta] = useState(false)
  const [editando, setEditando] = useState<UsuarioAdmin | null>(null)
  const [recarga, setRecarga] = useState(0)

  // Cada vez que cambia el filtro o `recarga`, se vuelve a pedir la lista
  useEffect(() => {
    let vigente = true
    listarUsuarios(verBajas ? undefined : true)
      .then((lista) => {
        if (!vigente) return
        setUsuarios(lista)
        setError(null)
      })
      .catch((e) => vigente && setError(mensajeDeError(e)))
      .finally(() => vigente && setCargando(false))
    return () => {
      vigente = false
    }
  }, [verBajas, recarga])

  useEffect(() => {
    listarRoles()
      .then(setRoles)
      .catch((e) => setError(mensajeDeError(e)))
  }, [])

  const cargar = () => setRecarga((n) => n + 1)

  // Esta pantalla es solo para administradores
  if (usuario?.rol === 'Operador') return <Navigate to="/" replace />

  const cambiarEstado = async (u: UsuarioAdmin) => {
    const accion = u.activo ? 'dar de baja' : 'reactivar'
    if (!window.confirm(`¿Querés ${accion} al operador ${u.numero_operador}?`)) return
    try {
      await modificarUsuario(u.id, { activo: !u.activo })
      cargar()
    } catch (e) {
      setError(mensajeDeError(e))
    }
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Usuarios</Title>
        <Button onClick={() => setAltaAbierta(true)}>Nuevo usuario</Button>
      </Group>

      <Switch
        label="Mostrar también los dados de baja"
        checked={verBajas}
        onChange={(e) => {
          setCargando(true)
          setVerBajas(e.currentTarget.checked)
        }}
      />

      {error && <Alert color="red">{error}</Alert>}

      {cargando ? (
        <Loader />
      ) : (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>N.º de operador</Table.Th>
              <Table.Th>Rol</Table.Th>
              <Table.Th>Estado</Table.Th>
              <Table.Th>Acciones</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {usuarios.map((u) => (
              <Table.Tr key={u.id}>
                <Table.Td>{u.numero_operador}</Table.Td>
                <Table.Td>{u.rol}</Table.Td>
                <Table.Td>
                  <Badge color={u.activo ? 'green' : 'gray'}>
                    {u.activo ? 'Activo' : 'De baja'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="default" onClick={() => setEditando(u)}>
                      Cambiar rol
                    </Button>
                    <Button
                      size="xs"
                      variant="light"
                      color={u.activo ? 'red' : 'green'}
                      onClick={() => cambiarEstado(u)}
                    >
                      {u.activo ? 'Dar de baja' : 'Reactivar'}
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={altaAbierta} onClose={() => setAltaAbierta(false)} title="Nuevo usuario">
        <FormAlta
          roles={roles}
          onCreado={() => {
            setAltaAbierta(false)
            cargar()
          }}
        />
      </Modal>

      <Modal opened={editando !== null} onClose={() => setEditando(null)} title="Cambiar rol">
        {editando && (
          <FormEdicion
            usuario={editando}
            roles={roles}
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