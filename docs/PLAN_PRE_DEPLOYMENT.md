# Plan Pre-Deployment — STI Matemáticas

**Fecha de definición:** 2026-03-06
**Estado:** ✅ COMPLETO (2026-03-06)

---

## Resumen de features

| # | Feature | Estado |
|---|---------|--------|
| 1 | Fix `[object Object]` en login | ✅ DONE |
| 2 | Admin panel refinado (tabs + contraseña + ML) | ✅ DONE |
| 3 | APScheduler — ML automático + cierre de sesiones | ✅ DONE |
| 4 | Recuperación de práctica incompleta | ✅ DONE |

---

## 1. Fix `[object Object]` en login ✅ DONE

**Archivo:** `frontend/src/services/api.ts` — función `getErrorMessage`

**Causa:** FastAPI devuelve `422 Unprocessable Entity` con `detail` como array de objetos
(`[{loc, msg, type}]`). La función solo manejaba `detail` como string, así que al
renderizarlo aparecía `[object Object]`.

**Fix:**
```typescript
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((e: any) => e.msg).join(', ');
    return error.message || 'Error desconocido';
  }
  if (error instanceof Error) return error.message;
  return 'Error desconocido';
};
```

---

## 2. Admin panel refinado ⏳ Pendiente

### Decisiones
- **Contraseña:** variable de entorno `VITE_ADMIN_PASSWORD` en frontend. Se guarda
  en `sessionStorage` para no pedir contraseña en cada recarga de la misma sesión.
- **4 tabs:** Usuarios · Organizaciones · Machine Learning · Sistema

### Archivos a modificar
- `frontend/src/pages/admin/AdminPage.tsx` — refactor completo con tabs y pantalla de contraseña

### Backend nuevo
- `GET /api/admin/sistema/stats` — totales globales:
  - total_estudiantes, total_profesores, total_grupos, total_organizaciones
  - sesiones_hoy, sesiones_semana
  - problemas_resueltos_hoy

### Tab Machine Learning (UI)
- Estado del modelo: clustering entrenado ✓/✗, predicción entrenado ✓/✗
- Fecha último entrenamiento (desde `metadata.json` o BD)
- Botón "Entrenar ahora" → `POST /api/admin/ml/entrenar`
- Resultado del entrenamiento (cuántos perfiles usados, cuántos reclasificados)

---

## 3. APScheduler — ML automático + cierre de sesiones ⏳ Pendiente

### Instalación
```bash
cd backend
poetry add apscheduler
```

### Tabla nueva en BD: `configuracion_sistema`
```python
class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    clave = Column(String, primary_key=True)   # ej: "ml_ultimo_entrenamiento"
    valor = Column(String, nullable=True)       # ISO datetime string
    actualizado_en = Column(DateTime)
```

Migración: `alembic revision --autogenerate -m "add configuracion_sistema"`

### Archivo nuevo: `backend/app/services/scheduler_service.py`
Dos jobs en el mismo scheduler:

**Job 1 — ML cada 3 días:**
- Trigger: intervalo de 24 horas (revisión diaria)
- Lógica: leer `ml_ultimo_entrenamiento` de BD → si pasaron ≥3 días → entrenar y reclasificar
- En startup: también ejecutar la verificación inmediatamente (catch-up si estuvo caído)

**Job 2 — Cierre de sesiones huérfanas:**
- Trigger: intervalo de 30 minutos
- Lógica: buscar `SesionPractica` con `estado = "en_progreso"` y
  `fecha_inicio < NOW() - 90min`
- Cerrarlas: calcular XP/monedas parciales por los problemas respondidos,
  actualizar perfil del estudiante, marcar `estado = "completada"`

### Integración en `main.py`
```python
from app.services.scheduler_service import start_scheduler, stop_scheduler

@app.on_event("startup")
async def startup():
    await start_scheduler()

@app.on_event("shutdown")
async def shutdown():
    await stop_scheduler()
```

---

## 4. Recuperación de práctica incompleta ⏳ Pendiente

### Flujo completo

1. **Estudiante pierde conexión** durante práctica → sesión queda `en_progreso` en BD
2. **Al volver** (dashboard o página de práctica) → detecta sesión activa
3. **Opciones:**
   - ✅ **Continuar** → retomar sesión existente (mismo `sesion_id`, problemas restantes nuevos)
   - ❌ **Descartar** → cerrar sesión con XP parcial por lo completado

**Timeout:** El scheduler (Job 2) cierra automáticamente sesiones con >90 min de inactividad.
Si ya fue cerrada por timeout, no aparece el banner (ya recibió XP parcial).

### Backend nuevo

**`GET /api/adaptive/practice/sesion-activa`**
- Retorna la sesión `en_progreso` del estudiante autenticado si existe y tiene <90 min
- Si no hay ninguna → `null`
- Response:
```json
{
  "sesion_id": 42,
  "operacion": "suma",
  "nivel": 3,
  "problemas_completados": 6,
  "total_problemas": 10,
  "fecha_inicio": "2026-03-06T10:30:00"
}
```

**`POST /api/adaptive/practice/retomar/{sesion_id}`**
- Valida que la sesión pertenece al estudiante autenticado y está `en_progreso`
- Retorna datos para continuar desde el problema N+1
- Los problemas restantes son generados nuevos (misma operación y nivel)

### Frontend

**`StudentDashboard.tsx`** — banner de recuperación:
- `useQuery(['sesion-activa'])` con `staleTime: 0` (siempre fresco)
- Si hay sesión activa → banner amarillo con "Tienes una práctica sin terminar"
  - Botón "Continuar" → navega a `/student/practice` con state `{reanudar: sesion_id}`
  - Botón "Descartar" → llama endpoint que cierra con XP parcial → invalida query

**`PracticePage.tsx`** — detección al montar:
- Al cargar, verifica `location.state?.reanudar` O llama `sesion-activa`
- Si detecta sesión activa → diálogo: "¿Continuar práctica anterior o iniciar nueva?"
- "Continuar" → llama `POST /retomar/{sesion_id}` y arranca desde problema N+1

---

## Notas de implementación

- `VITE_ADMIN_PASSWORD` se define en `.env` del frontend y en Vercel como variable de entorno
- APScheduler usa `AsyncIOScheduler` para no bloquear el event loop de FastAPI
- El cierre automático de sesiones respeta las monedas/XP proporcionales (no "cero o todo")
- La tabla `configuracion_sistema` sirve también para futuras configuraciones globales del sistema
