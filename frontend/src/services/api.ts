import axios from 'axios'

const CLAVE_TOKEN = 'ciclo_token'
// Dirección de la API. Se puede cambiar con VITE_API_URL (archivo frontend/.env).
const URL_API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export const leerToken = () => localStorage.getItem(CLAVE_TOKEN)
export const guardarToken = (token: string) => localStorage.setItem(CLAVE_TOKEN, token)
export const borrarToken = () => localStorage.removeItem(CLAVE_TOKEN)

export const api = axios.create({ baseURL: URL_API })

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