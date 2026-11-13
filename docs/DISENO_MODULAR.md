# Diseño: STI modular para varios temas (1.º a 6.º de primaria)

Resultado de la sesión de diseño del 11 de noviembre de 2026. Es un documento de diseño:
describe decisiones y preguntas abiertas, no el estado del código. La versión anterior del
STI (solo decimales) está archivada en la etiqueta `v1.0-tesis`.

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
- **Caminos por conjunto numérico.** Naturales, decimales, fracciones y enteros, más dos
  conjuntos propios: `medida` (conversiones de unidades) y `proporcionalidad` (razones,
  porcentajes, proporciones y regla de tres). Se separan porque en cada uno cambian el
  procedimiento y los errores típicos. El sistema actual pasa a ser el camino de decimales (suma,
  resta, multiplicación y división).
- **Habilidades dentro de cada conjunto.** Un camino es un conjunto más una habilidad: por ejemplo
  `naturales.numeracion`, `naturales.suma`, `naturales.resta`, `naturales.multiplicacion` o
  `naturales.secuencias`.
  - La **numeración** (conocer, componer, ubicar y comparar números, contar) es una habilidad
    dentro de cada conjunto.
  - El camino de **secuencias** empieza en 2.º U9 L2; contar de forma progresiva o de 10 en 10
    (1.º) es numeración.
- **Una lección puede pertenecer a varios caminos.** Por ejemplo, "Sumemos y restemos 3 números"
  cuenta para suma y para resta.
- **Progresión dentro de un camino.** En naturales, la dificultad crece con el rango, con llevar
  o pedir prestado y con la cantidad de sumandos. El paso siguiente lo define el orden del
  programa: después de "Sumemos con totales hasta 99" (1.º, sin llevar) viene "Sumemos llevando"
  (2.º).
- **Catálogo de lecciones.** La fuente de verdad es `backend/curriculo/programa_meduca.yaml`,
  versionado con git. Se carga en la base con `poetry run python scripts/cargar_curriculo.py`
  (`--solo-validar` solo revisa el archivo); la carga es idempotente. Se consulta con
  `GET /api/curriculo/lecciones?grado=N` y `GET /api/curriculo/caminos` (profesor o
  administrador).
  - Contiene las 168 lecciones del programa de 1.º a 6.º. Están incluidas 118 (21 de 1.º y 17 de
    2.º); las demás aparecen igual, con el motivo de su exclusión.
  - Campos además de grado, unidad, lección y caminos: `parcial` y `nota_parcial` (la lección solo
    se cubre en parte), `presentacion_especial` (`semirrecta` o `cinta`), `cubierta_por` (por
    ejemplo, el sistema actual de decimales o el módulo experimental de regla de tres) y `notas`.
  - **Nunca se borran lecciones.** Si una lección de la base falta en el archivo, la carga se
    detiene.
- **El grafo cumple tres funciones:**
  - prerrequisitos por defecto, que el profesor puede editar (en la fase 6, en una tabla aparte
    por año lectivo, para que recargar el archivo nunca pise sus cambios);
  - "paso siguiente" para la zona de extensión;
  - "paso anterior" para la zona de refuerzo.
- **Prerrequisitos mínimos.** Una lección depende solo de lo necesario para resolverla, no de todo
  lo anterior en el programa; el orden curricular ya cuenta en el reparto de la sesión. Así no se
  bloquean sin necesidad las lecciones que el profesor habilita de otros grados.
  - Dentro de un camino, cada lección depende de la anterior, y la primera operación de un rango
    depende de la numeración de ese rango.
  - La resta de un rango depende de la suma del mismo rango, y pedir prestado depende de llevar.
  - La validación exige ids únicos, prerrequisitos existentes, **incluidos** y de un grado igual o
    menor, y que no haya ciclos.
  - El grafo está completo para 1.º y 2.º; el de 3.º a 6.º queda pendiente.
- **Exclusiones y lecciones parciales.**
  - Fuera por ahora: lecciones prenuméricas (1.º U1, emparejar objetos de 2.º U1 L3), geometría,
    medir con instrumentos, reloj analógico, monedas y billetes, ordinales y números romanos,
    estadística (incluidas las medidas de tendencia central), cálculo sobre figuras (perímetro,
    área y volumen) y álgebra, salvo "Signos de agrupación", que va a operaciones combinadas.
  - Las lecciones de medida de 3.º a 6.º están marcadas como **parciales**: solo conversiones,
    sin medir con instrumentos ni sobre figuras; las de tiempo, sin el reloj analógico.
  - Lo excluido por estadística, cálculo sobre figuras y volumen se revisa en la fase 9.

### Dominio por lección

- **Estados:** no iniciado, en progreso y dominado. No hay niveles del 1 al 5 por lección.
- **El dominio es del estudiante.** El dominio del salón o de un grupo se **calcula** a partir de
  sus estudiantes; no se guarda aparte. El progreso se conserva aunque la lección se deshabilite.
- **Criterio provisional.** Todos los valores son parámetros configurables, nunca números fijos
  en el código. Se basan en la literatura y se ajustarán con especialistas o con MEDUCA.
  - **Para declarar dominio:** al menos 80 % de aciertos en los últimos 10 problemas, en 2 o más
    días distintos (fecha de Panamá). Solo cuenta como acierto el primer intento sin la pista de
    nivel 3.
  - **Para mandar a repaso:** 14 días sin practicar la lección.
  - **Para volver a "en progreso":** menos de 60 % en los primeros 5 problemas del repaso.
  - El **dominio provisional** del diagnóstico se confirma o se retira con estas mismas reglas.
  - Implementado en `backend/app/nucleo/dominio.py`; los valores están en
    `backend/app/nucleo/parametros.py` y se pueden cambiar con claves `nucleo.*` en
    `configuracion_sistema`.
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
  - **Por grado:** siempre en 1.º y 2.º, en 3.º según la lección, y teclado desde 4.º. Cuenta el
    grado del **estudiante**, no el de la lección: un estudiante de 4.º que repasa una lección de
    1.º usa teclado, salvo que tenga el banco forzado.
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
  - **Comportamiento en pantalla (fase 4).** Las fichas no se gastan: la misma puede ir a varios
    huecos. Soltar otra ficha sobre un hueco ocupado la cambia y registra `cambio_opcion`. Tocar
    un hueco solo elige qué banco se muestra; no coloca nada. Se usa `@dnd-kit` (ratón, toque y
    teclado).
- **Validación (implementada en la fase 3).**
  - Los números se comparan por su valor exacto, sin redondear.
  - Las fracciones aceptan las equivalentes, salvo que el hueco lo desactive.
  - Las cantidades con unidades se exigen normalizadas, salvo que el hueco acepte otra forma.
  - Una respuesta con forma inválida (un hueco vacío, un valor que no está en el banco) no cuenta
    como intento.
  - Las reglas de error usan códigos con el camino delante (por ejemplo `naturales.suma.resto`).
    Si varias reglas producen la misma respuesta, gana la primera de la lista.
  - El problema llega a la pantalla sin las respuestas correctas, sin los datos internos del
    generador y sin la regla de error de cada opción.

### Presentación

- **Íconos más texto.** Hasta 10 van sueltos en filas de 5; desde 11 se agrupan en barras de 10
  y unidades sueltas (el umbral es una constante del frontend). Usan el objeto del tema narrativo,
  por ahora como emoji, que se ven distintos en cada sistema operativo. Entre los grupos no se
  dibuja el signo, para no revelarlo cuando está oculto.
- **Lectura en voz alta.** Es opcional, como recurso de accesibilidad. Usa la voz en español del
  navegador; si no la hay, el botón no aparece.
- **Dispositivos.** Todo el flujo del estudiante debe funcionar en computadora y en tablet, con
  ratón y con toque.
  - En horizontal, desde 768 px de ancho, la pantalla va en dos columnas: a la izquierda la
    instrucción, los íconos y la expresión; a la derecha el banco o el teclado y "Comprobar". En
    vertical o en pantallas angostas va en una columna. Se decide solo con CSS y girar la tablet
    no borra la respuesta colocada.
  - Pendiente: probar con toque en una tablet real, en ambas orientaciones.
- **Enunciados.** La referencia de estilo son los libros Panamáticas de cada grado. En la fase 4
  la pantalla muestra una instrucción genérica según la forma del problema; las plantillas con el
  tema llegan en la fase 5.
- **Presentaciones especiales.** La semirrecta y la cinta (`presentacion_especial`) se hacen en la
  fase 5, con las lecciones que las usan.

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
- **Trimestres.** Son por organización y año. Fechas por defecto: el año empieza el primer lunes
  de marzo, con 3 trimestres de 13 semanas y una semana de vacaciones entre ellos (en 2026 va del
  2 de marzo al 11 de diciembre). Las fechas las cambia el **administrador, para toda la
  escuela**, no cada profesor. Hoy solo existe un administrador global, así que hasta que haya
  administración por escuela ese administrador las edita por organización.
- **Cierre del año.** Lo hace el administrador, por organización. Después cada profesor abre su
  salón para el año nuevo (el salón conserva su id) y vuelve a asignar a sus estudiantes.
- **Profesores.** Un profesor puede tener varios salones el mismo año.
- **Matrícula.** Un estudiante tiene una sola matrícula activa; lo garantiza la base de datos. Si
  ya está en otro salón, se rechaza la asignación: su profesor actual debe quitarlo primero.
- **Grado del estudiante.** Ya no es texto libre: sale del salón. La importación por Excel acepta
  la columna de grado, pero la ignora.
- **Grupos.** Son subconjuntos opcionales dentro del salón, por ejemplo para desafíos.
  - Se cierran junto con el año lectivo y quedan de solo lectura en el historial. No se
    reutilizan al año siguiente, porque un profesor puede tener salones distintos cada año.
  - Un grupo eliminado solo se desactiva.
- **Desafíos.** Son siempre de un solo salón; no hay desafíos entre salones.
  - Si no se eligen grupos, el salón completo compite como un solo equipo.
  - Un desafío sin terminar al cerrar el año pasa a "no completado", conservando los puntos ya
    otorgados.
- **No se borra nada con historial.** No se puede eliminar un profesor ni una organización que
  tengan salones.
- **Estudiante sin salón.** No puede practicar: se bloquean la práctica, la redención, la regla de
  tres y el diagnóstico. Ve un mensaje que le pide consultar a su profesor. El post-test no se
  bloquea, porque se retirará en una fase posterior.

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
  curricular y repaso. Como quedó implementado en la fase 3 (`backend/app/nucleo/reparto.py`):
  1. Las lecciones prioritarias reciben la mitad de la sesión y ceden su espacio si el estudiante
     ya las domina.
  2. Siguen el refuerzo y la extensión, con 2 problemas cada uno.
  3. El resto va, en orden, a las lecciones más débiles, a una lección nueva y al repaso, que
     siempre conserva un lugar.
  4. La sesión nunca empieza con un problema de extensión o de refuerzo.
  5. Si no queda nada pendiente, se practican las lecciones dominadas que hace más tiempo que no
     se ven.
- **Lecciones nuevas.** Entran solo cuando sus prerrequisitos que también están habilitados ya
  están dominados. Un prerrequisito que el profesor no habilitó no bloquea.
- **Zona de extensión.**
  - Va a las lecciones siguientes en el grafo de una lección habilitada que el estudiante ya
    domina: 1 o 2 problemas por sesión.
  - Ese progreso se registra aparte, y fallar ahí no baja al estudiante.
  - Si acierta de forma sostenida, el profesor recibe un aviso de excelencia que sugiere habilitar
    esa lección (fase 6).
  - Tras 2 fallos, la extensión se pausa 7 días, sin aviso.
- **Zona de refuerzo.**
  - Se activa cuando una lección en progreso tiene menos de 60 % con al menos 5 problemas.
  - Va a sus prerrequisitos directos no dominados que no están habilitados, y esos problemas
    cuentan para el dominio del prerrequisito.
- **Sesión a medias (fase 4).** Igual que en el sistema de decimales: si el estudiante sale a mitad
  de la práctica, al volver la retoma en el mismo problema, o la descarta.
  - El dashboard muestra "Tienes una práctica a medias" con "Continuar" y "Descartar".
  - Al descartarla, la sesión queda `abandonada`: el problema pendiente no cuenta para el dominio
    ni da experiencia, y los intentos ya hechos quedan registrados.
  - Una recarga de la página durante la práctica retoma sin preguntar.
- **Entrada mientras conviven los dos sistemas.** `GET /api/nucleo/estado` dice si el estudiante
  practica en el núcleo (su salón tiene lecciones habilitadas). En ese caso "Practicar" lleva a
  `/student/nucleo` y se ocultan los avisos de diagnóstico y post-test de decimales; si no, sigue
  la práctica de decimales. Sin salón, el núcleo no está disponible.

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
- **Post-test:** se retira, porque solo existía para medir el efecto del sistema en la
  validación de la versión anterior.

### Motivación

- **Mapa del camino.** Las lecciones son paradas, con las dominadas encendidas y la siguiente
  visible. Va decorado según el tema narrativo.
- **Medallas.** Hay tres tipos: por lección dominada, por unidad completa y por hito de camino
  (bronce, plata y oro). Reemplazan a las medallas de nivel por operación.
- **Nivel de jugador.** Es una recompensa de gamificación, distinta del dominio: no decide qué
  problemas recibe el estudiante.
  - Se calcula con **experiencia acumulada**: experiencia por practicar y acertar, más un bono
    grande al dominar una lección. Nunca baja, aunque una lección vuelva a "en progreso".
  - La experiencia es un contador aparte del saldo de puntos. `puntos_totales` es en realidad el
    saldo y baja al comprar en la tienda, así que no sirve para el nivel.
  - La fórmula del nivel y la barra de experiencia se definen en la fase 7.
  - Desde la fase 3 ya se registra: 1 de experiencia por problema terminado y 2 por acierto al
    primer intento (también si usó la pista de nivel 3), más el evento de "lección dominada" con
    la marca `primera_vez`, para decidir después cómo se da el bono.
- **Barras de progreso.** Nunca durante la práctica.
  - **Avance de cada camino:** lecciones dominadas sobre el total del camino.
  - **Avance hacia el dominio de cada lección.** Con la regla de "80 % de los últimos 10" puede
    retroceder, así que debe mostrarse de forma que no parezca un castigo.
  - **Experiencia hacia el siguiente nivel:** pendiente de la fase 7.
- **Durante el problema.**
  - No hay efectos ni sonidos.
  - La narrativa aparece solo en el enunciado y en los íconos.
  - Las celebraciones van entre problemas y al final de la sesión.
  - Un intento incorrecto solo marca el hueco en naranja y dice cuántos intentos quedan. La
    solución se muestra entre problemas, al agotar los intentos.
  - Se muestra el contador "3 de 10", sin barra de progreso.

### Funciones de IA

- **1.º y 2.º grado.**
  - No hay análisis posterior a la práctica (R1) ni mensajes motivacionales.
  - Los enunciados se generan con **plantillas**, sin DeepSeek: así el ícono y la cantidad salen
    del mismo dato que el problema.
- **Desde 3.º:** vuelven las funciones de IA.

### Registro de eventos por intento

- **Desde el principio:** qué opción eligió, si cambió de opción antes de confirmar, cuánto tardó
  y si usó la lectura en voz alta.
  - Eventos que envía la pantalla con cada intento: `opcion_elegida`, `cambio_opcion`, `voz` y,
    en la forma de ordenar, `orden_cambiado`. Cada uno lleva `ms` contado desde que se mostró el
    problema.
  - `tiempo_ms` se cuenta desde que empezó el intento: el primero, al mostrarse el problema; los
    siguientes, al recibir la corrección del anterior.
  - Si el envío falla, los eventos se conservan para el siguiente envío.
- **Más adelante,** en los grados que usan cuadrículas: el estado de la cuadrícula, al estilo de
  Graspable Math. Permitiría saber en qué columna se equivocó el estudiante.

---

## 4. Forma de trabajo

### Conservar la versión archivada

- **Rama y carpeta.** La rama `tesis` está creada desde la etiqueta `v1.0-tesis` (commit
  `a027809`) y abierta con `git worktree` en `Cap 4/Proyecto-tesis`. La rama existe solo en local;
  la etiqueta sí está en el remoto.
- **La carpeta actual no se mueve,** porque de su ruta dependen las sesiones de Claude y su
  memoria. Sigue en `master` para el desarrollo nuevo.
- **Bases de datos locales.** Viven en PostgreSQL 14 de Homebrew, no en Docker: `sti_db`
  (desarrollo), `sti_tesis` (copia archivada, con datos sembrados) y `sti_test` (pruebas). El
  contenedor Docker `sti-postgres` no se usa y su volumen está vacío; si se enciende, choca con
  Homebrew en el puerto 5432. Las dos copias del código usan los mismos puertos 8000 y 5173, así
  que no se ejecutan a la vez.
- **Datos de la validación.** El Excel es el único respaldo. Una demostración en vivo se hace con
  datos sembrados.

### Cómo se construye

- **Base de datos.** El sistema nuevo empieza con la base vacía, sin migrar datos de la versión anterior.
- **Opción (a).** El núcleo genérico se construye **en paralelo**, en `master`, en módulos
  propios. Los decimales siguen funcionando hasta que se pasen al núcleo.

### Fases

| Fase | Contenido |
|---|---|
| 0. Preparación ✅ | Rama `tesis` con worktree, pruebas sobre PostgreSQL e integración continua mínima. Terminada en el commit `a9a85cb` |
| 1. Organización ✅ | Salón fijo, año lectivo, trimestres, grado del estudiante, grupos dentro del salón. Terminada en el commit `20bb519` |
| 2. Currículo como datos ✅ | Catálogo de lecciones y grafo de prerrequisitos por defecto (completo para 1.º y 2.º) |
| 3. Núcleo de práctica ✅ | Paquete `backend/app/nucleo/`, tablas `nucleo_*` y API `/api/nucleo`. Expresión con huecos tipados, interfaz de generador de lección, dominio, reparto con prioridad, extensión, refuerzo y registro de eventos |
| 4. Pantalla genérica ✅ | Página `/student/nucleo`: huecos, banco arrastrable, teclado, ordenar, íconos agrupados en decenas, voz, sesión a medias y dos columnas en horizontal. Verificada en el navegador; falta probarla en una tablet real |
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
- **Estado tras la fase 4:** 410 pruebas de backend, **solo en PostgreSQL** (SQLite se quitó de
  las pruebas, de la integración continua y de las dependencias), y 106 de frontend (41 de la pantalla del núcleo). Ordenar, fracción, cantidad y teclado
  solo tienen pruebas de Vitest hasta que un generador los produzca (fase 5). El
  workflow `.github/workflows/pruebas.yml` las ejecuta en cada push y pull request a `master`.

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
5. **Lecciones que enseñan una estrategia,** como "Sumemos completando a 10". Resuelta en parte:
   el generador usa huecos para los pasos de la estrategia (`8 + 5 = 8 + _ + _ = _`), así que no
   basta con dar el resultado. Falta confirmar que esto sirve para otras lecciones de estrategia.
6. **Proporción del modo "al azar"** del signo y de los íconos.
7. **Revisar los PDF de Panamáticas,** poco a poco, como referencia para las plantillas de
   enunciados.
8. **Programa oficial por trimestre.** Si se consigue el de MEDUCA, serviría para las sugerencias
   de habilitación.
9. **Desafíos con varios grupos.** Hoy, cuando el primer equipo completa un desafío, el desafío
   entero pasa a "completado" y los demás equipos dejan de sumar. ¿Debería seguir abierto hasta
   la fecha límite para que los demás equipos también puedan completarlo?
10. **Traslado de un estudiante.** Si su profesor actual no lo quita del salón, nadie más puede
    asignarlo. ¿Debería poder hacerlo el administrador?
11. **Prerrequisitos de la gráfica de cinta** (2.º U4 L4). Hoy depende de sumar llevando y de
    restar pidiendo prestado con 2 cifras. Hay que verificar en Panamáticas qué rango usa.
12. **Medidas de volumen** (6.º U6 L4). Quedó excluida como cálculo sobre figuras, pero si es
    conversión de unidades debería incluirse como parcial, igual que las de superficie.
13. **Grafo de prerrequisitos de 3.º a 6.º.** Pendiente; hace falta antes de construir esos grados.
14. **Tienda y nivel de jugador.** Hoy los artículos de la tienda exigen un `nivel_minimo_requerido`
    que se compara con el nivel adaptativo de 1 a 5, que va a desaparecer. ¿El nivel de jugador
    reemplaza ese requisito?
15. **Bono por dominar una lección.** ¿Se da una sola vez por lección, o cada vez que el
    estudiante la vuelve a dominar después de un repaso fallido?

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
