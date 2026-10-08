/**
 * Página de administración — Gestión de usuarios y organizaciones.
 *
 * Acceso: /admin (público, sin autenticación requerida).
 * Permite crear estudiantes, profesores y organizaciones sin usar la terminal.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  UserPlus,
  GraduationCap,
  BookOpen,
  Check,
  AlertCircle,
  Loader2,
  Building2,
  Users,
  ChevronDown,
  ChevronUp,
  X,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Copy,
  Calendar,
  Clock,
  Sparkles,
  Brain,
  ShieldCheck,
  Activity,
  RefreshCw,
  Server,
  Lock,
  Upload,
  FileSpreadsheet,
  Download,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
  Pencil,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import apiClient, { getErrorMessage, ADMIN_TOKEN_KEY } from '@/services/api';
import { reglaDeTresService, type EstudianteNotaR3 } from '@/services/reglaDeTresService';

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface CreateStudentPayload {
  codigo_estudiante: string;
  nombre_completo: string;
  genero: 'masculino' | 'femenino';
  password: string;
  organizacion_id?: number;
  grado_academico?: string;
  edad?: number;
}

interface BulkStudentRow {
  codigo_estudiante: string;
  nombre_completo: string;
  genero: 'masculino' | 'femenino';
  password: string;
  organizacion_id?: number;
  grado_academico?: string;
  edad?: number;
}

interface BulkTeacherRow {
  codigo_profesor: string;
  nombre_completo: string;
  password: string;
  institucion?: string;
  organizacion_id?: number;
  grado_academico?: string;
}

interface BulkImportError { fila: number; codigo: string; mensaje: string; }
interface BulkImportResult { total: number; creados: number; errores: BulkImportError[]; }
interface ConteoHoja { hoja: string; procesados: number; creados: number; omitidos: number; }
interface ImportResumenExcel {
  organizacion_id: number;
  organizacion_nombre: string;
  organizacion_creada: boolean;
  hojas: ConteoHoja[];
  advertencias: string[];
}

interface CreateTeacherPayload {
  codigo_profesor: string;
  nombre_completo: string;
  password: string;
  institucion?: string;
  organizacion_id?: number;
  grado_academico?: string;
}

interface CreateOrgPayload {
  nombre: string;
  codigo: string;
  descripcion?: string;
  ciudad?: string;
  pais?: string;
}

interface UserCreated {
  id: number;
  tipo_usuario: string;
  codigo_estudiante?: string;
  codigo_profesor?: string;
  nombre_completo: string;
  activo: boolean;
}

interface OrgCreated {
  id: number;
  nombre: string;
  codigo: string;
  ciudad?: string;
  pais?: string;
  post_test_activo?: boolean;
  total_profesores: number;
  total_estudiantes: number;
}

interface OrgDetalle extends OrgCreated {
  descripcion?: string;
  profesores: Array<{ id: number; codigo: string; nombre_completo: string; tipo: string }>;
  estudiantes: Array<{ id: number; codigo: string; nombre_completo: string; tipo: string }>;
}

interface UsuarioAdmin {
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
  grado_academico?: string;
  genero?: string;
  edad?: number | null;
  pre_test_completado?: boolean;
  post_test_completado?: boolean;
}

interface AllUsersResponse {
  profesores: UsuarioAdmin[];
  estudiantes: UsuarioAdmin[];
}

// ─── Servicios de admin ───────────────────────────────────────────────────────

const adminService = {
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
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatFecha(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-PA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function CopiarBtn({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false);
  const copiar = () => {
    navigator.clipboard.writeText(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
  };
  return (
    <button
      onClick={copiar}
      className="ml-1 text-gray-400 hover:text-gray-700 transition-colors"
      title="Copiar"
    >
      {copiado ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

// ─── Input de contraseña con toggle ──────────────────────────────────────────

function PasswordInput({
  id,
  value,
  onChange,
  placeholder = 'Mínimo 6 caracteres',
  required = true,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <Input
        id={id}
        type={visible ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        minLength={6}
        className="pr-10"
      />
      <button
        type="button"
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
        onClick={() => setVisible((v) => !v)}
        tabIndex={-1}
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ─── Formulario Estudiante ────────────────────────────────────────────────────

function FormEstudiante({ organizaciones }: {
  organizaciones: OrgCreated[];
}) {
  const emptyForm = {
    codigo_estudiante: '', nombre_completo: '',
    genero: 'masculino' as 'masculino' | 'femenino',
    password: '', organizacion_id: '',
    grado_academico: '', edad: '',
  };
  const [form, setForm] = useState(emptyForm);
  const [resultado, setResultado] = useState<UserCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CreateStudentPayload) => adminService.crearEstudiante(data),
    onSuccess: (data) => {
      setResultado(data);
      setError(null);
      setForm(emptyForm);
    },
    onError: (err) => {
      setError(getErrorMessage(err));
      setResultado(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      codigo_estudiante: form.codigo_estudiante.trim().toUpperCase(),
      nombre_completo: form.nombre_completo.trim(),
      genero: form.genero,
      password: form.password,
      organizacion_id: form.organizacion_id ? Number(form.organizacion_id) : undefined,
      grado_academico: form.grado_academico.trim() || undefined,
      edad: form.edad ? Number(form.edad) : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="codigo-est">Código de estudiante *</Label>
          <Input
            id="codigo-est"
            placeholder="EST001"
            value={form.codigo_estudiante}
            onChange={e => setForm(f => ({ ...f, codigo_estudiante: e.target.value }))}
            required
            minLength={5}
          />
          <p className="text-xs text-muted-foreground">Mínimo 5 caracteres. Ej: EST001</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="nombre-est">Nombre completo *</Label>
          <Input
            id="nombre-est"
            placeholder="Juan Pérez"
            value={form.nombre_completo}
            onChange={e => setForm(f => ({ ...f, nombre_completo: e.target.value }))}
            required
            minLength={3}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="genero-est">Género *</Label>
          <select
            id="genero-est"
            value={form.genero}
            onChange={e => setForm(f => ({ ...f, genero: e.target.value as 'masculino' | 'femenino' }))}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
            required
          >
            <option value="masculino">Masculino</option>
            <option value="femenino">Femenino</option>
          </select>
          <p className="text-xs text-muted-foreground">Se usa para personalizar mensajes del tutor.</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="pass-est">Contraseña inicial *</Label>
          <PasswordInput
            id="pass-est"
            value={form.password}
            onChange={v => setForm(f => ({ ...f, password: v }))}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="org-est">Organización</Label>
          <select
            id="org-est"
            value={form.organizacion_id}
            onChange={e => setForm(f => ({ ...f, organizacion_id: e.target.value }))}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">— Sin organización —</option>
            {organizaciones.map(org => (
              <option key={org.id} value={org.id}>
                {org.nombre} ({org.codigo})
              </option>
            ))}
          </select>
          {organizaciones.length === 0 && (
            <p className="text-xs text-amber-600">Crea una organización primero en la pestaña "Orgs".</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="grado-est">Grado académico</Label>
          <Input
            id="grado-est"
            placeholder="5to grado"
            value={form.grado_academico}
            onChange={e => setForm(f => ({ ...f, grado_academico: e.target.value }))}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="edad-est">Edad</Label>
          <Input
            id="edad-est"
            type="number"
            placeholder="11"
            min={3}
            max={25}
            value={form.edad}
            onChange={e => setForm(f => ({ ...f, edad: e.target.value }))}
          />
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {resultado && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          <Check className="h-4 w-4 flex-shrink-0" />
          Estudiante <strong>{resultado.nombre_completo}</strong> creado con código{' '}
          <strong>{resultado.codigo_estudiante}</strong>.
        </div>
      )}

      <Button type="submit" disabled={mutation.isPending} className="w-full">
        {mutation.isPending ? (
          <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creando…</>
        ) : (
          <><UserPlus className="h-4 w-4 mr-2" />Crear estudiante</>
        )}
      </Button>
    </form>
  );
}

// ─── Formulario Profesor ──────────────────────────────────────────────────────

function FormProfesor({ organizaciones }: {
  organizaciones: OrgCreated[];
}) {
  const [form, setForm] = useState({
    codigo_profesor: '',
    nombre_completo: '',
    password: '',
    institucion: '',
    organizacion_id: '',
    grado_academico: '',
  });
  const [resultado, setResultado] = useState<UserCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CreateTeacherPayload) => adminService.crearProfesor(data),
    onSuccess: (data) => {
      setResultado(data);
      setError(null);
      setForm({ codigo_profesor: '', nombre_completo: '', password: '', institucion: '', organizacion_id: '', grado_academico: '' });
    },
    onError: (err) => {
      setError(getErrorMessage(err));
      setResultado(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      codigo_profesor: form.codigo_profesor.trim().toUpperCase(),
      nombre_completo: form.nombre_completo.trim(),
      password: form.password,
      institucion: form.institucion.trim() || undefined,
      organizacion_id: form.organizacion_id ? Number(form.organizacion_id) : undefined,
      grado_academico: form.grado_academico.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="codigo-prof">Código de profesor *</Label>
          <Input
            id="codigo-prof"
            placeholder="PROF001"
            value={form.codigo_profesor}
            onChange={e => setForm(f => ({ ...f, codigo_profesor: e.target.value }))}
            required
            minLength={5}
          />
          <p className="text-xs text-muted-foreground">Mínimo 5 caracteres. Ej: PROF001</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="nombre-prof">Nombre completo *</Label>
          <Input
            id="nombre-prof"
            placeholder="María García"
            value={form.nombre_completo}
            onChange={e => setForm(f => ({ ...f, nombre_completo: e.target.value }))}
            required
            minLength={3}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="pass-prof">Contraseña inicial *</Label>
          <PasswordInput
            id="pass-prof"
            value={form.password}
            onChange={v => setForm(f => ({ ...f, password: v }))}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="inst-prof">
            Institución <span className="text-muted-foreground text-xs">(opcional)</span>
          </Label>
          <Input
            id="inst-prof"
            placeholder="Escuela Primaria Central"
            value={form.institucion}
            onChange={e => setForm(f => ({ ...f, institucion: e.target.value }))}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="grado-prof">
            Grado académico <span className="text-muted-foreground text-xs">(opcional)</span>
          </Label>
          <Input
            id="grado-prof"
            placeholder="Ej: Licenciatura, Maestría"
            value={form.grado_academico}
            onChange={e => setForm(f => ({ ...f, grado_academico: e.target.value }))}
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="org-prof">Organización</Label>
          <select
            id="org-prof"
            value={form.organizacion_id}
            onChange={e => {
              const orgId = e.target.value;
              const org = organizaciones.find(o => String(o.id) === orgId);
              setForm(f => ({
                ...f,
                organizacion_id: orgId,
                institucion: f.institucion || (org?.nombre ?? ''),
              }));
            }}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">— Sin organización —</option>
            {organizaciones.map(org => (
              <option key={org.id} value={org.id}>
                {org.nombre} ({org.codigo})
              </option>
            ))}
          </select>
          {organizaciones.length === 0 && (
            <p className="text-xs text-amber-600">Crea una organización primero en la pestaña "Orgs".</p>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {resultado && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          <Check className="h-4 w-4 flex-shrink-0" />
          Profesor <strong>{resultado.nombre_completo}</strong> creado con código{' '}
          <strong>{resultado.codigo_profesor}</strong>.
        </div>
      )}

      <Button type="submit" disabled={mutation.isPending} className="w-full">
        {mutation.isPending ? (
          <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creando…</>
        ) : (
          <><UserPlus className="h-4 w-4 mr-2" />Crear profesor</>
        )}
      </Button>
    </form>
  );
}

// ─── Modal de edición de estudiante ──────────────────────────────────────────

function EditarEstudianteModal({
  est,
  open,
  onClose,
  onSaved,
}: {
  est: UsuarioAdmin;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nombre, setNombre] = useState(est.nombre_completo);
  const [genero, setGenero] = useState(est.genero ?? 'masculino');
  const [grado, setGrado] = useState(est.grado_academico ?? '');
  const [edad, setEdad] = useState(est.edad != null ? String(est.edad) : '');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const handleGuardar = async () => {
    if (!nombre.trim()) { setError('El nombre no puede estar vacío'); return; }
    setGuardando(true);
    setError('');
    try {
      await adminService.editarEstudiante(est.id, {
        nombre_completo: nombre.trim(),
        genero,
        grado_academico: grado.trim() || undefined,
        edad: edad ? Number(edad) : undefined,
      });
      onSaved();
      onClose();
    } catch (e: any) {
      setError(getErrorMessage(e));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Editar estudiante</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Nombre completo</Label>
            <Input value={nombre} onChange={e => setNombre(e.target.value)} className="h-8 text-sm mt-1" />
          </div>
          <div>
            <Label className="text-xs">Género</Label>
            <select
              value={genero}
              onChange={e => setGenero(e.target.value)}
              className="mt-1 w-full h-8 text-sm border rounded-md px-2 bg-background"
            >
              <option value="masculino">Masculino</option>
              <option value="femenino">Femenino</option>
            </select>
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <Label className="text-xs">Sección</Label>
              <Input value={grado} onChange={e => setGrado(e.target.value)} placeholder="ej. 6D" className="h-8 text-sm mt-1" />
            </div>
            <div className="w-20">
              <Label className="text-xs">Edad</Label>
              <Input value={edad} onChange={e => setEdad(e.target.value)} type="number" min={3} max={25} className="h-8 text-sm mt-1" />
            </div>
          </div>
          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose} disabled={guardando}>Cancelar</Button>
          <Button size="sm" onClick={handleGuardar} disabled={guardando}>
            {guardando ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Check className="h-3 w-3 mr-1" />}
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Panel de secciones de un profesor ───────────────────────────────────────

function SeccionesProfesorPanel({
  prof,
  gradosDisponibles,
  onSaved,
}: {
  prof: UsuarioAdmin;
  gradosDisponibles: string[];
  onSaved: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [seleccionadas, setSeleccionadas] = useState<string[]>(prof.secciones_asignadas ?? []);
  const [guardando, setGuardando] = useState(false);

  const toggle = (g: string) =>
    setSeleccionadas(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]);

  const handleGuardar = async () => {
    setGuardando(true);
    try {
      await adminService.actualizarSeccionesProfesor(prof.id, seleccionadas);
      onSaved();
      setEditando(false);
    } finally {
      setGuardando(false);
    }
  };

  const handleCancelar = () => {
    setSeleccionadas(prof.secciones_asignadas ?? []);
    setEditando(false);
  };

  const actuales = prof.secciones_asignadas ?? [];

  return (
    <div className="mt-1.5">
      {!editando ? (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-gray-500">Secciones:</span>
          {actuales.length === 0 ? (
            <span className="text-xs text-gray-400 italic">Todos los estudiantes de la org</span>
          ) : (
            actuales.map(g => (
              <span key={g} className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-mono">{g}</span>
            ))
          )}
          {gradosDisponibles.length > 0 && (
            <button
              onClick={() => setEditando(true)}
              className="text-xs text-blue-500 hover:text-blue-700 underline ml-1"
            >
              {actuales.length === 0 ? 'Asignar secciones' : 'Editar'}
            </button>
          )}
          {gradosDisponibles.length === 0 && actuales.length === 0 && (
            <span className="text-xs text-gray-400 italic">(los estudiantes de la org necesitan grado_academico asignado)</span>
          )}
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-3 mt-1 border border-gray-200 space-y-2">
          <p className="text-xs font-medium text-gray-600">
            Selecciona las secciones que enseña este profesor:
          </p>
          <div className="flex flex-wrap gap-2">
            {gradosDisponibles.map(g => {
              const checked = seleccionadas.includes(g);
              return (
                <label key={g} className={[
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-full border cursor-pointer text-sm font-mono transition-colors',
                  checked
                    ? 'bg-blue-100 border-blue-400 text-blue-800'
                    : 'bg-white border-gray-300 text-gray-600 hover:border-blue-300',
                ].join(' ')}>
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={() => toggle(g)}
                  />
                  {checked && <Check className="h-3 w-3 text-blue-600" />}
                  {g}
                </label>
              );
            })}
          </div>
          {seleccionadas.length === 0 && (
            <p className="text-xs text-amber-600">
              ⚠️ Sin secciones → verá todos los estudiantes de la organización.
            </p>
          )}
          <div className="flex gap-2 pt-1">
            <Button size="sm" className="h-7 text-xs" onClick={handleGuardar} disabled={guardando}>
              {guardando ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Check className="h-3 w-3 mr-1" />}
              Guardar
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleCancelar} disabled={guardando}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tarjeta de Organización (detalle + asignación) ───────────────────────────

function OrgCard({ org, allUsers, notasR3, onRefresh }: {
  org: OrgCreated;
  allUsers: AllUsersResponse | undefined;
  notasR3: EstudianteNotaR3[] | undefined;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [togglingPostTest, setTogglingPostTest] = useState(false);
  const [editandoEst, setEditandoEst] = useState<UsuarioAdmin | null>(null);
  const notaR3ById = new Map((notasR3 ?? []).map(n => [n.estudiante_id, n]));

  const handleTogglePostTest = async () => {
    setTogglingPostTest(true);
    try {
      if (org.post_test_activo) {
        await adminService.desactivarPostTest(org.id);
      } else {
        await adminService.activarPostTest(org.id);
      }
      onRefresh();
    } finally {
      setTogglingPostTest(false);
    }
  };

  const { data: detalle, refetch } = useQuery({
    queryKey: ['org-detalle', org.id],
    queryFn: () => adminService.getDetalleOrg(org.id),
    enabled: expanded,
    staleTime: 0,
  });

  // Grados disponibles en la org (basado en grado_academico de sus estudiantes)
  const { data: gradosDisponibles = [] } = useQuery({
    queryKey: ['org-grados', org.id],
    queryFn: () => adminService.getGradosOrg(org.id),
    enabled: expanded,
    staleTime: 30_000,
  });

  const handleRefetchAll = () => { refetch(); onRefresh(); };

  const handleAsignarProf = async (profId: number) => {
    setLoadingId(`prof-${profId}`);
    try { await adminService.asignarProfesorOrg(org.id, profId); await refetch(); onRefresh(); }
    finally { setLoadingId(null); }
  };
  const handleQuitarProf = async (profId: number) => {
    setLoadingId(`prof-${profId}`);
    try { await adminService.quitarProfesorOrg(org.id, profId); await refetch(); onRefresh(); }
    finally { setLoadingId(null); }
  };
  const handleAsignarEst = async (estId: number) => {
    setLoadingId(`est-${estId}`);
    try { await adminService.asignarEstudianteOrg(org.id, estId); await refetch(); onRefresh(); }
    finally { setLoadingId(null); }
  };
  const handleQuitarEst = async (estId: number) => {
    setLoadingId(`est-${estId}`);
    try { await adminService.quitarEstudianteOrg(org.id, estId); await refetch(); onRefresh(); }
    finally { setLoadingId(null); }
  };

  const profsMiembros = detalle?.profesores ?? [];
  const estsMiembros = detalle?.estudiantes ?? [];
  const profsMiembrosIds = new Set(profsMiembros.map(p => p.id));
  const estsMiembrosIds = new Set(estsMiembros.map(e => e.id));
  const profsDisponibles = (allUsers?.profesores ?? []).filter(p => !profsMiembrosIds.has(p.id));
  const estsDisponibles = (allUsers?.estudiantes ?? []).filter(e => !estsMiembrosIds.has(e.id));

  return (
    <Card className="border border-gray-200">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-blue-500" />
              {org.nombre}
              <Badge variant="outline" className="text-xs font-mono">{org.codigo}</Badge>
            </CardTitle>
            {(org.ciudad || org.pais) && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {[org.ciudad, org.pais].filter(Boolean).join(', ')}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              <span className="font-medium">{org.total_profesores}</span> prof ·{' '}
              <span className="font-medium">{org.total_estudiantes}</span> est
            </span>
            {/* Post-test toggle */}
            <Button
              variant={org.post_test_activo ? 'default' : 'outline'}
              size="sm"
              className={`h-7 text-xs gap-1 ${org.post_test_activo ? 'bg-orange-500 hover:bg-orange-600 border-orange-500' : ''}`}
              disabled={togglingPostTest}
              onClick={handleTogglePostTest}
              title={org.post_test_activo ? 'Desactivar post-test' : 'Activar post-test final'}
            >
              {togglingPostTest
                ? <Loader2 className="h-3 w-3 animate-spin" />
                : <ClipboardCheck className="h-3 w-3" />}
              Post-test
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setExpanded(v => !v)}>
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-4">
          {!detalle ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            </div>
          ) : (
            <>
              {/* Profesores */}
              <div>
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-1">
                  <GraduationCap className="h-4 w-4" /> Profesores ({profsMiembros.length})
                </h4>
                <div className="space-y-2">
                  {profsMiembros.map(p => {
                    // Buscar datos del profesor en allUsers para tener secciones_asignadas
                    const profData = allUsers?.profesores.find(u => u.id === p.id);
                    return (
                      <div key={p.id} className="bg-blue-50 rounded px-3 py-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-blue-600 mr-2">{p.codigo}</span>
                          <span className="flex-1">{p.nombre_completo}</span>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                            disabled={loadingId === `prof-${p.id}`} onClick={() => handleQuitarProf(p.id)}>
                            {loadingId === `prof-${p.id}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                          </Button>
                        </div>
                        {/* Panel de secciones asignadas */}
                        {profData && (
                          <SeccionesProfesorPanel
                            prof={profData}
                            gradosDisponibles={gradosDisponibles}
                            onSaved={handleRefetchAll}
                          />
                        )}
                      </div>
                    );
                  })}
                  {profsMiembros.length === 0 && <p className="text-xs text-muted-foreground italic px-1">Sin profesores asignados.</p>}
                </div>
                {profsDisponibles.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-muted-foreground mb-1">Agregar profesor:</p>
                    <div className="flex flex-wrap gap-1">
                      {profsDisponibles.map(p => (
                        <Button key={p.id} variant="outline" size="sm" className="h-7 text-xs"
                          disabled={loadingId === `prof-${p.id}`} onClick={() => handleAsignarProf(p.id)}>
                          {loadingId === `prof-${p.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Plus className="h-3 w-3 mr-1" />}
                          {p.codigo}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t pt-3">
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-1">
                  <BookOpen className="h-4 w-4" /> Estudiantes ({estsMiembros.length})
                </h4>
                <div className="space-y-1">
                  {estsMiembros.map(e => {
                    const estData = allUsers?.estudiantes.find(u => u.id === e.id);
                    const notaR3 = notaR3ById.get(e.id);
                    return (
                      <div key={e.id} className="flex items-center justify-between bg-green-50 rounded px-3 py-1.5 text-sm">
                        <span className="font-mono text-xs text-green-600 mr-2">{e.codigo}</span>
                        <span className="flex-1">{e.nombre_completo}</span>
                        {estData?.grado_academico && (
                          <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-mono mr-2">
                            {estData.grado_academico}
                          </span>
                        )}
                        {estData?.pre_test_completado && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-semibold mr-1" title="Pre-test completado">
                            Pre ✓
                          </span>
                        )}
                        {estData?.post_test_completado && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded font-semibold mr-1" title="Post-test completado">
                            Post ✓
                          </span>
                        )}
                        {notaR3?.tiene_practica && (
                          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-semibold mr-1" title={`Regla de 3: ${notaR3.nota_pct?.toFixed(1)}%`}>
                            R3 {notaR3.nota_pct?.toFixed(0)}%
                          </span>
                        )}
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-gray-400 hover:text-gray-700 mr-1"
                          onClick={() => setEditandoEst(estData ?? null)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                          disabled={loadingId === `est-${e.id}`} onClick={() => handleQuitarEst(e.id)}>
                          {loadingId === `est-${e.id}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                        </Button>
                      </div>
                    );
                  })}
                  {estsMiembros.length === 0 && <p className="text-xs text-muted-foreground italic px-1">Sin estudiantes asignados.</p>}
                </div>
                {estsDisponibles.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-muted-foreground mb-1">Agregar estudiante:</p>
                    <div className="flex flex-wrap gap-1">
                      {estsDisponibles.map(e => (
                        <Button key={e.id} variant="outline" size="sm" className="h-7 text-xs"
                          disabled={loadingId === `est-${e.id}`} onClick={() => handleAsignarEst(e.id)}>
                          {loadingId === `est-${e.id}` ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Plus className="h-3 w-3 mr-1" />}
                          {e.codigo}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </CardContent>
      )}
      {editandoEst && (
        <EditarEstudianteModal
          est={editandoEst}
          open={!!editandoEst}
          onClose={() => setEditandoEst(null)}
          onSaved={() => { handleRefetchAll(); setEditandoEst(null); }}
        />
      )}
    </Card>
  );
}

// ─── Sección Organizaciones ───────────────────────────────────────────────────

function SeccionOrganizaciones() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    nombre: '', codigo: '', descripcion: '', ciudad: 'Ciudad de Panamá', pais: 'Panamá',
  });
  const [resultado, setResultado] = useState<OrgCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: orgsData, refetch: refetchOrgs, isLoading: loadingOrgs } = useQuery({
    queryKey: ['admin-organizaciones'], queryFn: () => adminService.getOrganizaciones(), staleTime: 0,
  });
  const { data: allUsers } = useQuery({
    queryKey: ['admin-all-users'], queryFn: () => adminService.getAllUsers(), staleTime: 0,
  });
  const { data: notasR3Data } = useQuery({
    queryKey: ['admin-regla-de-tres-notas'], queryFn: () => reglaDeTresService.obtenerNotasAdmin(), staleTime: 0,
  });

  const mutation = useMutation({
    mutationFn: (data: CreateOrgPayload) => adminService.crearOrganizacion(data),
    onSuccess: (data) => {
      setResultado(data);
      setError(null);
      // Reset con defaults correctos (Panamá, no Colombia)
      setForm({ nombre: '', codigo: '', descripcion: '', ciudad: 'Ciudad de Panamá', pais: 'Panamá' });
      refetchOrgs();
    },
    onError: (err) => { setError(getErrorMessage(err)); setResultado(null); },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      nombre: form.nombre.trim(),
      codigo: form.codigo.trim().toUpperCase(),
      descripcion: form.descripcion.trim() || undefined,
      ciudad: form.ciudad.trim() || undefined,
      pais: form.pais.trim() || 'Panamá',
    });
  };

  const handleRefreshAll = () => {
    refetchOrgs();
    queryClient.invalidateQueries({ queryKey: ['admin-all-users'] });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Nueva Organización</CardTitle>
          <CardDescription>Crea un colegio o institución para agrupar profesores y estudiantes.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="org-nombre">Nombre *</Label>
                <Input id="org-nombre" placeholder="Escuela Primaria Central" value={form.nombre}
                  onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} required minLength={3} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-codigo">Código único *</Label>
                <Input id="org-codigo" placeholder="EPC001" value={form.codigo}
                  onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))} required minLength={3} />
                <p className="text-xs text-muted-foreground">Se convertirá a mayúsculas.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-ciudad">Ciudad</Label>
                <Input id="org-ciudad" placeholder="Ciudad de Panamá" value={form.ciudad}
                  onChange={e => setForm(f => ({ ...f, ciudad: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-pais">País</Label>
                <Input id="org-pais" placeholder="Panamá" value={form.pais}
                  onChange={e => setForm(f => ({ ...f, pais: e.target.value }))} />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="org-desc">Descripción (opcional)</Label>
                <Input id="org-desc" placeholder="Breve descripción de la organización" value={form.descripcion}
                  onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))} />
              </div>
            </div>
            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />{error}
              </div>
            )}
            {resultado && (
              <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                <Check className="h-4 w-4 flex-shrink-0" />
                Organización <strong>{resultado.nombre}</strong> creada con código <strong>{resultado.codigo}</strong>.
              </div>
            )}
            <Button type="submit" disabled={mutation.isPending} className="w-full">
              {mutation.isPending ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creando…</> : <><Building2 className="h-4 w-4 mr-2" />Crear organización</>}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div>
        <h3 className="text-base font-semibold mb-3 flex items-center gap-2">
          <Users className="h-4 w-4" />Organizaciones existentes
          {orgsData && <Badge variant="secondary">{orgsData.total}</Badge>}
        </h3>
        {loadingOrgs ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="space-y-3">
            {(orgsData?.organizaciones ?? []).map(org => (
              <OrgCard key={org.id} org={org} allUsers={allUsers} notasR3={notasR3Data?.estudiantes} onRefresh={handleRefreshAll} />
            ))}
            {orgsData?.total === 0 && (
              <p className="text-sm text-muted-foreground text-center py-6">Aún no hay organizaciones. Crea la primera arriba.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sección Ver Usuarios ─────────────────────────────────────────────────────

function SeccionVerUsuarios() {
  const [editandoEst, setEditandoEst] = useState<UsuarioAdmin | null>(null);
  // Claves colapsadas: "org-{orgId}" y "sec-{orgId}-{secNombre}"
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const toggleCollapse = (key: string) =>
    setCollapsed(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const { data: allUsers, isLoading: loadingUsers, refetch } = useQuery({
    queryKey: ['admin-all-users-view'],
    queryFn: () => adminService.getAllUsers(),
    staleTime: 0,
  });
  const { data: orgsData, isLoading: loadingOrgs } = useQuery({
    queryKey: ['admin-organizaciones-view'],
    queryFn: () => adminService.getOrganizaciones(),
    staleTime: 0,
  });
  const { data: notasR3Data } = useQuery({
    queryKey: ['admin-regla-de-tres-notas'],
    queryFn: () => reglaDeTresService.obtenerNotasAdmin(),
    staleTime: 0,
  });
  const notaR3ById = new Map((notasR3Data?.estudiantes ?? []).map(n => [n.estudiante_id, n]));

  const isLoading = loadingUsers || loadingOrgs;

  // Mapa orgId → nombre
  const orgNombre = (id: number | null) => {
    if (!id) return null;
    return orgsData?.organizaciones.find(o => o.id === id)?.nombre ?? `Org #${id}`;
  };

  // Filas de la tabla — compartida entre estudiantes y profesores
  const FilaUsuario = ({ u, tipo }: { u: UsuarioAdmin; tipo: 'estudiante' | 'profesor' }) => (
    <tr className="hover:bg-muted/40">
      <td className="px-3 py-2">
        <div className="flex items-center">
          <code className={`text-xs px-1.5 py-0.5 rounded font-mono ${tipo === 'estudiante' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'}`}>
            {u.codigo}
          </code>
          <CopiarBtn texto={u.codigo} />
        </div>
      </td>
      <td className="px-3 py-2 font-medium">{u.nombre_completo}</td>
      {tipo === 'estudiante' && (
        <td className="px-3 py-2">
          {u.grado_academico
            ? <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-mono">{u.grado_academico}</span>
            : <span className="text-xs text-muted-foreground italic">—</span>}
        </td>
      )}
      {tipo === 'profesor' && (
        <td className="px-3 py-2 text-xs text-muted-foreground">{u.institucion || '—'}</td>
      )}
      {tipo === 'estudiante' && (
        <td className="px-3 py-2">
          <div className="flex gap-1 flex-wrap">
            {u.pre_test_completado
              ? <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-semibold" title="Pre-test completado">Pre ✓</span>
              : <span className="text-xs bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded" title="Pre-test pendiente">Pre —</span>}
            {u.post_test_completado && (
              <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded font-semibold" title="Post-test completado">Post ✓</span>
            )}
          </div>
        </td>
      )}
      {tipo === 'estudiante' && (
        <td className="px-3 py-2">
          {(() => {
            const nota = notaR3ById.get(u.id);
            if (!nota?.tiene_practica) {
              return <span className="text-xs text-muted-foreground italic">Sin practicar</span>;
            }
            return (
              <Badge variant={nota.nota_pct! >= 60 ? 'default' : 'secondary'} className="text-xs">
                {nota.correctos}/{nota.total} · {nota.nota_pct!.toFixed(1)}%
              </Badge>
            );
          })()}
        </td>
      )}
      <td className="px-3 py-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1"><Calendar className="h-3 w-3" />{formatFecha(u.fecha_creacion)}</div>
      </td>
      <td className="px-3 py-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1"><Clock className="h-3 w-3" />{formatFecha(u.ultimo_acceso)}</div>
      </td>
      <td className="px-3 py-2">
        <Badge variant={u.activo ? 'default' : 'secondary'} className="text-xs">
          {u.activo ? 'Activo' : 'Inactivo'}
        </Badge>
      </td>
      <td className="px-3 py-2">
        {tipo === 'estudiante' && (
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-gray-400 hover:text-gray-700"
            onClick={() => setEditandoEst(u)}>
            <Pencil className="h-3 w-3" />
          </Button>
        )}
      </td>
    </tr>
  );

  const TablaHeader = ({ tipo }: { tipo: 'estudiante' | 'profesor' }) => (
    <thead>
      <tr className="bg-muted text-left text-xs">
        <th className="px-3 py-1.5 font-semibold">Código</th>
        <th className="px-3 py-1.5 font-semibold">Nombre</th>
        {tipo === 'estudiante' && <th className="px-3 py-1.5 font-semibold">Sección</th>}
        {tipo === 'profesor'   && <th className="px-3 py-1.5 font-semibold">Institución</th>}
        {tipo === 'estudiante' && <th className="px-3 py-1.5 font-semibold">Pruebas</th>}
        {tipo === 'estudiante' && <th className="px-3 py-1.5 font-semibold">Regla de 3</th>}
        <th className="px-3 py-1.5 font-semibold">Creado</th>
        <th className="px-3 py-1.5 font-semibold">Último acceso</th>
        <th className="px-3 py-1.5 font-semibold">Estado</th>
        <th className="px-3 py-1.5 font-semibold"></th>
      </tr>
    </thead>
  );

  // Agrupa estudiantes: orgId → seccion → lista
  const estudiantesPorOrgYSeccion = (() => {
    const estudiantes = allUsers?.estudiantes ?? [];
    // Obtener orgIds únicos (null = sin org), ordenados: con org primero
    const orgIds = [...new Set(estudiantes.map(e => e.organizacion_id))].sort((a, b) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return (orgNombre(a) ?? '').localeCompare(orgNombre(b) ?? '');
    });
    return orgIds.map(orgId => {
      const deOrg = estudiantes.filter(e => e.organizacion_id === orgId);
      // Secciones únicas dentro de esta org, ordenadas
      const secciones = [...new Set(deOrg.map(e => e.grado_academico ?? ''))].sort((a, b) => {
        if (a === '') return 1;
        if (b === '') return -1;
        return a.localeCompare(b);
      });
      return {
        orgId,
        nombre: orgNombre(orgId) ?? 'Sin organización',
        secciones: secciones.map(sec => ({
          nombre: sec || 'Sin sección',
          usuarios: deOrg
            .filter(e => (e.grado_academico ?? '') === sec)
            .sort((a, b) => a.nombre_completo.localeCompare(b.nombre_completo)),
        })),
      };
    });
  })();

  // Agrupa profesores: orgId → lista
  const profesoresPorOrg = (() => {
    const profesores = allUsers?.profesores ?? [];
    const orgIds = [...new Set(profesores.map(p => p.organizacion_id))].sort((a, b) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return (orgNombre(a) ?? '').localeCompare(orgNombre(b) ?? '');
    });
    return orgIds.map(orgId => ({
      orgId,
      nombre: orgNombre(orgId) ?? 'Sin organización',
      usuarios: profesores
        .filter(p => p.organizacion_id === orgId)
        .sort((a, b) => a.nombre_completo.localeCompare(b.nombre_completo)),
    }));
  })();

  const totalEst = allUsers?.estudiantes.length ?? 0;
  const totalProf = allUsers?.profesores.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Controles */}
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-1" />Actualizar
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <div className="space-y-8">

          {/* ── Estudiantes por organización → sección ── */}
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <BookOpen className="h-4 w-4 text-green-600" />
              Estudiantes
              <Badge variant="secondary">{totalEst}</Badge>
            </h3>
            <div className="space-y-5">
              {estudiantesPorOrgYSeccion.map(org => {
                const orgKey = `org-est-${org.orgId ?? 'none'}`;
                const orgCollapsed = collapsed.has(orgKey);
                return (
                  <div key={org.orgId ?? 'sin-org'} className="rounded-xl border border-gray-200 overflow-hidden">
                    {/* Cabecera organización — clicable */}
                    <button
                      onClick={() => toggleCollapse(orgKey)}
                      className="w-full bg-gray-50 px-4 py-2 flex items-center gap-2 border-b border-gray-200 hover:bg-gray-100 transition-colors text-left"
                    >
                      {orgCollapsed
                        ? <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
                        : <ChevronUp className="h-4 w-4 text-gray-400 shrink-0" />}
                      <Building2 className="h-4 w-4 text-gray-400 shrink-0" />
                      <span className="font-semibold text-sm text-gray-700">{org.nombre}</span>
                      <Badge variant="outline" className="text-xs ml-auto">
                        {org.secciones.reduce((s, sec) => s + sec.usuarios.length, 0)} estudiantes
                      </Badge>
                    </button>
                    {/* Secciones — visibles solo si org expandida */}
                    {!orgCollapsed && org.secciones.map(sec => {
                      const secKey = `sec-est-${org.orgId ?? 'none'}-${sec.nombre}`;
                      const secCollapsed = collapsed.has(secKey);
                      return (
                        <div key={sec.nombre} className="border-b border-gray-100 last:border-0">
                          {/* Cabecera sección — clicable */}
                          <button
                            onClick={() => toggleCollapse(secKey)}
                            className="w-full bg-green-50/60 px-4 py-1.5 flex items-center gap-2 hover:bg-green-50 transition-colors text-left"
                          >
                            {secCollapsed
                              ? <ChevronDown className="h-3 w-3 text-green-500 shrink-0" />
                              : <ChevronUp className="h-3 w-3 text-green-500 shrink-0" />}
                            <span className="text-xs font-semibold text-green-700 font-mono">{sec.nombre}</span>
                            <span className="text-xs text-green-600 ml-auto">
                              {sec.usuarios.length} estudiante{sec.usuarios.length !== 1 ? 's' : ''}
                            </span>
                          </button>
                          {!secCollapsed && (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <TablaHeader tipo="estudiante" />
                                <tbody className="divide-y divide-gray-50">
                                  {sec.usuarios.map(u => <FilaUsuario key={u.id} u={u} tipo="estudiante" />)}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
              {totalEst === 0 && (
                <p className="text-center text-sm text-muted-foreground py-4">Sin estudiantes registrados.</p>
              )}
            </div>
          </div>

          {/* ── Profesores por organización ── */}
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <GraduationCap className="h-4 w-4 text-blue-600" />
              Profesores
              <Badge variant="secondary">{totalProf}</Badge>
            </h3>
            <div className="space-y-3">
              {profesoresPorOrg.map(org => {
                const orgKey = `org-prof-${org.orgId ?? 'none'}`;
                const orgCollapsed = collapsed.has(orgKey);
                return (
                  <div key={org.orgId ?? 'sin-org'} className="rounded-xl border border-gray-200 overflow-hidden">
                    <button
                      onClick={() => toggleCollapse(orgKey)}
                      className="w-full bg-gray-50 px-4 py-2 flex items-center gap-2 border-b border-gray-200 hover:bg-gray-100 transition-colors text-left"
                    >
                      {orgCollapsed
                        ? <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
                        : <ChevronUp className="h-4 w-4 text-gray-400 shrink-0" />}
                      <Building2 className="h-4 w-4 text-gray-400 shrink-0" />
                      <span className="font-semibold text-sm text-gray-700">{org.nombre}</span>
                      <Badge variant="outline" className="text-xs ml-auto">
                        {org.usuarios.length} profesor{org.usuarios.length !== 1 ? 'es' : ''}
                      </Badge>
                    </button>
                    {!orgCollapsed && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <TablaHeader tipo="profesor" />
                          <tbody className="divide-y divide-gray-50">
                            {org.usuarios.map(u => <FilaUsuario key={u.id} u={u} tipo="profesor" />)}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
              {totalProf === 0 && (
                <p className="text-center text-sm text-muted-foreground py-4">Sin profesores registrados.</p>
              )}
            </div>
          </div>

        </div>
      )}
      {editandoEst && (
        <EditarEstudianteModal
          est={editandoEst}
          open={!!editandoEst}
          onClose={() => setEditandoEst(null)}
          onSaved={() => { refetch(); setEditandoEst(null); }}
        />
      )}
    </div>
  );
}

// ─── Sección Eliminar ─────────────────────────────────────────────────────────

function FilaEliminable({
  etiqueta, nombre, onEliminar, color = 'gray',
}: {
  etiqueta: string; nombre: string;
  onEliminar: () => Promise<void>;
  color?: 'blue' | 'green' | 'purple' | 'gray';
}) {
  const [confirmando, setConfirmando] = useState(false);
  const [cargando, setCargando] = useState(false);

  const colores: Record<string, string> = {
    blue: 'bg-blue-50 border-blue-100',
    green: 'bg-green-50 border-green-100',
    purple: 'bg-purple-50 border-purple-100',
    gray: 'bg-gray-50 border-gray-100',
  };

  const handleEliminar = async () => {
    setCargando(true);
    try { await onEliminar(); }
    finally { setCargando(false); setConfirmando(false); }
  };

  return (
    <div className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-sm ${colores[color]}`}>
      <span className="font-mono text-xs font-semibold w-20 shrink-0">{etiqueta}</span>
      <span className="flex-1 truncate">{nombre}</span>
      {!confirmando ? (
        <Button variant="ghost" size="sm" className="h-7 px-2 text-red-400 hover:text-red-600 hover:bg-red-50 shrink-0"
          onClick={() => setConfirmando(true)}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      ) : (
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-xs text-red-600 font-medium">¿Seguro?</span>
          <Button variant="destructive" size="sm" className="h-7 px-2 text-xs" disabled={cargando} onClick={handleEliminar}>
            {cargando ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Sí, borrar'}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setConfirmando(false)}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
    </div>
  );
}

function SeccionEliminar() {
  const queryClient = useQueryClient();
  const { data: allUsers, refetch: refetchUsers, isLoading: loadingUsers } = useQuery({
    queryKey: ['admin-all-users-delete'], queryFn: () => adminService.getAllUsers(), staleTime: 0,
  });
  const { data: orgsData, refetch: refetchOrgs, isLoading: loadingOrgs } = useQuery({
    queryKey: ['admin-organizaciones-delete'], queryFn: () => adminService.getOrganizaciones(), staleTime: 0,
  });

  const refetchAll = () => {
    refetchUsers(); refetchOrgs();
    queryClient.invalidateQueries({ queryKey: ['admin-organizaciones'] });
    queryClient.invalidateQueries({ queryKey: ['admin-all-users'] });
    queryClient.invalidateQueries({ queryKey: ['admin-all-users-view'] });
  };

  return (
    <Card className="border-red-100">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-red-700">
          <Trash2 className="h-5 w-5" />Eliminar usuarios y organizaciones
        </CardTitle>
        <CardDescription>Las eliminaciones son permanentes. Los datos no podrán recuperarse.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {(loadingUsers || loadingOrgs) ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <>
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <Building2 className="h-4 w-4 text-purple-500" />Organizaciones ({orgsData?.total ?? 0})
              </h4>
              <div className="space-y-1.5">
                {(orgsData?.organizaciones ?? []).map(org => (
                  <FilaEliminable key={org.id} etiqueta={org.codigo} nombre={org.nombre} color="purple"
                    onEliminar={async () => { await adminService.eliminarOrganizacion(org.id); refetchAll(); }} />
                ))}
                {orgsData?.total === 0 && <p className="text-xs text-muted-foreground italic">Sin organizaciones.</p>}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <GraduationCap className="h-4 w-4 text-blue-500" />Profesores ({allUsers?.profesores.length ?? 0})
              </h4>
              <div className="space-y-1.5">
                {(allUsers?.profesores ?? []).map(p => (
                  <FilaEliminable key={p.id} etiqueta={p.codigo} nombre={p.nombre_completo} color="blue"
                    onEliminar={async () => { await adminService.eliminarProfesor(p.id); refetchAll(); }} />
                ))}
                {(allUsers?.profesores ?? []).length === 0 && <p className="text-xs text-muted-foreground italic">Sin profesores.</p>}
              </div>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-green-500" />Estudiantes ({allUsers?.estudiantes.length ?? 0})
              </h4>
              <div className="space-y-1.5">
                {(allUsers?.estudiantes ?? []).map(e => (
                  <FilaEliminable key={e.id} etiqueta={e.codigo} nombre={e.nombre_completo} color="green"
                    onEliminar={async () => { await adminService.eliminarEstudiante(e.id); refetchAll(); }} />
                ))}
                {(allUsers?.estudiantes ?? []).length === 0 && <p className="text-xs text-muted-foreground italic">Sin estudiantes.</p>}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Sección: Agregar puntos ──────────────────────────────────────────────────

function SeccionAgregarPuntos() {
  const queryClient = useQueryClient();
  const [estudianteId, setEstudianteId] = useState('');
  const [puntos, setPuntos] = useState('');
  const [resultado, setResultado] = useState<{ nombre: string; nuevo_saldo: number } | null>(null);

  const { data: usersData } = useQuery({
    queryKey: ['admin-usuarios'],
    queryFn: () => apiClient.get('/admin/users').then(r => r.data),
    staleTime: 30 * 1000,
  });
  const estudiantes: { id: number; nombre_completo: string; codigo: string; puntos_totales: number }[] =
    usersData?.estudiantes ?? [];

  const mutation = useMutation({
    mutationFn: (payload: { estudiante_id: number; puntos: number }) =>
      apiClient.post('/admin/gamification/add-points', payload).then(r => r.data),
    onSuccess: (data) => {
      setResultado({ nombre: data.nombre, nuevo_saldo: data.nuevo_saldo });
      setPuntos('');
      queryClient.invalidateQueries({ queryKey: ['admin-usuarios'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!estudianteId || !puntos) return;
    setResultado(null);
    mutation.mutate({ estudiante_id: Number(estudianteId), puntos: Number(puntos) });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-500" />
          Agregar Puntos (Testing)
        </CardTitle>
        <CardDescription>Añade puntos manualmente a un estudiante para probar la tienda y el sistema.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4 max-w-sm">
          <div className="space-y-2">
            <Label htmlFor="estudiante-sel">Estudiante</Label>
            <select
              id="estudiante-sel"
              value={estudianteId}
              onChange={e => { setEstudianteId(e.target.value); setResultado(null); }}
              className="w-full border border-input bg-background rounded-md px-3 py-2 text-sm"
              required
            >
              <option value="">Seleccionar estudiante...</option>
              {estudiantes.map(e => (
                <option key={e.id} value={e.id}>
                  {e.nombre_completo} ({e.codigo}) — {e.puntos_totales} pts
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="puntos-input">Puntos a agregar</Label>
            <Input
              id="puntos-input"
              type="number"
              min={1}
              max={99999}
              placeholder="Ej: 500"
              value={puntos}
              onChange={e => setPuntos(e.target.value)}
              required
            />
          </div>

          <Button type="submit" disabled={mutation.isPending} className="w-full bg-yellow-500 hover:bg-yellow-600 text-white">
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
            Agregar Puntos
          </Button>

          {mutation.isError && (
            <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-md">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {getErrorMessage(mutation.error)}
            </div>
          )}

          {resultado && (
            <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 p-3 rounded-md">
              <Check className="h-4 w-4 flex-shrink-0" />
              <span>
                <strong>{resultado.nombre}</strong> ahora tiene{' '}
                <strong>{resultado.nuevo_saldo.toLocaleString()} puntos</strong>
              </span>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

// ─── Tab: Machine Learning ────────────────────────────────────────────────────

function TabML() {
  const queryClient = useQueryClient();

  const { data: estado, isLoading: cargandoEstado } = useQuery({
    queryKey: ['admin-ml-estado'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/ml/estado');
      return res.data as {
        clustering_entrenado: boolean;
        prediccion_entrenado: boolean;
        scaler_disponible: boolean;
        umbrales_por_perfil: Record<string, number>;
      };
    },
    staleTime: 30 * 1000,
  });

  const entrenarMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/admin/ml/entrenar');
      return res.data as {
        success: boolean;
        mensaje: string;
        total_perfiles?: number;
        perfiles_validos?: number;
        reclasificados?: number;
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-ml-estado'] });
    },
  });

  const perfilesLabel: Record<string, { label: string; color: string }> = {
    rapido_preciso: { label: 'Rápido y Preciso', color: 'bg-green-100 text-green-800' },
    cuidadoso_metodico: { label: 'Cuidadoso y Metódico', color: 'bg-blue-100 text-blue-800' },
    impulsivo: { label: 'Impulsivo', color: 'bg-orange-100 text-orange-800' },
    en_desarrollo: { label: 'En Desarrollo', color: 'bg-purple-100 text-purple-800' },
    no_clasificado: { label: 'No Clasificado', color: 'bg-gray-100 text-gray-600' },
  };

  return (
    <div className="space-y-4">
      {/* Estado del modelo */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-600" />
            Estado del Modelo K-Means
          </CardTitle>
          <CardDescription>Clustering de perfiles de aprendizaje (k=4)</CardDescription>
        </CardHeader>
        <CardContent>
          {cargandoEstado ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Consultando estado...
            </div>
          ) : estado ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  { label: 'Clustering', activo: estado.clustering_entrenado },
                  { label: 'Scaler', activo: estado.scaler_disponible },
                  { label: 'Predicción', activo: estado.prediccion_entrenado },
                ].map(({ label, activo }) => (
                  <div key={label} className={`flex items-center gap-2 rounded-lg p-3 ${activo ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                    <div className={`h-2.5 w-2.5 rounded-full ${activo ? 'bg-green-500' : 'bg-gray-400'}`} />
                    <span className="text-sm font-medium">{label}</span>
                    <span className={`ml-auto text-xs font-semibold ${activo ? 'text-green-700' : 'text-gray-500'}`}>
                      {activo ? 'Activo' : 'Sin modelo'}
                    </span>
                  </div>
                ))}
              </div>

              {/* Umbrales por perfil */}
              <div>
                <p className="text-sm font-medium mb-2">Umbrales de promoción por perfil</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(estado.umbrales_por_perfil).map(([perfil, umbral]) => {
                    const info = perfilesLabel[perfil] ?? { label: perfil, color: 'bg-gray-100 text-gray-700' };
                    return (
                      <div key={perfil} className={`flex items-center justify-between rounded-md px-3 py-2 text-xs ${info.color}`}>
                        <span>{info.label}</span>
                        <span className="font-bold ml-2">{umbral} ✓</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Entrenar */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-blue-600" />
            Entrenar / Re-entrenar Modelo
          </CardTitle>
          <CardDescription>
            Usa todos los perfiles con ≥3 sesiones. Requiere mínimo 10 estudiantes válidos.
            Tras entrenar, reclasifica a todos los estudiantes automáticamente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={() => entrenarMutation.mutate()}
            disabled={entrenarMutation.isPending}
            className="w-full sm:w-auto"
          >
            {entrenarMutation.isPending
              ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Entrenando...</>
              : <><Brain className="h-4 w-4 mr-2" /> Entrenar ahora</>
            }
          </Button>

          {entrenarMutation.isError && (
            <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              {getErrorMessage(entrenarMutation.error)}
            </div>
          )}

          {entrenarMutation.isSuccess && entrenarMutation.data && (
            <div className={`rounded-lg p-4 border ${entrenarMutation.data.success ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
              <div className="flex items-start gap-2">
                {entrenarMutation.data.success
                  ? <Check className="h-4 w-4 text-green-700 mt-0.5 flex-shrink-0" />
                  : <AlertCircle className="h-4 w-4 text-amber-700 mt-0.5 flex-shrink-0" />
                }
                <div className="space-y-1">
                  <p className={`text-sm font-medium ${entrenarMutation.data.success ? 'text-green-800' : 'text-amber-800'}`}>
                    {entrenarMutation.data.mensaje}
                  </p>
                  {entrenarMutation.data.success && (
                    <div className="flex gap-4 text-xs text-green-700 mt-2">
                      <span>Perfiles totales: <strong>{entrenarMutation.data.total_perfiles}</strong></span>
                      <span>Válidos: <strong>{entrenarMutation.data.perfiles_validos}</strong></span>
                      <span>Reclasificados: <strong>{entrenarMutation.data.reclasificados}</strong></span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            El sistema también entrena automáticamente cada 3 días si hay suficientes datos.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Tab: Sistema ─────────────────────────────────────────────────────────────

function TabSistema() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin-sistema-stats'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/sistema/stats');
      return res.data as {
        total_estudiantes: number;
        total_profesores: number;
        total_grupos: number;
        total_organizaciones: number;
        sesiones_hoy: number;
        sesiones_semana: number;
        sesiones_activas: number;
        total_sesiones: number;
        perfiles_clasificados: number;
      };
    },
    staleTime: 60 * 1000,
  });

  const stats = [
    { label: 'Estudiantes', value: data?.total_estudiantes, icon: BookOpen, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Profesores', value: data?.total_profesores, icon: GraduationCap, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Grupos', value: data?.total_grupos, icon: Users, color: 'text-violet-600', bg: 'bg-violet-50' },
    { label: 'Organizaciones', value: data?.total_organizaciones, icon: Building2, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Sesiones hoy', value: data?.sesiones_hoy, icon: Activity, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Sesiones (7 días)', value: data?.sesiones_semana, icon: Calendar, color: 'text-teal-600', bg: 'bg-teal-50' },
    { label: 'Sesiones activas', value: data?.sesiones_activas, icon: Clock, color: 'text-orange-600', bg: 'bg-orange-50' },
    { label: 'Total sesiones', value: data?.total_sesiones, icon: Server, color: 'text-gray-600', bg: 'bg-gray-50' },
    { label: 'Perfiles ML', value: data?.perfiles_clasificados, icon: Brain, color: 'text-purple-600', bg: 'bg-purple-50' },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-gray-600" />
              Estadísticas del Sistema
            </CardTitle>
            <CardDescription>Vista general del estado actual del STI</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Cargando estadísticas...
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {stats.map(({ label, value, icon: Icon, color, bg }) => (
              <div key={label} className={`rounded-xl p-4 ${bg} flex items-center gap-3`}>
                <div className={`p-2 rounded-lg bg-white shadow-sm`}>
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className={`text-xl font-bold ${color}`}>{value ?? '—'}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Password Gate ─────────────────────────────────────────────────────────────

function PasswordGate({ onAcceso }: { onAcceso: () => void }) {
  const [pwd, setPwd] = useState('');
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState('');

  const [enviando, setEnviando] = useState(false);

  // La contraseña se verifica en el backend (POST /auth/admin-login), que
  // devuelve un token con rol de administrador.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const res = await apiClient.post<{ access_token: string }>('/auth/admin-login', { password: pwd });
      sessionStorage.setItem(ADMIN_TOKEN_KEY, res.data.access_token);
      onAcceso();
    } catch (err) {
      setError(getErrorMessage(err));
      setPwd('');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center space-y-2">
          <div className="flex justify-center">
            <div className="p-3 rounded-full bg-blue-100">
              <Lock className="h-6 w-6 text-blue-700" />
            </div>
          </div>
          <CardTitle>Panel de Administración</CardTitle>
          <CardDescription>Ingresa la contraseña para continuar</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Input
                type={visible ? 'text' : 'password'}
                placeholder="Contraseña de administrador"
                value={pwd}
                onChange={e => { setPwd(e.target.value); setError(''); }}
                className="pr-10"
                autoFocus
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
                onClick={() => setVisible(v => !v)}
                tabIndex={-1}
              >
                {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" /> {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={enviando || !pwd}>
              <ShieldCheck className="h-4 w-4 mr-2" /> Ingresar
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Importación Masiva ───────────────────────────────────────────────────────



function FormImportarMasivo({ organizaciones }: { organizaciones: OrgCreated[] }) {
  const [tipo, setTipo] = useState<'estudiantes' | 'profesores' | 'excel_completo'>('estudiantes');
  const [filasEst, setFilasEst] = useState<BulkStudentRow[]>([]);
  const [filasProf, setFilasProf] = useState<BulkTeacherRow[]>([]);
  const [resultado, setResultado] = useState<BulkImportResult | null>(null);
  const [importando, setImportando] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  // ── Excel completo (8 hojas, sandbox) ────────────────────────────────────
  const [archivoExcel, setArchivoExcel] = useState<File | null>(null);
  const [orgDestino, setOrgDestino] = useState(() => `Sandbox - ${new Date().toISOString().slice(0, 10)}`);
  const [resumenExcel, setResumenExcel] = useState<ImportResumenExcel | null>(null);
  const [importandoExcel, setImportandoExcel] = useState(false);
  const [errorExcel, setErrorExcel] = useState<string | null>(null);

  const handleImportarExcelCompleto = async () => {
    if (!archivoExcel || !orgDestino.trim()) return;
    setImportandoExcel(true);
    setErrorExcel(null);
    setResumenExcel(null);
    try {
      const res = await adminService.importarExcelCompleto(archivoExcel, orgDestino.trim());
      setResumenExcel(res);
      setArchivoExcel(null);
    } catch (err) {
      setErrorExcel(getErrorMessage(err));
    } finally {
      setImportandoExcel(false);
    }
  };

  const filas = tipo === 'estudiantes' ? filasEst : filasProf;

  // ── Leer archivo CSV o Excel ─────────────────────────────────────────────
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setParseError(null);
    setResultado(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = new Uint8Array(ev.target!.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows: Record<string, string>[] = XLSX.utils.sheet_to_json(ws, { defval: '' });

        if (tipo === 'estudiantes') {
          const parsed = rows.map((r, i) => {
            const codigo = String(r['codigo_estudiante'] || r['codigo'] || '').trim().toUpperCase();
            // Soporta nombre_completo OR nombre + apellido como columnas separadas
            const nombreBase = String(r['nombre_completo'] || r['nombre'] || '').trim();
            const apellido = String(r['apellido'] || '').trim();
            const nombre = apellido ? `${nombreBase} ${apellido}` : nombreBase;
            // Password puede ser fórmula de Excel que genera número → convertir a string
            const password = String(r['password'] || r['contraseña'] || r['clave'] || '').trim();
            if (!codigo || !nombre || !password) throw new Error(`Fila ${i + 2}: faltan campos obligatorios (codigo, nombre, password)`);
            return {
              codigo_estudiante: codigo,
              nombre_completo: nombre,
              genero: (String(r['genero'] || 'masculino').toLowerCase() === 'femenino' ? 'femenino' : 'masculino') as 'masculino' | 'femenino',
              password,
              organizacion_id: r['organizacion_id'] ? Number(r['organizacion_id']) : undefined,
              grado_academico: String(r['grado_academico'] || '').trim() || undefined,
              edad: r['edad'] ? Number(r['edad']) : undefined,
            } as BulkStudentRow;
          });
          setFilasEst(parsed);
        } else {
          const parsed = rows.map((r, i) => {
            const codigo = String(r['codigo_profesor'] || r['codigo'] || '').trim().toUpperCase();
            const nombre = String(r['nombre_completo'] || r['nombre'] || '').trim();
            const password = String(r['password'] || r['contraseña'] || '').trim();
            if (!codigo || !nombre || !password) throw new Error(`Fila ${i + 2}: faltan campos obligatorios (codigo, nombre, password)`);
            const orgId = r['organizacion_id'] ? Number(r['organizacion_id']) : undefined;
            const institucionArchivo = String(r['institucion'] || '').trim();
            const orgNombre = orgId ? organizaciones.find(o => o.id === orgId)?.nombre : undefined;
            return {
              codigo_profesor: codigo,
              nombre_completo: nombre,
              password,
              institucion: institucionArchivo || orgNombre || undefined,
              organizacion_id: orgId,
              grado_academico: String(r['grado_academico'] || '').trim() || undefined,
            } as BulkTeacherRow;
          });
          setFilasProf(parsed);
        }
      } catch (err) {
        setParseError(err instanceof Error ? err.message : 'Error al leer el archivo');
        if (tipo === 'estudiantes') setFilasEst([]);
        else setFilasProf([]);
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = '';
  };

  // ── Importar ─────────────────────────────────────────────────────────────
  const handleImportar = async () => {
    setImportando(true);
    setResultado(null);
    try {
      const res = tipo === 'estudiantes'
        ? await adminService.bulkImportStudents(filasEst)
        : await adminService.bulkImportTeachers(filasProf);
      setResultado(res);
      if (tipo === 'estudiantes') setFilasEst([]);
      else setFilasProf([]);
    } catch (err) {
      setParseError(getErrorMessage(err));
    } finally {
      setImportando(false);
    }
  };

  // ── Descargar plantilla ───────────────────────────────────────────────────
  const descargarPlantilla = () => {
    const wb = XLSX.utils.book_new();

    if (tipo === 'estudiantes') {
      const wsData = XLSX.utils.aoa_to_sheet([
        ['codigo_estudiante', 'nombre', 'apellido', 'genero', 'password', 'organizacion_id', 'grado_academico', 'edad'],
        ['EST001', 'Juan', 'Pérez', 'masculino', 'temp123', organizaciones[0]?.id ?? '', '6A', 11],
        ['EST002', 'María', 'García', 'femenino', 'temp123', organizaciones[0]?.id ?? '', '6A', 11],
      ]);
      XLSX.utils.book_append_sheet(wb, wsData, 'Estudiantes');
    } else {
      const wsData = XLSX.utils.aoa_to_sheet([
        ['codigo_profesor', 'nombre_completo', 'password', 'institucion', 'organizacion_id', 'grado_academico'],
        ['PROF001', 'Ana Martínez', 'temp123', 'Escuela Central', organizaciones[0]?.id ?? '', '5to grado'],
        ['PROF002', 'Carlos López', 'temp123', '', '', '6to grado'],
      ]);
      XLSX.utils.book_append_sheet(wb, wsData, 'Profesores');
    }

    // Segunda hoja: catálogo de organizaciones disponibles
    const wsOrgs = XLSX.utils.aoa_to_sheet([
      ['ID', 'Nombre', 'Código'],
      ...organizaciones.map(o => [o.id, o.nombre, o.codigo]),
    ]);
    XLSX.utils.book_append_sheet(wb, wsOrgs, 'Organizaciones');

    XLSX.writeFile(wb, tipo === 'estudiantes' ? 'plantilla_estudiantes.xlsx' : 'plantilla_profesores.xlsx');
  };

  return (
    <div className="space-y-4">
      {/* Selector de tipo */}
      <div className="flex gap-2">
        <Button
          variant={tipo === 'estudiantes' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setTipo('estudiantes'); setResultado(null); setParseError(null); }}
        >
          <GraduationCap className="h-4 w-4 mr-1.5" /> Estudiantes
        </Button>
        <Button
          variant={tipo === 'profesores' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setTipo('profesores'); setResultado(null); setParseError(null); }}
        >
          <BookOpen className="h-4 w-4 mr-1.5" /> Profesores
        </Button>
        <Button
          variant={tipo === 'excel_completo' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setTipo('excel_completo'); setResultado(null); setParseError(null); }}
        >
          <FileSpreadsheet className="h-4 w-4 mr-1.5" /> Excel completo (sandbox)
        </Button>
        {tipo !== 'excel_completo' && (
          <Button variant="outline" size="sm" onClick={descargarPlantilla} className="ml-auto">
            <Download className="h-4 w-4 mr-1.5" /> Descargar plantilla
          </Button>
        )}
      </div>

      {tipo === 'excel_completo' ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
            Importa un Excel con el mismo formato que exportamos (Estudiantes, Diagnóstico, Sesiones,
            Niveles Actuales, Medallas, Tienda). Todo queda aislado en la organización que indiques
            abajo — se crea si no existe — así que <strong>nunca afecta datos de otras organizaciones</strong>.
          </div>

          <div>
            <Label htmlFor="org-destino">Organización destino</Label>
            <Input
              id="org-destino"
              value={orgDestino}
              onChange={(e) => setOrgDestino(e.target.value)}
              placeholder="Sandbox - prueba"
            />
          </div>

          <label className="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-8 cursor-pointer hover:bg-gray-100 transition-colors">
            <FileSpreadsheet className="h-10 w-10 text-gray-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700">
                {archivoExcel ? archivoExcel.name : 'Haz clic para seleccionar el Excel completo'}
              </p>
              <p className="text-xs text-gray-500 mt-1">.xlsx con las 8 hojas del export</p>
            </div>
            <input
              type="file"
              accept=".xlsx,.xlsm"
              className="hidden"
              onChange={(e) => { setArchivoExcel(e.target.files?.[0] ?? null); setResumenExcel(null); setErrorExcel(null); }}
            />
          </label>

          {errorExcel && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              {errorExcel}
            </div>
          )}

          <Button
            onClick={handleImportarExcelCompleto}
            disabled={!archivoExcel || !orgDestino.trim() || importandoExcel}
            className="w-full"
          >
            {importandoExcel ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Importando…</>
            ) : (
              <><Upload className="h-4 w-4 mr-2" />Importar a "{orgDestino || '…'}"</>
            )}
          </Button>

          {resumenExcel && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm font-medium text-green-800">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                Importado a "{resumenExcel.organizacion_nombre}"
                {resumenExcel.organizacion_creada ? ' (organización nueva)' : ' (organización existente)'}.
              </div>
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Hoja</th>
                      <th className="px-3 py-2 text-left font-medium">Procesados</th>
                      <th className="px-3 py-2 text-left font-medium">Creados</th>
                      <th className="px-3 py-2 text-left font-medium">Omitidos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumenExcel.hojas.map((h) => (
                      <tr key={h.hoja} className="border-b last:border-0">
                        <td className="px-3 py-1.5 font-medium">{h.hoja}</td>
                        <td className="px-3 py-1.5">{h.procesados}</td>
                        <td className="px-3 py-1.5 text-green-700">{h.creados}</td>
                        <td className="px-3 py-1.5 text-gray-500">{h.omitidos}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {resumenExcel.advertencias.length > 0 && (
                <div className="rounded-lg border border-amber-200 overflow-hidden">
                  <p className="px-3 py-2 text-xs font-semibold text-amber-700 bg-amber-50 border-b">
                    Advertencias ({resumenExcel.advertencias.length})
                  </p>
                  <div className="max-h-40 overflow-y-auto">
                    {resumenExcel.advertencias.map((a, i) => (
                      <p key={i} className="px-3 py-1.5 text-xs text-gray-600 border-b last:border-0">{a}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <>
      {/* Zona de carga */}
      <label className="flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-8 cursor-pointer hover:bg-gray-100 transition-colors">
        <FileSpreadsheet className="h-10 w-10 text-gray-400" />
        <div className="text-center">
          <p className="text-sm font-medium text-gray-700">Haz clic para seleccionar un archivo</p>
          <p className="text-xs text-gray-500 mt-1">CSV o Excel (.xlsx, .xls) — Máx. 500 filas</p>
        </div>
        <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFile} />
      </label>

      {/* Error de parseo */}
      {parseError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          {parseError}
        </div>
      )}

      {/* Preview de filas */}
      {filas.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">
            Vista previa — <span className="text-blue-600">{filas.length} {tipo}</span> listos para importar
          </p>
          <div className="overflow-x-auto rounded-lg border max-h-64">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {tipo === 'estudiantes' ? (
                    <>
                      <th className="px-3 py-2 text-left font-medium">Código</th>
                      <th className="px-3 py-2 text-left font-medium">Nombre</th>
                      <th className="px-3 py-2 text-left font-medium">Género</th>
                      <th className="px-3 py-2 text-left font-medium">Grado</th>
                      <th className="px-3 py-2 text-left font-medium">Edad</th>
                      <th className="px-3 py-2 text-left font-medium">Org.</th>
                    </>
                  ) : (
                    <>
                      <th className="px-3 py-2 text-left font-medium">Código</th>
                      <th className="px-3 py-2 text-left font-medium">Nombre</th>
                      <th className="px-3 py-2 text-left font-medium">Grado</th>
                      <th className="px-3 py-2 text-left font-medium">Institución</th>
                      <th className="px-3 py-2 text-left font-medium">Org.</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {filas.slice(0, 20).map((fila, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    {tipo === 'estudiantes' ? (() => {
                      const f = fila as BulkStudentRow;
                      const org = organizaciones.find(o => o.id === f.organizacion_id);
                      return (
                        <>
                          <td className="px-3 py-1.5 font-mono">{f.codigo_estudiante}</td>
                          <td className="px-3 py-1.5">{f.nombre_completo}</td>
                          <td className="px-3 py-1.5">{f.genero}</td>
                          <td className="px-3 py-1.5">{f.grado_academico || '—'}</td>
                          <td className="px-3 py-1.5">{f.edad ?? '—'}</td>
                          <td className="px-3 py-1.5">{org ? org.codigo : '—'}</td>
                        </>
                      );
                    })() : (() => {
                      const f = fila as BulkTeacherRow;
                      const org = organizaciones.find(o => o.id === f.organizacion_id);
                      return (
                        <>
                          <td className="px-3 py-1.5 font-mono">{f.codigo_profesor}</td>
                          <td className="px-3 py-1.5">{f.nombre_completo}</td>
                          <td className="px-3 py-1.5">{f.grado_academico || '—'}</td>
                          <td className="px-3 py-1.5">{f.institucion || '—'}</td>
                          <td className="px-3 py-1.5">{org ? org.codigo : '—'}</td>
                        </>
                      );
                    })()}
                  </tr>
                ))}
              </tbody>
            </table>
            {filas.length > 20 && (
              <p className="px-3 py-2 text-xs text-gray-500">
                … y {filas.length - 20} filas más (no se muestran en la vista previa)
              </p>
            )}
          </div>

          <Button onClick={handleImportar} disabled={importando} className="w-full">
            {importando ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Importando…</>
            ) : (
              <><Upload className="h-4 w-4 mr-2" />Importar {filas.length} {tipo}</>
            )}
          </Button>
        </div>
      )}

      {/* Resultado */}
      {resultado && (
        <div className="space-y-3">
          <div className={`flex items-center gap-2 rounded-lg border p-3 text-sm font-medium ${resultado.errores.length === 0 ? 'border-green-200 bg-green-50 text-green-800' : 'border-amber-200 bg-amber-50 text-amber-800'}`}>
            {resultado.errores.length === 0
              ? <CheckCircle2 className="h-5 w-5 text-green-600" />
              : <AlertCircle className="h-5 w-5 text-amber-600" />}
            {resultado.creados} de {resultado.total} creados exitosamente.
            {resultado.errores.length > 0 && ` ${resultado.errores.length} con error.`}
          </div>
          {resultado.errores.length > 0 && (
            <div className="rounded-lg border border-red-200 overflow-hidden">
              <p className="px-3 py-2 text-xs font-semibold text-red-700 bg-red-50 border-b">Errores</p>
              {resultado.errores.map((err, i) => (
                <div key={i} className="flex items-start gap-2 px-3 py-1.5 text-xs border-b last:border-0">
                  <XCircle className="h-3.5 w-3.5 mt-0.5 text-red-500 flex-shrink-0" />
                  <span className="font-mono text-gray-600 w-20 flex-shrink-0">Fila {err.fila} · {err.codigo}</span>
                  <span className="text-red-700">{err.mensaje}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
}

// ─── Tab Exportar ─────────────────────────────────────────────────────────────

interface ExportDataset { columnas: string[]; filas: Record<string, unknown>[]; }

const ENDPOINTS_EXPORT = [
  { key: 'estudiantes', label: 'Estudiantes',     desc: 'Listado completo de estudiantes con datos básicos y contraseñas.', sheet: 'Estudiantes' },
  { key: 'diagnostico', label: 'Pre vs Post-test', desc: 'Comparación pre-test / post-test por estudiante con delta de mejora por operación.', sheet: 'Diagnóstico' },
  { key: 'sesiones',  label: 'Sesiones',         desc: 'Historial de sesiones de práctica completadas.',         sheet: 'Sesiones' },
  { key: 'niveles',   label: 'Niveles',           desc: 'Evolución de niveles e instantánea actual.',             sheet: null /* two sheets */ },
  { key: 'medallas',  label: 'Medallas',          desc: 'Medallas obtenidas por los estudiantes.',                sheet: 'Medallas' },
  { key: 'tienda',    label: 'Tienda',            desc: 'Compras realizadas en la tienda de recompensas.',        sheet: 'Tienda' },
  { key: 'resumen',   label: 'Resumen por org',   desc: 'Agregado por organización: sesiones, precisión, etc.',   sheet: 'Resumen' },
] as const;

type ExportKey = (typeof ENDPOINTS_EXPORT)[number]['key'];

function TabExportar({ organizaciones }: { organizaciones: OrgCreated[] }) {
  const [orgFiltro, setOrgFiltro] = useState<string>('');
  const [descargando, setDescargando] = useState<ExportKey | null>(null);
  const [descargandoTodo, setDescargandoTodo] = useState(false);
  const [msg, setMsg] = useState<{ tipo: 'ok' | 'err'; texto: string } | null>(null);

  const orgParam = orgFiltro ? `?org_id=${orgFiltro}` : '';

  async function fetchDataset(key: ExportKey): Promise<{ data: ExportDataset; data2?: ExportDataset; label2?: string }> {
    const res = await apiClient.get(`/admin/export/${key}${orgParam}`);
    if (key === 'niveles') {
      return { data: res.data.historial, data2: res.data.nivel_actual, label2: 'Niveles Actuales' };
    }
    return { data: res.data };
  }

  function datasetToSheet(dataset: ExportDataset) {
    const rows = dataset.filas.map(f => {
      const row: Record<string, unknown> = {};
      for (const col of dataset.columnas) row[col] = f[col] ?? '';
      return row;
    });
    return XLSX.utils.json_to_sheet(rows, { header: dataset.columnas });
  }

  async function descargarUno(ep: (typeof ENDPOINTS_EXPORT)[number]) {
    setDescargando(ep.key);
    setMsg(null);
    try {
      const { data, data2, label2 } = await fetchDataset(ep.key);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, datasetToSheet(data), ep.sheet ?? ep.label);
      if (data2) XLSX.utils.book_append_sheet(wb, datasetToSheet(data2), label2!);
      const orgSuffix = orgFiltro ? `_org${orgFiltro}` : '';
      XLSX.writeFile(wb, `STI_${ep.key}${orgSuffix}.xlsx`);
      setMsg({ tipo: 'ok', texto: `"${ep.label}" descargado correctamente.` });
    } catch {
      setMsg({ tipo: 'err', texto: `Error al descargar "${ep.label}".` });
    } finally {
      setDescargando(null);
    }
  }

  async function descargarTodo() {
    setDescargandoTodo(true);
    setMsg(null);
    try {
      const wb = XLSX.utils.book_new();
      for (const ep of ENDPOINTS_EXPORT) {
        const { data, data2, label2 } = await fetchDataset(ep.key);
        XLSX.utils.book_append_sheet(wb, datasetToSheet(data), ep.sheet ?? ep.label);
        if (data2) XLSX.utils.book_append_sheet(wb, datasetToSheet(data2), label2!);
      }
      const orgSuffix = orgFiltro ? `_org${orgFiltro}` : '_todas';
      XLSX.writeFile(wb, `STI_exportacion_completa${orgSuffix}.xlsx`);
      setMsg({ tipo: 'ok', texto: 'Exportación completa descargada.' });
    } catch {
      setMsg({ tipo: 'err', texto: 'Error al generar la exportación completa.' });
    } finally {
      setDescargandoTodo(false);
    }
  }

  return (
    <div className="space-y-4 mt-4">
      {/* Filtro de organización */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="h-4 w-4 text-blue-600" />
            Exportar datos de investigación
          </CardTitle>
          <CardDescription>
            Descarga los registros del sistema en formato Excel para análisis estadístico en la tesis.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs mb-1 block">Filtrar por organización (opcional)</Label>
              <select
                value={orgFiltro}
                onChange={e => setOrgFiltro(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">— Todas las organizaciones —</option>
                {organizaciones.map(o => (
                  <option key={o.id} value={String(o.id)}>{o.nombre}</option>
                ))}
              </select>
            </div>
            <Button
              onClick={descargarTodo}
              disabled={descargandoTodo}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {descargandoTodo
                ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generando…</>
                : <><FileSpreadsheet className="h-4 w-4 mr-2" />Descargar todo</>}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Mensaje de estado */}
      {msg && (
        <div className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm ${
          msg.tipo === 'ok'
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {msg.tipo === 'ok'
            ? <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            : <XCircle className="h-4 w-4 flex-shrink-0" />}
          {msg.texto}
        </div>
      )}

      {/* Tarjetas por dataset */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {ENDPOINTS_EXPORT.map(ep => (
          <Card key={ep.key} className="flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{ep.label}</CardTitle>
              <CardDescription className="text-xs">{ep.desc}</CardDescription>
            </CardHeader>
            <CardContent className="mt-auto pt-0">
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => descargarUno(ep)}
                disabled={descargando === ep.key}
              >
                {descargando === ep.key
                  ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Descargando…</>
                  : <><Download className="h-3.5 w-3.5 mr-1.5" />Descargar .xlsx</>}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function AdminPage() {
  const [autenticado, setAutenticado] = useState(() =>
    !!sessionStorage.getItem(ADMIN_TOKEN_KEY)
  );

  // Lista de organizaciones disponibles para los dropdowns (compartida entre tabs)
  const { data: orgsData } = useQuery({
    queryKey: ['admin-organizaciones'],
    queryFn: () => adminService.getOrganizaciones(),
    staleTime: 30 * 1000,
    enabled: autenticado,
  });
  const organizaciones = orgsData?.organizaciones ?? [];

  if (!autenticado) {
    return <PasswordGate onAcceso={() => setAutenticado(true)} />;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-100">
            <UserPlus className="h-6 w-6 text-blue-700" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Administración STI</h1>
            <p className="text-sm text-muted-foreground">Gestión de usuarios, organizaciones y sistema</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" /> Admin
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => { sessionStorage.removeItem(ADMIN_TOKEN_KEY); setAutenticado(false); }}
            >
              Cerrar sesión
            </Button>
          </div>
        </div>

        {/* Info */}
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-start gap-2 text-sm text-amber-800">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <p>
                <span className="font-medium">Uso interno.</span>{' '}
                Los usuarios creados pueden iniciar sesión con su código y contraseña.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Tabs — 5 secciones principales */}
        <Tabs defaultValue="usuarios">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="usuarios" className="flex items-center gap-1.5 text-xs">
              <Users className="h-3.5 w-3.5" />
              <span>Usuarios</span>
            </TabsTrigger>
            <TabsTrigger value="organizaciones" className="flex items-center gap-1.5 text-xs">
              <Building2 className="h-3.5 w-3.5" />
              <span>Orgs</span>
            </TabsTrigger>
            <TabsTrigger value="ml" className="flex items-center gap-1.5 text-xs">
              <Brain className="h-3.5 w-3.5" />
              <span>ML</span>
            </TabsTrigger>
            <TabsTrigger value="sistema" className="flex items-center gap-1.5 text-xs">
              <Server className="h-3.5 w-3.5" />
              <span>Sistema</span>
            </TabsTrigger>
            <TabsTrigger value="exportar" className="flex items-center gap-1.5 text-xs text-blue-700 data-[state=active]:text-blue-800">
              <Download className="h-3.5 w-3.5" />
              <span>Exportar</span>
            </TabsTrigger>
          </TabsList>

          {/* ── Usuarios: sub-tabs con toda la gestión de usuarios ── */}
          <TabsContent value="usuarios">
            <Tabs defaultValue="estudiante" className="mt-2">
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="estudiante" className="flex items-center gap-1 text-xs">
                  <BookOpen className="h-3 w-3" />
                  <span className="hidden sm:inline">+ Estudiante</span>
                </TabsTrigger>
                <TabsTrigger value="profesor" className="flex items-center gap-1 text-xs">
                  <GraduationCap className="h-3 w-3" />
                  <span className="hidden sm:inline">+ Profesor</span>
                </TabsTrigger>
                <TabsTrigger value="ver" className="flex items-center gap-1 text-xs">
                  <Users className="h-3 w-3" />
                  <span className="hidden sm:inline">Ver todos</span>
                </TabsTrigger>
                <TabsTrigger value="puntos" className="flex items-center gap-1 text-xs text-yellow-600 data-[state=active]:text-yellow-700">
                  <Sparkles className="h-3 w-3" />
                  <span className="hidden sm:inline">Puntos</span>
                </TabsTrigger>
                <TabsTrigger value="importar" className="flex items-center gap-1 text-xs text-green-700 data-[state=active]:text-green-800">
                  <Upload className="h-3 w-3" />
                  <span className="hidden sm:inline">Importar</span>
                </TabsTrigger>
                <TabsTrigger value="eliminar" className="flex items-center gap-1 text-xs text-red-600 data-[state=active]:text-red-700">
                  <Trash2 className="h-3 w-3" />
                  <span className="hidden sm:inline">Eliminar</span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="estudiante">
                <Card>
                  <CardHeader>
                    <CardTitle>Crear Estudiante</CardTitle>
                    <CardDescription>El estudiante podrá iniciar sesión con su código y contraseña.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <FormEstudiante organizaciones={organizaciones} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="profesor">
                <Card>
                  <CardHeader>
                    <CardTitle>Crear Profesor</CardTitle>
                    <CardDescription>El profesor tendrá acceso al dashboard de gestión de grupos.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <FormProfesor organizaciones={organizaciones} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="ver">
                <SeccionVerUsuarios />
              </TabsContent>

              <TabsContent value="puntos">
                <SeccionAgregarPuntos />
              </TabsContent>

              <TabsContent value="importar">
                <Card>
                  <CardHeader>
                    <CardTitle>Importación masiva</CardTitle>
                    <CardDescription>
                      Carga un archivo CSV o Excel para crear múltiples usuarios de una vez.
                      Descarga la plantilla, complétala y súbela aquí.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <FormImportarMasivo organizaciones={organizaciones} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="eliminar">
                <SeccionEliminar />
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* ── Organizaciones ── */}
          <TabsContent value="organizaciones">
            <SeccionOrganizaciones />
          </TabsContent>

          {/* ── Machine Learning ── */}
          <TabsContent value="ml">
            <TabML />
          </TabsContent>

          {/* ── Sistema ── */}
          <TabsContent value="sistema">
            <TabSistema />
          </TabsContent>

          {/* ── Exportar ── */}
          <TabsContent value="exportar">
            <TabExportar organizaciones={organizaciones} />
          </TabsContent>
        </Tabs>

        <p className="text-center text-xs text-muted-foreground">
          STI — Sistema de Tutoría Inteligente · Panel de Administración
        </p>
      </div>
    </div>
  );
}
