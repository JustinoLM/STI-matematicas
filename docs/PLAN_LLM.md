# Plan de Implementación — Sistema LLM (DeepSeek)

**Fecha de definición:** 2026-03-03
**Estado:** Pendiente de implementación

---

## Infraestructura

| Componente | Decisión |
|---|---|
| Deployment | Railway Hobby ($5/month) — backend + frontend |
| LLM (dev y prod) | **DeepSeek API** — sin Ollama en ningún entorno |
| Mensajes simples | DeepSeek **V3** (rápido, barato) |
| Análisis post-práctica | DeepSeek **R1** (razonamiento) |
| Config | Variable de entorno `DEEPSEEK_API_KEY` |

> `ollama_service.py` se reemplaza por `llm_service.py` que llama a DeepSeek API directamente.

---

## Features a implementar (en este orden)

### 1. Enunciados temáticos del problema — V3 ✅ DONE
- **Qué hace:** Envuelve el problema matemático en una narrativa según el tema del estudiante.
  - Ej: `"plus_12.50_8.30"` + `"tema-piratas del caribe"` → *"El Capitán Barbanegra encontró 12.50 monedas de oro en la isla del tesoro. Su tripulación capturó otro barco con 8.30 monedas más. ¿Cuántas monedas tienen en total?"*
- **Caché:** tabla `enunciado_tematico` — permanente, PK: `(signature, tema, nivel)`
- **Carga progresiva:** frontend dispara peticiones en paralelo (una por problema), cada enunciado aparece en cuanto el LLM o caché responde
- **6 temas ricos implementados** con contexto específico, vocabulario y saludo propio:

| Tema (BD) | Contexto | Saludo |
|---|---|---|
| Piratas del Caribe | Repartir tesoros, distancias entre islas | ¡Arrr! ¡Excelente cálculo, marinero! |
| Astronautas Galácticos | Mezclar combustibles, calcular órbitas | ¡Misión cumplida, comandante! |
| Magos de la Academia | Preparar pociones, calcular hechizos | ¡Conjuro perfecto, joven mago! |
| Caballeros del Reino | Repartir provisiones, medir distancias | ¡Honor al campeón matemático! |
| Vaqueros del Oeste | Comercio de ganado, medir terrenos | ¡Yeehaw! ¡Cálculo certero, vaquero! |
| Princesas Inventoras | Construir inventos, medir materiales | ¡Brillante ingenio, alteza! |

### 2. Mensaje motivacional del Dashboard — V3 ✅ DONE
- **Qué hace:** Mensaje personalizado al entrar al dashboard.
  - Ej: *"¡Bienvenida, Sofía! Estás en nivel 3, ¡sigue adelante capitana!"*
- **Contexto:** nombre + género + nivel general
- **Caché:** tabla `mensaje_motivacional` — caché diaria (fecha_hoy). Mismo mensaje todo el día, nuevo al día siguiente.
- **UX (async):** Mensaje genérico estático inmediatamente → LLM reemplaza en segundo plano sin spinner

### 3. Mensaje motivacional de Progreso — V3 ✅ DONE
- **Qué hace:** Mensaje motivacional en la página de progreso del estudiante.
- **Contexto:** nombre + género
- **Caché:** misma tabla `mensaje_motivacional`, tipo="progreso", misma estrategia diaria
- **UX:** mismo patrón async que el dashboard — aparece en el header de la página de progreso

### 4. Análisis post-práctica — R1 ✅ DONE
- **Qué hace:** Al finalizar una sesión de práctica, el LLM genera un análisis breve.
- **Contexto que recibe:**
  - Precisión de la sesión
  - Tiempo promedio por problema
  - Operaciones con más errores
  - Nivel actual
  - Pasos intermedios correctos/incorrectos (multiplicación y división — ya los valida el backend)
- **Caché:** No — es único por sesión
- **UX:** Aparece automáticamente al terminar la práctica (sin botón). Async: se muestra la pantalla de resultados inmediatamente y el análisis aparece cuando R1 termina

---

## Canvas Animation ("Video Pista")

- **Qué es:** Animación paso a paso de cómo resolver el problema, reutilizando los grids existentes (`SumaRestaGrid`, `MultiplicacionGrid`, `DivisionGrid`) en modo animado
- **Trigger:** Se muestra como **popup automático después del 3er intento fallido**, ANTES de que el estudiante pueda pasar al siguiente problema (no es una pista, es una opción separada)
- **UX exacta:** Cuando `intentosRestantes === 0` → se muestra pantalla de "Sin intentos" → aparece popup de canvas animation automáticamente → estudiante puede guardarlo o descartarlo → LUEGO puede hacer clic en "Siguiente Problema"
- **No es una pista (pista != canvas):** Las pistas son ayudas durante el intento. El canvas es una revisión que aparece cuando ya se agotaron los intentos.
- **Texto:** Plantillas deterministas genéricas (no LLM, no temáticas)
  - Ej: *"Escribe el 3 en la columna de unidades"*, *"Lleva 1 a la columna de decenas"*
- **Por qué no LLM/temático:** El estudiante puede cambiar de tema en cualquier momento; el texto genérico es independiente del tema
- **Guardado:** tabla `video_guardado(estudiante_id, problema_id, guardado_en)` — máx 10 por estudiante. El popup incluye botón "Guardar en mi colección"
- **Reproducción:** Frontend re-renderiza la animación desde los datos del problema (`problema_id`). No se guarda ningún archivo.

---

## Cambios de Base de Datos requeridos

### 1. Campo `genero` en `Usuario`
```python
genero: str  # "masculino" | "femenino"
```
- Requerido en registro
- Afecta: pronombres en mensajes LLM del dashboard y progreso
- Actualizar panel `/admin` para incluir el campo

### 2. Tabla `enunciado_tematico`
```sql
CREATE TABLE enunciado_tematico (
  firma       VARCHAR NOT NULL,   -- ej. "plus_12.50_8.30"
  tema_id     VARCHAR NOT NULL,   -- ej. "tema-piratas"
  nivel       INTEGER NOT NULL,   -- 1-5
  texto       TEXT    NOT NULL,
  created_at  TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (firma, tema_id, nivel)
);
```

### 3. Tabla `mensaje_motivacional`
```sql
CREATE TABLE mensaje_motivacional (
  id           SERIAL PRIMARY KEY,
  estudiante_id INTEGER NOT NULL REFERENCES usuario(id),
  tipo          VARCHAR NOT NULL,  -- "dashboard" | "progreso"
  texto         TEXT    NOT NULL,
  sesion_id     VARCHAR NOT NULL,  -- UUID del JWT de login
  created_at    TIMESTAMP DEFAULT NOW()
);
-- Index para lookup rápido
CREATE INDEX ix_mensaje_mot_sesion ON mensaje_motivacional(estudiante_id, tipo, sesion_id);
```

### 4. Tabla `video_guardado`
```sql
CREATE TABLE video_guardado (
  id             SERIAL PRIMARY KEY,
  estudiante_id  INTEGER NOT NULL REFERENCES usuario(id),
  problema_id    INTEGER NOT NULL REFERENCES problema(id),
  guardado_en    TIMESTAMP DEFAULT NOW(),
  UNIQUE (estudiante_id, problema_id)
);
```
- Límite: 10 registros por `estudiante_id` — validar en servicio

---

## Orden de Implementación

```
1. Base:        llm_service.py (DeepSeek API) + genero en BD + admin actualizado ✅ DONE
2. Feature 1:   Enunciados temáticos — 6 temas ricos con carga progresiva  ✅ DONE
3. Feature 2/3: Mensajes motivacionales — dashboard + progreso               ✅ DONE
4. Feature 4:   Análisis post-práctica (R1)              ✅ DONE
5. Feature 5:   Canvas animation + video_guardado        ✅ DONE
```

---

## Archivos a modificar / crear

### Backend
- `backend/app/services/llm_service.py` — NUEVO (reemplaza ollama_service.py)
- `backend/app/models/llm.py` — NUEVO (modelos ORM para las 3 tablas nuevas)
- `backend/app/repositories/llm_repository.py` — NUEVO
- `backend/app/services/enunciado_service.py` — NUEVO
- `backend/app/api/routers/llm.py` — NUEVO (endpoints async)
- `backend/app/models/user.py` — agregar campo `genero`
- `backend/app/services/problem_service.py` — integrar enunciado temático
- `backend/app/services/practice_service.py` — integrar análisis post-práctica
- `backend/alembic/versions/` — migración con las 3 tablas + campo genero

### Frontend
- `frontend/src/components/animations/` — NUEVO (canvas animation components)
- `frontend/src/pages/student/StudentDashboard.tsx` — mensaje motivacional async
- `frontend/src/pages/student/ProgressPage.tsx` — mensaje motivacional async
- `frontend/src/pages/student/PracticePage.tsx` — enunciado temático + análisis post-práctica + botón guardar animación
- `frontend/src/pages/student/VideoCollectionPage.tsx` — NUEVO (colección de 10 animaciones)
- `frontend/src/pages/admin/AdminPage.tsx` — agregar campo género

---

## Variables de entorno a agregar

```env
# DeepSeek API
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_API_URL=https://api.deepseek.com/v1

# Modelos
DEEPSEEK_MODEL_V3=deepseek-chat
DEEPSEEK_MODEL_R1=deepseek-reasoner
```
