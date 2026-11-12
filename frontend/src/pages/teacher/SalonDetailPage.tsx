/**
 * Detalle de un salón (año lectivo) del profesor.
 * Estudiantes (asignar, quitar, importar por códigos), grupos dentro del salón,
 * trimestres y configuración de práctica. Un año cerrado se muestra en solo lectura.
 */

import { useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Users,
  UserPlus,
  UserMinus,
  Search,
  Loader2,
  Eye,
  FileSpreadsheet,
  Download,
  Upload,
  CheckCircle2,
  XCircle,
  Lock,
  Layers,
  CalendarDays,
  Plus,
  Settings,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { teacherService, BulkAddResult } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const fechaCorta = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('es-PA', { day: 'numeric', month: 'short' });

export default function SalonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const anioLectivoId = parseInt(id || '0');
  const queryClient = useQueryClient();

  const [busqueda, setBusqueda] = useState('');
  const [nombreGrupo, setNombreGrupo] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Importación por códigos
  const [codigosPreview, setCodigosPreview] = useState<string[]>([]);
  const [bulkResult, setBulkResult] = useState<BulkAddResult | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const claveSalon = ['teacher', 'salon', anioLectivoId];
  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: claveSalon });
    queryClient.invalidateQueries({ queryKey: ['teacher', 'salon-candidatos', anioLectivoId] });
    queryClient.invalidateQueries({ queryKey: ['teacher', 'salones'] });
    queryClient.invalidateQueries({ queryKey: ['teacher', 'students'] });
  };

  const { data: salon, isLoading } = useQuery({
    queryKey: claveSalon,
    queryFn: () => teacherService.getSalonDetalle(anioLectivoId),
    enabled: !!anioLectivoId,
  });

  const { data: candidatos = [] } = useQuery({
    queryKey: ['teacher', 'salon-candidatos', anioLectivoId],
    queryFn: () => teacherService.getCandidatosSalon(anioLectivoId),
    enabled: !!anioLectivoId && salon !== undefined && !salon.cerrado,
  });

  const asignarMutation = useMutation({
    mutationFn: (estudianteId: number) => teacherService.asignarAlSalon(anioLectivoId, estudianteId),
    onSuccess: () => { setError(null); invalidar(); },
    onError: (e: Error) => setError(e.message),
  });

  const quitarMutation = useMutation({
    mutationFn: (estudianteId: number) => teacherService.quitarDelSalon(anioLectivoId, estudianteId),
    onSuccess: () => { setError(null); invalidar(); },
    onError: (e: Error) => setError(e.message),
  });

  const crearGrupoMutation = useMutation({
    mutationFn: () => teacherService.crearGrupo(anioLectivoId, nombreGrupo.trim()),
    onSuccess: () => {
      setNombreGrupo('');
      setError(null);
      invalidar();
      queryClient.invalidateQueries({ queryKey: ['teacher', 'groups'] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const handleBulkFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBulkResult(null);
    setBulkError(null);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const wb = XLSX.read(ev.target?.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, { defval: '' });
        const codigos = rows
          .map((r) => String(r['codigo_estudiante'] ?? r['codigo'] ?? '').trim().toUpperCase())
          .filter(Boolean);
        if (codigos.length === 0) {
          setBulkError('No se encontraron códigos en el archivo. Verifica que la columna se llame "codigo_estudiante" o "codigo".');
        } else {
          setCodigosPreview(codigos);
        }
      } catch {
        setBulkError('No se pudo leer el archivo. Verifica que sea CSV o Excel válido.');
      }
    };
    reader.readAsArrayBuffer(file);
  }, []);

  const handleBulkImport = useCallback(async () => {
    if (codigosPreview.length === 0) return;
    setBulkLoading(true);
    setBulkError(null);
    try {
      const result = await teacherService.asignarAlSalonPorCodigos(anioLectivoId, codigosPreview);
      setBulkResult(result);
      if (result.agregados > 0) invalidar();
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : 'Error al importar');
    } finally {
      setBulkLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codigosPreview, anioLectivoId]);

  const downloadTemplate = useCallback(() => {
    const ws = XLSX.utils.aoa_to_sheet([['codigo_estudiante'], ['EST001'], ['EST002'], ['EST003']]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Códigos');
    XLSX.writeFile(wb, 'plantilla_asignar_salon.xlsx');
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <p className="text-muted-foreground">Cargando el salón...</p>
      </div>
    );
  }

  if (!salon) {
    return (
      <div className="space-y-6">
        <Link to="/teacher/salones">
          <Button variant="ghost">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a mis salones
          </Button>
        </Link>
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">Salón no encontrado</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const soloLectura = salon.cerrado;
  const q = busqueda.toLowerCase();
  const disponibles = candidatos.filter(
    (c) =>
      !c.en_este_salon &&
      (!q || c.nombre_completo.toLowerCase().includes(q) || c.codigo_estudiante.toLowerCase().includes(q))
  );
  const nombrePorId = new Map(salon.estudiantes.map((e) => [e.estudiante_id, e.nombre_completo]));

  return (
    <div className="space-y-6">
      {/* ── Encabezado ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <Link to="/teacher/salones">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a mis salones
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">Salón {salon.nombre}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{salon.grado}.º grado</Badge>
            <Badge variant="outline">Año {salon.anio}</Badge>
            <span className="text-sm text-muted-foreground">Profesor: {salon.profesor_nombre}</span>
          </div>
        </div>
        {!soloLectura && (
          <Link to={`/teacher/configuration?salon=${salon.anio_lectivo_id}`}>
            <Button variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Configurar práctica
            </Button>
          </Link>
        )}
      </div>

      {soloLectura && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <Lock className="h-4 w-4 flex-shrink-0" />
          Este año lectivo está cerrado. Puedes consultarlo, pero no hacer cambios.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {/* ── Resumen ─────────────────────────────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estudiantes</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{salon.cantidad_estudiantes}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Grupos</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{salon.cantidad_grupos}</div>
            <p className="text-xs text-muted-foreground">Opcionales, por ejemplo para desafíos</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Práctica de decimales</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {salon.configuracion ? (
              <p className="text-sm">
                Operaciones: <span className="font-medium">{salon.configuracion.operaciones_permitidas.join(', ')}</span>
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">Sin configuración: se usa la adaptativa</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="estudiantes">
        <TabsList className={`grid w-full ${soloLectura ? 'grid-cols-3' : 'grid-cols-5'}`}>
          <TabsTrigger value="estudiantes">
            <Users className="mr-2 h-4 w-4" />
            Estudiantes ({salon.estudiantes.length})
          </TabsTrigger>
          {!soloLectura && (
            <TabsTrigger value="agregar">
              <UserPlus className="mr-2 h-4 w-4" />
              Asignar
            </TabsTrigger>
          )}
          {!soloLectura && (
            <TabsTrigger value="importar">
              <Upload className="mr-2 h-4 w-4" />
              Importar lista
            </TabsTrigger>
          )}
          <TabsTrigger value="grupos">
            <Layers className="mr-2 h-4 w-4" />
            Grupos ({salon.grupos.length})
          </TabsTrigger>
          <TabsTrigger value="trimestres">
            <CalendarDays className="mr-2 h-4 w-4" />
            Trimestres
          </TabsTrigger>
        </TabsList>

        {/* Estudiantes del salón */}
        <TabsContent value="estudiantes">
          <Card>
            <CardContent className="pt-4">
              {salon.estudiantes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-10">
                  {soloLectura
                    ? 'Este salón no tuvo estudiantes.'
                    : 'Aún no hay estudiantes en este salón. Usa la pestaña "Asignar".'}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                        <th className="px-4 py-3 text-center text-sm font-semibold">Nivel</th>
                        <th className="px-4 py-3 text-center text-sm font-semibold">Precisión</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold">Acciones</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {salon.estudiantes.map((est) => (
                        <tr key={est.estudiante_id} className="hover:bg-muted/50">
                          <td className="px-4 py-3">
                            <code className="text-xs bg-muted px-2 py-1 rounded">{est.codigo_estudiante}</code>
                          </td>
                          <td className="px-4 py-3 font-medium">{est.nombre_completo}</td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant="outline">Nivel {est.nivel_actual}</Badge>
                          </td>
                          <td className="px-4 py-3 text-center text-sm font-semibold">
                            {est.precision_ultimos_15.toFixed(0)}%
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Link to={`/teacher/students/${est.estudiante_id}`}>
                                <Button size="sm" variant="ghost" title="Ver estudiante">
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </Link>
                              {!soloLectura && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  title="Quitar del salón"
                                  className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                  disabled={quitarMutation.isPending}
                                  onClick={() => quitarMutation.mutate(est.estudiante_id)}
                                >
                                  <UserMinus className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Asignar estudiantes de la organización */}
        {!soloLectura && (
          <TabsContent value="agregar">
            <Card>
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm text-muted-foreground">
                  Un estudiante solo puede estar en un salón a la vez. Si ya está en otro, su profesor
                  debe quitarlo primero.
                </p>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Buscar por nombre o código..."
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                {disponibles.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">
                    {busqueda ? 'No se encontraron estudiantes con esa búsqueda.' : 'No hay más estudiantes en tu organización.'}
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
                          <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                          <th className="px-4 py-3 text-left text-sm font-semibold">Salón actual</th>
                          <th className="px-4 py-3 text-right text-sm font-semibold">Asignar</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {disponibles.map((c) => (
                          <tr key={c.id} className="hover:bg-muted/50">
                            <td className="px-4 py-3">
                              <code className="text-xs bg-muted px-2 py-1 rounded">{c.codigo_estudiante}</code>
                            </td>
                            <td className="px-4 py-3 font-medium">{c.nombre_completo}</td>
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {c.salon_actual ?? 'Sin salón'}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-green-600 hover:text-green-800 hover:bg-green-50"
                                disabled={asignarMutation.isPending || c.salon_actual !== null}
                                title={c.salon_actual ? `Ya está en el salón ${c.salon_actual}` : 'Asignar a este salón'}
                                onClick={() => asignarMutation.mutate(c.id)}
                              >
                                <UserPlus className="h-4 w-4 mr-1" />
                                Asignar
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Importar lista de códigos */}
        {!soloLectura && (
          <TabsContent value="importar">
            <Card>
              <CardContent className="pt-4 space-y-4">
                <p className="text-sm text-muted-foreground">
                  Sube un archivo CSV o Excel con una columna{' '}
                  <code className="bg-muted px-1 rounded text-xs">codigo_estudiante</code> (o{' '}
                  <code className="bg-muted px-1 rounded text-xs">codigo</code>). Los estudiantes deben
                  pertenecer a tu organización y no estar en otro salón.
                </p>
                <div className="flex flex-wrap gap-2 items-center">
                  <Button variant="outline" size="sm" onClick={downloadTemplate}>
                    <Download className="h-4 w-4 mr-1" />
                    Descargar plantilla
                  </Button>
                  <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleBulkFile} />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => { fileInputRef.current?.click(); setCodigosPreview([]); setBulkResult(null); }}
                  >
                    <FileSpreadsheet className="h-4 w-4 mr-1" />
                    Seleccionar archivo
                  </Button>
                </div>
                {codigosPreview.length > 0 && !bulkResult && (
                  <div className="space-y-3">
                    <p className="text-sm font-medium">{codigosPreview.length} códigos detectados — vista previa (máx. 15):</p>
                    <div className="flex flex-wrap gap-1.5">
                      {codigosPreview.slice(0, 15).map((c, i) => (
                        <code key={i} className="text-xs bg-muted px-2 py-1 rounded border">{c}</code>
                      ))}
                      {codigosPreview.length > 15 && (
                        <span className="text-xs text-muted-foreground self-center">…y {codigosPreview.length - 15} más</span>
                      )}
                    </div>
                    <Button onClick={handleBulkImport} disabled={bulkLoading} size="sm">
                      {bulkLoading ? (
                        <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Asignando...</>
                      ) : (
                        <><UserPlus className="h-4 w-4 mr-1" /> Asignar {codigosPreview.length} estudiantes al salón</>
                      )}
                    </Button>
                  </div>
                )}
                {bulkResult && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-4 p-3 rounded-lg bg-muted">
                      <div className="flex items-center gap-1.5 text-green-700">
                        <CheckCircle2 className="h-4 w-4" />
                        <span className="font-semibold">{bulkResult.agregados} asignados</span>
                      </div>
                      {bulkResult.errores.length > 0 && (
                        <div className="flex items-center gap-1.5 text-red-600">
                          <XCircle className="h-4 w-4" />
                          <span className="font-semibold">{bulkResult.errores.length} con problemas</span>
                        </div>
                      )}
                      <span className="text-sm text-muted-foreground">de {bulkResult.total} códigos</span>
                    </div>
                    {bulkResult.errores.length > 0 && (
                      <div className="rounded border border-red-200 bg-red-50 p-2 space-y-1 max-h-40 overflow-y-auto">
                        {bulkResult.errores.map((err, i) => (
                          <p key={i} className="text-xs text-red-700">
                            <code className="font-mono">{err.codigo || `fila ${err.fila}`}</code>: {err.mensaje}
                          </p>
                        ))}
                      </div>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setCodigosPreview([]);
                        setBulkResult(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      Nueva importación
                    </Button>
                  </div>
                )}
                {bulkError && <p className="text-sm text-red-600">{bulkError}</p>}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Grupos del salón */}
        <TabsContent value="grupos">
          <Card>
            <CardContent className="pt-4 space-y-4">
              {!soloLectura && (
                <form
                  className="flex gap-2"
                  onSubmit={(e) => { e.preventDefault(); if (nombreGrupo.trim()) crearGrupoMutation.mutate(); }}
                >
                  <Input
                    value={nombreGrupo}
                    onChange={(e) => setNombreGrupo(e.target.value)}
                    placeholder="Nombre del grupo, ej. Equipo rojo"
                    maxLength={255}
                  />
                  <Button type="submit" disabled={crearGrupoMutation.isPending || !nombreGrupo.trim()}>
                    <Plus className="h-4 w-4 mr-1" />
                    Crear grupo
                  </Button>
                </form>
              )}
              {salon.grupos.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  Este salón no tiene grupos. Son opcionales: sirven, por ejemplo, para desafíos por equipos.
                </p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {salon.grupos.map((g) => (
                    <Link key={g.id} to={`/teacher/groups/${g.id}`}>
                      <div className="rounded-lg border p-3 hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">{g.nombre}</span>
                          <Badge variant="outline">{g.estudiantes_ids.length} estudiantes</Badge>
                        </div>
                        {g.estudiantes_ids.length > 0 && (
                          <p className="text-xs text-muted-foreground mt-1 truncate">
                            {g.estudiantes_ids.map((eid) => nombrePorId.get(eid) ?? `#${eid}`).join(', ')}
                          </p>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trimestres (los define el administrador para toda la escuela) */}
        <TabsContent value="trimestres">
          <Card>
            <CardContent className="pt-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                Las fechas de los trimestres las define el administrador para toda la escuela.
              </p>
              <div className="grid gap-3 md:grid-cols-3">
                {salon.trimestres.map((t) => (
                  <div key={t.numero} className="rounded-lg border p-3">
                    <p className="text-sm font-semibold">Trimestre {t.numero}</p>
                    <p className="text-sm text-muted-foreground">
                      {fechaCorta(t.fecha_inicio)} – {fechaCorta(t.fecha_fin)}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
