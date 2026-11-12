"""
Núcleo genérico de práctica del STI modular (fase 3, docs/DISENO_MODULAR.md).

Va en paralelo al sistema de decimales: no usa sus modelos ni sus servicios.

- problema.py: el problema como expresión con huecos tipados, y la forma aparte de ordenar.
- validacion.py: interpretación y validación de la respuesta de cada tipo de hueco.
- errores.py: reglas de error por camino (clasificación y fuente de opciones incorrectas).
- banco.py: banco de opciones para arrastrar.
- modos.py: signo, íconos y banco o teclado, por lección y por estudiante.
- parametros.py: todos los valores ajustables del núcleo, configurables sin tocar el código.
- generador.py: interfaz del generador de lección.
- registro.py: generadores disponibles, por id de lección.
- lecciones/: un generador por lección, agrupados por conjunto numérico.
"""
