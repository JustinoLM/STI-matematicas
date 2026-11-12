# Diseño: STI modular para varios temas (1.º a 6.º de primaria)

Resultado de la sesión de diseño del 11 de noviembre de 2026. Es un documento de diseño:
describe decisiones y preguntas abiertas, no el estado del código. La versión validada en la
tesis está en la etiqueta `v1.0-tesis`.

Alcance de esta etapa: **primero y segundo grado completos**. De tercero a sexto solo se deja
el plan.

---

## 1. Estructura del sistema

### Contenido

- **Temas.** Son las lecciones del programa de MEDUCA, solo las de contenido numérico.
  - Entra la medida que es cálculo con unidades: sumar y restar longitudes, conversiones de
    longitud, masa y capacidad, y medición del tiempo de 6.º (por ejemplo, 3 h 40 min + 2 h 35 min).
  - Queda para más adelante lo que requiere percibir o dibujar: comparar longitudes, monedas,
    reloj analógico, geometría y ordinales.
- **Caminos por conjunto numérico.** Naturales, decimales, fracciones y enteros. Se separan
  porque en cada uno cambian el procedimiento y los errores típicos. El sistema actual pasa a ser
  el camino de decimales (suma, resta, multiplicación y división).
- **Progresión dentro de un camino.** En naturales, la dificultad crece con el rango, con llevar
  o pedir prestado y con la cantidad de sumandos. El paso siguiente lo define el orden del
  programa: después de "Sumemos con totales hasta 99" (1.º) viene "Sumemos llevando" (2.º).
- **Catálogo de lecciones y grafo.** Viven en un archivo YAML o JSON del repositorio, versionado
  con git, que se carga en la base de datos. Cada lección registra grado, unidad, lección y camino.
- **El grafo cumple tres funciones:**
  - prerrequisitos por defecto, que el profesor puede editar;
  - "paso siguiente" para la zona de extensión;
  - "paso anterior" para la zona de refuerzo.

### Dominio por lección

- **Estados:** no iniciado, en progreso y dominado. No hay niveles del 1 al 5 por lección.
- **El dominio es del estudiante.** El dominio del salón o de un grupo se **calcula** a partir de
  sus estudiantes; no se guarda aparte. El progreso se conserva aunque la lección se deshabilite.
- **Criterio provisional.** Todos los valores son parámetros configurables, nunca números fijos
  en el código. Se basan en la literatura y se ajustarán con especialistas o con MEDUCA.
  - **Para declarar dominio:** al menos 80 % de aciertos en los últimos 10 problemas, en 2 o más
    sesiones de días distintos, sin contar los aciertos que usaron la pista de nivel 3.
  - **Para mandar a repaso:** 2 o 3 semanas sin practicar la lección.
  - **Para volver a "en progreso":** menos de 60 % en el repaso.
- **Confirmación.** El dominio se confirma o se retira siempre con la regla absoluta. La
  comparación con los compañeros solo genera **alertas**.

### Formas de respuesta

- **Expresión con huecos tipados.** Es la forma general de respuesta. Los tipos de hueco son:
  número, opción, fracción y cantidad con unidades.

  | Ejemplo | Huecos |
  |---|---|
  | `23 + 14 = _` | un hueco numérico al final |
  | `1 + _ = 10` | un hueco numérico en medio |
  | `12, 13, _, 15` | un hueco numérico dentro de una secuencia |
  | `_ decenas y _ unidades` | dos huecos numéricos |
  | `17 ÷ 5 = _ residuo _` | dos huecos numéricos |
  | `8 _ 3 = 5` | un hueco de opción (+, −) |
  | `45 _ 54` | un hueco de opción (<, >, =) |
  | `3 h 40 min + 2 h 35 min = _ h _ min` | huecos con unidad |
  | `½ + ¼ = _/_` | hueco de fracción |

- **Identificar la operación.** Una lección incluye dos tipos de ejercicio: el cálculo y la
  identificación de la operación. Para identificarla basta con **ocultar el signo**, que convierte
  el operador en un hueco de opción.
- **Ordenar números.** Es una forma de respuesta aparte: el niño arrastra tarjetas.
- **Banco de respuestas para arrastrar.** Se arrastra, no se toca: según Khan Academy Kids, tocar
  favorece las respuestas al azar.
  - **Por grado:** siempre en 1.º y 2.º, en 3.º según la lección, y teclado desde 4.º.
  - **Por estudiante:** el profesor puede forzar el banco como adaptación de accesibilidad.
  - **Cantidad de opciones:** entre 3 y 4, siempre completas (por ejemplo `{72, 62, 612}`) y no
    fichas de dígitos.
  - **Opciones incorrectas:** salen de los **errores típicos** de cada camino. Para `3 + 2`, por
    ejemplo: `4` (contó uno de menos), `6` (contó uno de más) y `1` (restó). Si las reglas no dan
    suficientes opciones distintas, se completa con números cercanos.
  - **Diagnóstico del error:** elegir una opción incorrecta indica el tipo de error. Las reglas de
    error de cada camino sirven para generar las opciones y para diagnosticar.
  - **Valor del acierto:** un acierto con banco cuenta igual que uno con teclado. Con 3 opciones,
    la probabilidad de alcanzar 8 de 10 solo adivinando es de aproximadamente 0,3 %.

### Presentación

- **Íconos más texto.** A partir de cierto rango, los íconos se agrupan en decenas: barras de 10
  y unidades sueltas.
- **Lectura en voz alta.** Es opcional, como recurso de accesibilidad.
- **Dispositivos.** Todo el flujo del estudiante debe funcionar en computadora y en tablet, con
  ratón y con toque.
- **Enunciados.** La referencia de estilo son los libros Panamáticas de cada grado.

### Qué es genérico y qué es propio de cada tema

| Genérico | Propio de cada lección o camino |
|---|---|
| Sesión, intentos, puntos y medallas | Generador de problemas |
| Reparto de la sesión | Validación de cada tipo de hueco |
| Dominio por lección | Reglas de error y opciones incorrectas del banco |
| Grafo, zona de extensión y zona de refuerzo | Contenido de las pistas |
| Habilitación por salón y asignación individual | Presentaciones especiales (cuadrículas de decimales, semirrecta) |
| Alertas | |
| Expresión con huecos tipados y presentación (íconos, texto, voz) | |
| Los 3 niveles de pista (estrategia, paso a paso y casi la respuesta) | |

### Código actual que hay que generalizar

- **El tema está fijo en el esquema.**
  - `Operacion` es un enum con solo `+ - × ÷`, y `Problema` tiene `numero1`, `numero2` y
    `resultado` (`backend/app/models/problem.py`).
  - El perfil tiene una columna de nivel por operación (`nivel_suma` y las demás), y el mismo
    patrón se repite en el diagnóstico, el post-test y `SesionPractica`
    (`backend/app/models/adaptive.py`).
- **El reparto de la sesión** tiene porcentajes fijos para 1 a 4 operaciones y un diccionario fijo
  `PREREQUISITOS` (`backend/app/services/adaptive_service.py`).
- **La detección de errores** mezcla reglas genéricas (confundió la operación, orden incorrecto)
  con reglas solo de decimales, todo en un único enum `TipoError`
  (`backend/app/services/deteccion_errores_service.py`, `backend/app/models/hints.py`).
- **Medallas.** Cerca de la mitad usa criterios de nivel por operación
  (`backend/scripts/seed_data.py`).
- **Regla de tres.** Duplica todas las tablas (problema, perfil, sesión e intento). Muestra lo que
  cuesta hoy añadir un tema.
- **Pantalla de práctica.** Solo envía la respuesta final y el tiempo; lo que se escribe en las
  cuadrículas se pierde (`frontend/src/pages/student/PracticePage.tsx`).

---

## 2. Flujo del profesor

### Organización

- **Salón fijo y año lectivo.**
  - El salón tiene un id permanente, por ejemplo "1A, La Salle de Margarita".
  - El **año lectivo del salón** ("1A en 2026") tiene profesor, estudiantes, configuración de
    temas y fechas de trimestres.
  - Al empezar un año se crea un año lectivo nuevo y el anterior queda cerrado, de solo lectura.
    No se reinicia ni se borra nada.
- **Quién gestiona el salón.** El profesor crea el salón y asigna o quita estudiantes.
- **Trimestres.** Cada año lectivo tiene 3 trimestres con fechas por defecto: el primero empieza
  en marzo, el año termina a mediados de diciembre y hay una semana de vacaciones entre
  trimestres. Las fechas las cambia el **administrador, para toda la escuela**, no cada profesor.
  Hoy solo existe un administrador global, así que hasta que haya administración por escuela ese
  administrador las edita por organización.
- **Grupos.** Pasan a ser subconjuntos opcionales dentro del salón, por ejemplo para desafíos.
  - Se cierran junto con el año lectivo y quedan de solo lectura en el historial. No se
    reutilizan al año siguiente, porque un profesor puede tener salones distintos cada año.
  - Los desafíos son siempre dentro de un mismo salón; no hay desafíos entre salones.
  - Un desafío sin terminar al cerrar el año se cierra como "no completado", conservando los
    puntos ya otorgados.
  - Hoy `ConfiguracionPractica` cuelga de `Grupo` y el grupo activo se elige con `.limit(1)` sin
    orden.
  - `Grupo` no tiene grado.
  - El grado del estudiante es un texto libre: hay que corregirlo para que dependa del salón.
- **Estudiante sin salón.** No puede practicar. Ve un mensaje que le pide consultar a su profesor.

### Catálogo y habilitación

- **Catálogo.** Muestra por defecto las lecciones del grado del salón. El profesor puede habilitar
  lecciones de otros grados, porque los salones no suelen estar parejos.
- **Habilitación.** Una lección queda habilitada hasta que el profesor la desactiva.
- **Plan por trimestre (opcional).**
  - Habilita y deshabilita lecciones según la fecha.
  - El profesor siempre puede ajustar a mano.
  - El trimestre también sirve como corte para los informes.
  - No hay un plan de trimestres por defecto, porque no tenemos el plan oficial.

### Configuración por lección

| Control | Valores |
|---|---|
| Signo | siempre, nunca o al azar |
| Íconos | siempre, nunca o al azar |
| Pistas habilitadas | sí o no por nivel |
| Prioridad | de 1 a 3 lecciones a la vez |

- **Prioridad.** Las lecciones prioritarias se reparten la mitad de la sesión. Para un estudiante
  que ya domina una de ellas, la prioridad cede su espacio.
- **Zona de extensión.** No se configura: siempre está activa.

### Prerrequisitos, refuerzo y asignación individual

- **Prerrequisitos.** El sistema los trae por defecto según el orden del programa, y el profesor
  puede editarlos.
- **Zona de refuerzo automática** (inspirada en los Boosts de Zearn). Si el estudiante falla en
  un prerrequisito de una lección habilitada, se mezclan 1 o 2 problemas del prerrequisito por
  sesión. No habilita nada para el salón.
- **Si el problema persiste.** El profesor recibe un aviso concreto y puede **asignar la lección
  solo a ese estudiante**. La asignación individual se cierra sola cuando el estudiante domina la
  lección.

### Seguimiento (de lo general a lo particular)

1. **Panel principal.** Tabla del salón por lecciones, con el porcentaje de estudiantes que domina
   cada una.
2. **Alertas.** Quién está atascado y quién sobresale, siempre indicando la lección. Se reutilizan
   las alertas `EXCELENCIA` y `DIFICULTAD_PERSISTENTE`, que hoy funcionan por operación.
3. **Ficha del estudiante.** Es una pantalla aparte e incluye un resumen del historial de años
   anteriores.

---

## 3. Flujo del estudiante

### Avance

- **Lo decide el sistema.** Orden de criterios: prioridad del profesor, debilidad, novedad, orden
  curricular y repaso.
- **Zona de extensión.**
  - Cuando el estudiante domina una lección, se mezclan 1 o 2 problemas del paso siguiente.
  - Ese progreso se registra aparte, y fallar ahí no baja al estudiante.
  - Si acierta de forma sostenida, el profesor recibe un aviso de excelencia que sugiere habilitar
    esa lección.
  - Si falla, la extensión se pausa un tiempo, sin aviso.

### Diagnóstico inicial

- **Cuándo se hace:** solo la primera vez que el estudiante entra al sistema.
- **Cómo funciona:** recorre el grafo de forma adaptativa.
  - Empieza por las lecciones más avanzadas que habilitó el profesor.
  - Si el estudiante acierta, se dan por sabidas las anteriores.
  - Si falla, retrocede por el grafo.
- **Duración:** alrededor de 10 minutos. La cantidad de problemas se ajusta midiendo cuánto
  tardan los niños, que también tienen que interpretar las figuras.
- **Valor del resultado:** el dominio que marca es **provisional**, y la práctica lo confirma o lo
  retira con la regla absoluta. El profesor recibe el resultado.
- **Post-test:** se retira, porque solo existía para medir el efecto en la tesis.

### Motivación

- **Mapa del camino.** Las lecciones son paradas, con las dominadas encendidas y la siguiente
  visible. Va decorado según el tema narrativo.
- **Medallas.** Hay tres tipos: por lección dominada, por unidad completa y por hito de camino
  (bronce, plata y oro). Reemplazan a las medallas de nivel por operación.
- **Durante el problema.**
  - No hay efectos ni sonidos.
  - La narrativa aparece solo en el enunciado y en los íconos.
  - Las celebraciones van entre problemas y al final de la sesión.

### Funciones de IA

- **1.º y 2.º grado.**
  - No hay análisis posterior a la práctica (R1) ni mensajes motivacionales.
  - Los enunciados se generan con **plantillas**, sin DeepSeek: así el ícono y la cantidad salen
    del mismo dato que el problema.
- **Desde 3.º:** vuelven las funciones de IA.

### Registro de eventos por intento

- **Desde el principio:** qué opción eligió, si cambió de opción antes de confirmar, cuánto tardó
  y si usó la lectura en voz alta.
- **Más adelante,** en los grados que usan cuadrículas: el estado de la cuadrícula, al estilo de
  Graspable Math. Permitiría saber en qué columna se equivocó el estudiante.

---

## 4. Forma de trabajo

### Conservar la versión de la tesis

- **Rama y carpeta.** La rama `tesis` está creada desde la etiqueta `v1.0-tesis` (commit
  `a027809`) y abierta con `git worktree` en `Cap 4/Proyecto-tesis`. La rama existe solo en local;
  la etiqueta sí está en el remoto.
- **La carpeta actual no se mueve,** porque de su ruta dependen las sesiones de Claude y su
  memoria. Sigue en `master` para el desarrollo nuevo.
- **Docker.** `docker-compose.yml` fija `container_name: sti-postgres` y el puerto `5432`: las dos
  copias no pueden levantar su base de datos a la vez.
- **Base de datos de la validación.** No existe en Docker: la base `sti_db` está vacía, sin
  tablas. El Excel es el único respaldo de los datos de la validación, y una demostración en vivo
  se hará con los datos de prueba del seed.

### Cómo se construye

- **Base de datos.** El sistema nuevo empieza con la base vacía, sin migrar datos de la tesis.
- **Opción (a).** El núcleo genérico se construye **en paralelo**, en `master`, en módulos
  propios. Los decimales siguen funcionando hasta que se pasen al núcleo.

### Fases

| Fase | Contenido |
|---|---|
| 0. Preparación ✅ | Rama `tesis` con worktree, pruebas sobre PostgreSQL e integración continua mínima. Terminada en el commit `a9a85cb` |
| 1. Organización | Salón fijo, año lectivo, trimestres, grado del estudiante, grupos dentro del salón |
| 2. Currículo como datos | Catálogo de lecciones y grafo de prerrequisitos por defecto |
| 3. Núcleo de práctica | Expresión con huecos tipados, interfaz de generador de lección, dominio, reparto con prioridad, extensión, refuerzo y registro de eventos |
| 4. Pantalla genérica | Huecos, banco arrastrable, íconos agrupados en decenas, voz, ordenar; probada en tablet |
| 5. Lecciones de 1.º | Primero suma y resta (U3, U5, U7), después números (U2, U4, U6) |
| 6. Flujo del profesor | Catálogo, configuración por lección, plan por trimestre, tabla de dominio, alertas, ficha, asignación individual |
| 7. Entrada y motivación | Diagnóstico adaptativo, medallas nuevas, mapa del camino |
| 8. Lecciones de 2.º | Generadores y reglas de error nuevas (llevar, pedir prestado) |
| 9. Lo que sigue | Plan para 3.º a 6.º y para pasar los decimales al núcleo (solo plan) |

### Pruebas

- **Por generador de lección:** pruebas con muchos problemas aleatorios. Comprueban que la
  respuesta correcta es correcta, que hay entre 3 y 4 opciones distintas y solo una correcta, y
  que los números están dentro del rango de la lección.
- **Por regla de negocio:** pruebas unitarias del dominio, el reparto, la extensión, el refuerzo y
  el cierre automático de la asignación individual.
- **Estado tras la fase 0:** 190 pruebas de backend corren tanto en SQLite como en
  PostgreSQL 15, y 65 pruebas de frontend. El workflow `.github/workflows/pruebas.yml` las ejecuta
  en cada push y pull request a `master`.
- **Decisión:** las pruebas pasan a correr **solo en PostgreSQL**, el motor real. Se quita SQLite
  de las pruebas y de la integración continua (primer paso de la fase 1).

### Riesgos

- **Un núcleo con la forma de primer grado.** Se mitiga revisando cada decisión contra decimales y
  fracciones.
- **Crecimiento del alcance.** Primero y segundo grado ya suman unas 40 lecciones.
- **Sin prueba con niños hasta el final.** Por eso los parámetros son configurables. Un docente de
  primaria conocido revisará capturas o un video al terminar la fase 5. El piloto en una escuela
  se hará con el sistema terminado.
- **Cuentas y administración por escuela** siguen sin definir.

---

## 5. Preguntas abiertas

1. **Cuentas y administración por escuela.**
   - Hoy hay un único administrador global con contraseña compartida (`ADMIN_PASSWORD`), y su
     token no está ligado a ninguna organización.
   - Falta averiguar cómo funcionan los correos institucionales de MEDUCA.
   - Falta decidir si conviene importar la matrícula exportada desde MEREB. Es una plataforma
     privada, así que no todas las escuelas la usan.
2. **Estudiantes de 3.º en adelante con el banco forzado.** ¿Reciben las funciones de IA, se las
   leemos en voz alta o se omiten?
3. ~~**Base de datos de la validación.**~~ Cerrada: no existe en Docker; la demostración usa el
   seed.
4. **Valores de los parámetros.** Hay que validarlos con especialistas o con MEDUCA: criterio de
   dominio, tiempo para mandar a repaso, duración del diagnóstico, cuántos problemas de extensión
   y refuerzo se mezclan, y cuándo salta el aviso de refuerzo.
5. **Lecciones que enseñan una estrategia,** como "Sumemos completando a 10". Si solo se comprueba
   el resultado, la lección pierde su propósito.
6. **Proporción del modo "al azar"** del signo y de los íconos.
7. **Revisar los PDF de Panamáticas,** poco a poco, como referencia para las plantillas de
   enunciados.
8. **Programa oficial por trimestre.** Si se consigue el de MEDUCA, serviría para las sugerencias
   de habilitación.

---

## Fuentes consultadas

- [Khan Academy Kids: Prototyping Playful and Nimble Pre-K Assessments](https://blog.khanacademy.org/prototyping-playful-and-nimble-pre-k-assessments/)
- [Zearn: Tower Alerts Report](https://help.zearn.org/hc/en-us/articles/236239748)
- [Zearn: Boosts](https://help.zearn.org/hc/en-us/articles/1500003390061)
- [EdWeek: A personal nudge can get teachers to use student data in smart ways](https://edweek.org/teaching-learning/a-personal-nudge-can-get-teachers-to-use-student-data-in-smart-ways/2025/06)
- [IXL Diagnostic Action Plan Guide](https://ca.ixl.com/materials/diagnostic/IXL_Diagnostic_Action_Plan_Guide.pdf)
- [Khan Academy: What types of content can I assign to my students?](https://support.khanacademy.org/hc/de/articles/18564282990861)
- [Graspable Math Activities](https://sites.google.com/view/gmactivities/overview/what-is-gma)
- [MEREB (BS Educativo)](https://bseducativo.com/mrbroot/Mrbindex.aspx)
