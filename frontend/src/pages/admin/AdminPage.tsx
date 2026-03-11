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
} from 'lucide-react';
import apiClient, { getErrorMessage } from '@/services/api';

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface CreateStudentPayload {
  codigo_estudiante: string;
  nombre_completo: string;
  genero: 'masculino' | 'femenino';
  password: string;
  organizacion_id?: number;
}

interface CreateTeacherPayload {
  codigo_profesor: string;
  nombre_completo: string;
  password: string;
  institucion?: string;
  organizacion_id?: number;
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
  password_plain: string | null;
  activo: boolean;
  fecha_creacion: string | null;
  ultimo_acceso: string | null;
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
  async eliminarOrganizacion(orgId: number): Promise<void> {
    await apiClient.delete(`/admin/organizations/${orgId}`);
  },
  async eliminarProfesor(profId: number): Promise<void> {
    await apiClient.delete(`/admin/professors/${profId}`);
  },
  async eliminarEstudiante(estId: number): Promise<void> {
    await apiClient.delete(`/admin/students/${estId}`);
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
  const [form, setForm] = useState({
    codigo_estudiante: '',
    nombre_completo: '',
    genero: 'masculino' as 'masculino' | 'femenino',
    password: '',
    organizacion_id: '',
  });
  const [resultado, setResultado] = useState<UserCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CreateStudentPayload) => adminService.crearEstudiante(data),
    onSuccess: (data) => {
      setResultado(data);
      setError(null);
      setForm({ codigo_estudiante: '', nombre_completo: '', genero: 'masculino', password: '', organizacion_id: '' });
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
  });
  const [resultado, setResultado] = useState<UserCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CreateTeacherPayload) => adminService.crearProfesor(data),
    onSuccess: (data) => {
      setResultado(data);
      setError(null);
      setForm({ codigo_profesor: '', nombre_completo: '', password: '', institucion: '', organizacion_id: '' });
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

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="org-prof">Organización</Label>
          <select
            id="org-prof"
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

// ─── Tarjeta de Organización (detalle + asignación) ───────────────────────────

function OrgCard({ org, allUsers, onRefresh }: {
  org: OrgCreated;
  allUsers: AllUsersResponse | undefined;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const { data: detalle, refetch } = useQuery({
    queryKey: ['org-detalle', org.id],
    queryFn: () => adminService.getDetalleOrg(org.id),
    enabled: expanded,
    staleTime: 0,
  });

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
                <div className="space-y-1">
                  {profsMiembros.map(p => (
                    <div key={p.id} className="flex items-center justify-between bg-blue-50 rounded px-3 py-1.5 text-sm">
                      <span className="font-mono text-xs text-blue-600 mr-2">{p.codigo}</span>
                      <span className="flex-1">{p.nombre_completo}</span>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                        disabled={loadingId === `prof-${p.id}`} onClick={() => handleQuitarProf(p.id)}>
                        {loadingId === `prof-${p.id}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                      </Button>
                    </div>
                  ))}
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
                  {estsMiembros.map(e => (
                    <div key={e.id} className="flex items-center justify-between bg-green-50 rounded px-3 py-1.5 text-sm">
                      <span className="font-mono text-xs text-green-600 mr-2">{e.codigo}</span>
                      <span className="flex-1">{e.nombre_completo}</span>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                        disabled={loadingId === `est-${e.id}`} onClick={() => handleQuitarEst(e.id)}>
                        {loadingId === `est-${e.id}` ? <Loader2 className="h-3 w-3 animate-spin" /> : <X className="h-3 w-3" />}
                      </Button>
                    </div>
                  ))}
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
              <OrgCard key={org.id} org={org} allUsers={allUsers} onRefresh={handleRefreshAll} />
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
  const [showPasswords, setShowPasswords] = useState(false);

  const { data: allUsers, isLoading, refetch } = useQuery({
    queryKey: ['admin-all-users-view'],
    queryFn: () => adminService.getAllUsers(),
    staleTime: 0,
  });

  const TablaUsuarios = ({
    usuarios,
    tipo,
    color,
  }: {
    usuarios: UsuarioAdmin[];
    tipo: 'estudiante' | 'profesor';
    color: string;
  }) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted text-left">
            <th className="px-3 py-2 font-semibold">Código</th>
            <th className="px-3 py-2 font-semibold">Nombre</th>
            {tipo === 'profesor' && <th className="px-3 py-2 font-semibold">Institución</th>}
            <th className="px-3 py-2 font-semibold">Contraseña</th>
            <th className="px-3 py-2 font-semibold">Creado</th>
            <th className="px-3 py-2 font-semibold">Último acceso</th>
            <th className="px-3 py-2 font-semibold">Estado</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {usuarios.map(u => (
              <tr key={u.id} className="hover:bg-muted/40">
                <td className="px-3 py-2">
                  <div className="flex items-center">
                    <code className={`text-xs px-1.5 py-0.5 rounded font-mono ${color}`}>{u.codigo}</code>
                    <CopiarBtn texto={u.codigo} />
                  </div>
                </td>
                <td className="px-3 py-2 font-medium">{u.nombre_completo}</td>
                {tipo === 'profesor' && (
                  <td className="px-3 py-2 text-muted-foreground text-xs">{u.institucion || '—'}</td>
                )}
                <td className="px-3 py-2">
                  {u.password_plain ? (
                    <div className="flex items-center gap-1">
                      <code className="text-xs bg-yellow-50 border border-yellow-200 px-1.5 py-0.5 rounded">
                        {showPasswords ? u.password_plain : '••••••'}
                      </code>
                      <CopiarBtn texto={u.password_plain} />
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground italic">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatFecha(u.fecha_creacion)}
                  </div>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatFecha(u.ultimo_acceso)}
                  </div>
                </td>
                <td className="px-3 py-2">
                  <Badge variant={u.activo ? 'default' : 'secondary'} className="text-xs">
                    {u.activo ? 'Activo' : 'Inactivo'}
                  </Badge>
                </td>
              </tr>
          ))}
        </tbody>
      </table>
      {usuarios.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-6">Sin {tipo === 'estudiante' ? 'estudiantes' : 'profesores'} registrados.</p>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Controles */}
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={() => setShowPasswords(v => !v)}>
          {showPasswords ? <EyeOff className="h-4 w-4 mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
          {showPasswords ? 'Ocultar' : 'Mostrar'} contraseñas
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <Loader2 className="h-4 w-4 mr-1" />Actualizar
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <>
          {/* Estudiantes */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-green-600" />
                Estudiantes
                <Badge variant="secondary">{allUsers?.estudiantes.length ?? 0}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 pb-2">
              <TablaUsuarios
                usuarios={allUsers?.estudiantes ?? []}
                tipo="estudiante"
                color="bg-green-50 text-green-700"
              />
            </CardContent>
          </Card>

          {/* Profesores */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <GraduationCap className="h-4 w-4 text-blue-600" />
                Profesores
                <Badge variant="secondary">{allUsers?.profesores.length ?? 0}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 pb-2">
              <TablaUsuarios
                usuarios={allUsers?.profesores ?? []}
                tipo="profesor"
                color="bg-blue-50 text-blue-700"
              />
            </CardContent>
          </Card>

        </>
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

  const ADMIN_PWD = import.meta.env.VITE_ADMIN_PASSWORD || '';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pwd === ADMIN_PWD) {
      sessionStorage.setItem('admin_auth', 'ok');
      onAcceso();
    } else {
      setError('Contraseña incorrecta');
      setPwd('');
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
            <Button type="submit" className="w-full">
              <ShieldCheck className="h-4 w-4 mr-2" /> Ingresar
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function AdminPage() {
  const [autenticado, setAutenticado] = useState(() =>
    sessionStorage.getItem('admin_auth') === 'ok'
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
              onClick={() => { sessionStorage.removeItem('admin_auth'); setAutenticado(false); }}
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

        {/* Tabs — 4 secciones principales */}
        <Tabs defaultValue="usuarios">
          <TabsList className="grid w-full grid-cols-4">
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
          </TabsList>

          {/* ── Usuarios: sub-tabs con toda la gestión de usuarios ── */}
          <TabsContent value="usuarios">
            <Tabs defaultValue="estudiante" className="mt-2">
              <TabsList className="grid w-full grid-cols-5">
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
        </Tabs>

        <p className="text-center text-xs text-muted-foreground">
          STI — Sistema de Tutoría Inteligente · Panel de Administración
        </p>
      </div>
    </div>
  );
}
