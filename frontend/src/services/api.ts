import axios from 'axios'

const CLAVE_TOKEN = 'ciclo_token'

export const leerToken = () => localStorage.getItem(CLAVE_TOKEN)
export const guardarToken = (token: string) => localStorage.setItem(CLAVE_TOKEN, token)
export const borrarToken = () => localStorage.removeItem(CLAVE_TOKEN)

// * Instancia única de Axios: todas las pantallas hablan con la API por acá.
export const api = axios.create({ baseURL: '/api' })

// Agrega el token a cada pedido
api.interceptors.request.use((config) => {
  const token = leerToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Si el token venció o no sirve, se borra y se vuelve al login.
// El propio login también responde 401 si la contraseña es incorrecta: ese caso no se toca.
api.interceptors.response.use(
  (respuesta) => respuesta,
  (error) => {
    const esLogin = error.config?.url === '/auth/login'
    if (error.response?.status === 401 && !esLogin) {
      borrarToken()
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)