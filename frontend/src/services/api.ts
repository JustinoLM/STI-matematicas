/**
 * Cliente HTTP centralizado con Axios.
 */

import axios, { AxiosError } from 'axios';

// URL base de la API
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Clave en sessionStorage del token del panel /admin (rol "admin")
export const ADMIN_TOKEN_KEY = 'admin_token';

// Rutas que usan el token de administrador en lugar del de estudiante/profesor
const esRutaAdmin = (url?: string) =>
  !!url && (url.startsWith('/admin') || url.startsWith('/auth/admin'));

// Crear instancia de Axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de request: Agregar token JWT
apiClient.interceptors.request.use(
  (config) => {
    // Rutas de administración: token de admin (sessionStorage), no el de usuario
    if (esRutaAdmin(config.url) && config.url !== '/auth/admin-login') {
      const adminToken = sessionStorage.getItem(ADMIN_TOKEN_KEY);
      if (adminToken) {
        config.headers.Authorization = `Bearer ${adminToken}`;
      }
      return config;
    }
    // Obtener token del localStorage (viene del authStore persist)
    const authStorage = localStorage.getItem('auth-storage');
    if (authStorage) {
      const { token } = JSON.parse(authStorage).state;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor de response: Manejo de errores
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Token inválido o expirado — pero NO redirigir si es el propio endpoint de login.
    // Un 401 en /auth/login significa "credenciales incorrectas", no "token expirado".
    const isLoginRequest =
      error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/admin-login');
    // Token de admin vencido o inválido: volver a pedir la contraseña del panel
    if (
      (error.response?.status === 401 || error.response?.status === 403) &&
      esRutaAdmin(error.config?.url) &&
      !isLoginRequest
    ) {
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
      window.location.href = '/admin';
      return Promise.reject(error);
    }
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('auth-storage');
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// Helper para extraer mensajes de error
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    // FastAPI validation errors (422) devuelven detail como array de objetos
    if (Array.isArray(detail)) {
      return detail.map((e: { msg?: string }) => e.msg ?? 'Error de validación').join(', ');
    }
    if (typeof detail === 'string') return detail;
    return error.message || 'Error desconocido';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Error desconocido';
};
