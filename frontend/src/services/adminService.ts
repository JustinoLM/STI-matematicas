/**
 * Servicio del panel de administración (/admin).
 */

import apiClient, { ADMIN_TOKEN_KEY } from './api';

export interface CreateStudentPayload {
  codigo_estudiante: string;
  nombre_completo: string;
  genero: 'masculino' | 'femenino';
  password: string;
  organizacion_id?: number;
  grado_academico?: string;
  edad?: number;
}

export interface BulkStudentRow {
  codigo_estudiante: string;
  nombre_completo: string;
  genero: 'masculino' | 'femenino';
  password: string;
  organizacion_id?: number;
  grado_academico?: string;
  edad?: number;
}

export interface BulkTeacherRow {
  codigo_profesor: string;
  nombre_completo: string;
  password: string;
  institucion?: string;
  organizacion_id?: number;
  grado_academico?: string;
}

export interface BulkImportError { fila: number; codigo: string; mensaje: string; }
export interface BulkImportResult { total: number; creados: number; errores: BulkImportError[]; }
export interface ConteoHoja { hoja: string; procesados: number; creados: number; omitidos: number; }
export interface ImportResumenExcel {
  organizacion_id: number;
  organizacion_nombre: string;
  organizacion_creada: boolean;
  hojas: ConteoHoja[];
  advertencias: string[];
}

export interface CreateTeacherPayload {
  codigo_profesor: string;
  nombre_completo: string;
  password: string;
  institucion?: string;
  organizacion_id?: number;
  grado_academico?: string;
}

export interface CreateOrgPayload {
  nombre: string;
  codigo: string;
  descripcion?: string;
  ciudad?: string;
  pais?: string;
}

export interface UserCreated {
  id: number;
  tipo_usuario: string;
  codigo_estudiante?: string;
  codigo_profesor?: string;
  nombre_completo: string;
  activo: boolean;
}

export interface OrgCreated {
  id: number;
  nombre: string;
  codigo: string;
  ciudad?: string;
  pais?: string;
  post_test_activo?: boolean;
  total_profesores: number;
  total_estudiantes: number;
}

export interface OrgDetalle extends OrgCreated {
  descripcion?: string;
  profesores: Array<{ id: number; codigo: string; nombre_completo: string; tipo: string }>;
  estudiantes: Array<{ id: number; codigo: string; nombre_completo: string; tipo: string }>;
}

export interface UsuarioAdmin {
  id: number;
  codigo: string;
  nombre_completo: string;
  organizacion_id: number | null;
  institucion?: string;
  activo: boolean;
  fecha_creacion: string | null;
  ultimo_acceso: string | null;
  // Solo en profesores
  secciones_asignadas?: string[];
  // Solo en estudiantes
  puntos_totales?: number;
  grado_academico?: string;
  genero?: string;
  edad?: number | null;
  pre_test_completado?: boolean;
  post_test_completado?: boolean;
}

export interface AllUsersResponse {
  profesores: UsuarioAdmin[];
  estudiantes: UsuarioAdmin[];
}

export const adminService = {
  async crearEstudiante(data: CreateStudentPayload): Promise<UserCreated> {
    const response = await apiClient.post<UserCreated>('/auth/admin/students', data);
    return response.data;
  },
  async crearProfesor(data: CreateTeacherPayload): Promise<UserCreated> {
    const response = await apiClient.post<UserCreated>('/auth/admin/teachers', data);
    return response.data;
  },
  async crearOrganizacion(data: CreateOrgPayload): Promise<OrgCreated> {
    const response = await apiClient.post<OrgCreated>('/admin/organizations', data);
    return response.data;
  },
  async getOrganizaciones(): Promise<{ total: number; organizaciones: OrgCreated[] }> {
    const response = await apiClient.get('/admin/organizations');
    return response.data;
  },
  async getDetalleOrg(id: number): Promise<OrgDetalle> {
    const response = await apiClient.get(`/admin/organizations/${id}`);
    return response.data;
  },
  async getAllUsers(): Promise<AllUsersResponse> {
    const response = await apiClient.get('/admin/users');
    return response.data;
  },
  async asignarProfesorOrg(orgId: number, profId: number): Promise<void> {
    await apiClient.put(`/admin/organizations/${orgId}/professors/${profId}`);
  },
  async quitarProfesorOrg(orgId: number, profId: number): Promise<void> {
    await apiClient.delete(`/admin/organizations/${orgId}/professors/${profId}`);
  },
  async asignarEstudianteOrg(orgId: number, estId: number): Promise<void> {
    await apiClient.put(`/admin/organizations/${orgId}/students/${estId}`);
  },
  async quitarEstudianteOrg(orgId: number, estId: number): Promise<void> {
    await apiClient.delete(`/admin/organizations/${orgId}/students/${estId}`);
  },
  async activarPostTest(orgId: number): Promise<void> {
    await apiClient.post(`/admin/organizations/${orgId}/post-test/activate`);
  },
  async desactivarPostTest(orgId: number): Promise<void> {
    await apiClient.delete(`/admin/organizations/${orgId}/post-test/activate`);
  },
  async eliminarOrganizacion(orgId: number): Promise<void> {
    await apiClient.delete(`/admin/organizations/${orgId}`);
  },
  async eliminarProfesor(profId: number): Promise<void> {
    await apiClient.delete(`/admin/professors/${profId}`);
  },
  async eliminarEstudiante(estId: number): Promise<void> {
    await apiClient.delete(`/admin/students/${estId}`);
  },
  async bulkImportStudents(rows: BulkStudentRow[]): Promise<BulkImportResult> {
    const response = await apiClient.post<BulkImportResult>('/auth/admin/bulk/students', { estudiantes: rows });
    return response.data;
  },
  async bulkImportTeachers(rows: BulkTeacherRow[]): Promise<BulkImportResult> {
    const response = await apiClient.post<BulkImportResult>('/auth/admin/bulk/teachers', { profesores: rows });
    return response.data;
  },
  async importarExcelCompleto(archivo: File, organizacionNombre: string): Promise<ImportResumenExcel> {
    const formData = new FormData();
    formData.append('archivo', archivo);
    formData.append('organizacion_nombre', organizacionNombre);
    const response = await apiClient.post<ImportResumenExcel>('/admin/import/excel', formData);
    return response.data;
  },
  async getGradosOrg(orgId: number): Promise<string[]> {
    const response = await apiClient.get<string[]>(`/admin/organizations/${orgId}/grados`);
    return response.data;
  },
  async actualizarSeccionesProfesor(profId: number, secciones: string[]): Promise<void> {
    await apiClient.patch(`/admin/professors/${profId}/secciones`, { secciones });
  },
  async editarEstudiante(estId: number, data: {
    nombre_completo?: string;
    genero?: string;
    grado_academico?: string;
    edad?: number;
  }): Promise<void> {
    await apiClient.patch(`/admin/students/${estId}`, data);
  },
  async agregarPuntos(payload: { estudiante_id: number; puntos: number }) {
    const response = await apiClient.post('/admin/gamification/add-points', payload);
    return response.data;
  },
  async getEstadoML() {
    const response = await apiClient.get('/admin/ml/estado');
    return response.data;
  },
  async entrenarML() {
    const response = await apiClient.post('/admin/ml/entrenar');
    return response.data;
  },
  async getStatsSistema() {
    const response = await apiClient.get('/admin/sistema/stats');
    return response.data;
  },
  async exportar(key: string, orgId?: number | string, conNombres = false) {
    const response = await apiClient.get(`/admin/export/${key}`, {
      params: { ...(orgId ? { org_id: orgId } : {}), ...(conNombres ? { con_nombres: true } : {}) },
    });
    return response.data;
  },
  /** Verifica la contraseña del panel en el backend y guarda el token de administrador. */
  async login(password: string): Promise<void> {
    const response = await apiClient.post<{ access_token: string }>('/auth/admin-login', { password });
    sessionStorage.setItem(ADMIN_TOKEN_KEY, response.data.access_token);
  },
  haySesion(): boolean {
    return !!sessionStorage.getItem(ADMIN_TOKEN_KEY);
  },
  cerrarSesion(): void {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  },
};
