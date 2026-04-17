"""
Service de generación y validación de problemas matemáticos.

Implementa algoritmos de generación aleatoria por nivel de dificultad.
"""

import random
from typing import List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status

from app.repositories.problem_repository import ProblemRepository
from app.models.problem import Operacion, TipoSesion, Problema, Intento
from app.schemas.problem import (
    ProblemaGenerate,
    ProblemaResponse,
    ProblemaDisplay,
    ValidateAnswerResponse,
    SubmitAnswerRequest,
    IntentoResponse
)


class ProblemService:
    """Service para generación y validación de problemas."""
    
    # Configuración por defecto según nivel de dificultad
    NIVEL_CONFIG = {
        1: {
            "operaciones": [Operacion.SUMA, Operacion.RESTA],
            "rango": (1, 20),
            "decimales": 0,
        },
        2: {
            "operaciones": [Operacion.SUMA, Operacion.RESTA],
            "rango": (1, 50),
            "decimales": 1,
        },
        3: {
            "operaciones": [Operacion.SUMA, Operacion.RESTA, Operacion.MULTIPLICACION],
            "rango": (1, 100),
            "decimales": 2,
        },
        4: {
            "operaciones": [Operacion.SUMA, Operacion.RESTA, Operacion.MULTIPLICACION, Operacion.DIVISION],
            "rango": (1, 100),
            "decimales": 2,
        },
        5: {
            "operaciones": [Operacion.SUMA, Operacion.RESTA, Operacion.MULTIPLICACION, Operacion.DIVISION],
            "rango": (1, 200),
            "decimales": 3,
        },
    }
    
    def __init__(self, problem_repo: ProblemRepository):
        self.problem_repo = problem_repo
    
    # ============================================
    # Generación de Problemas
    # ============================================
    
    async def generate_problems(
        self,
        request: ProblemaGenerate
    ) -> List[ProblemaDisplay]:
        """
        Genera una lista de problemas matemáticos según parámetros.
        
        Args:
            request: Parámetros de generación
            
        Returns:
            Lista de problemas (sin mostrar resultado)
        """
        # Obtener configuración del nivel
        config = self.NIVEL_CONFIG.get(request.nivel_dificultad)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nivel {request.nivel_dificultad} no válido"
            )
        
        # Usar parámetros custom o defaults del nivel
        operaciones = request.operaciones_permitidas or config["operaciones"]
        decimales_max = request.decimales_maximos if request.decimales_maximos is not None else config["decimales"]
        rango_min = request.rango_min or config["rango"][0]
        rango_max = request.rango_max or config["rango"][1]
        
        problemas = []
        
        for _ in range(request.cantidad):
            # Generar un problema
            problema = await self._generate_single_problem(
                nivel=request.nivel_dificultad,
                operaciones=operaciones,
                decimales_max=decimales_max,
                rango_min=rango_min,
                rango_max=rango_max
            )
            
            # Convertir a display (sin resultado)
            problemas.append(ProblemaDisplay(
                id=problema.id,
                operacion=problema.operacion.value,
                numero1=problema.numero1,
                numero2=problema.numero2,
                nivel_dificultad=problema.nivel_dificultad
            ))
        
        return problemas
    
    async def _generate_single_problem(
        self,
        nivel: int,
        operaciones: List[Operacion],
        decimales_max: int,
        rango_min: int,
        rango_max: int
    ) -> Problema:
        """
        Genera un solo problema matemático.
        
        Intenta reutilizar problemas existentes (por signature).
        Si no existe, lo crea.
        """
        # Elegir operación aleatoria
        operacion = random.choice(operaciones)
        
        # Generar números según operación y parámetros
        numero1, numero2 = self._generate_numbers(
            operacion=operacion,
            rango_min=rango_min,
            rango_max=rango_max,
            decimales_max=decimales_max,
            nivel=nivel,
        )
        
        # Calcular resultado
        resultado = self._calculate_result(operacion, numero1, numero2)
        
        # Contar decimales reales (después de calcular)
        cantidad_decimales = max(
            self._count_decimals(numero1),
            self._count_decimals(numero2),
            self._count_decimals(resultado)
        )
        
        # Generar signature única
        signature = self._generate_signature(operacion, numero1, numero2)
        
        # Buscar si ya existe este problema
        problema_existente = await self.problem_repo.get_problem_by_signature(signature)
        
        if problema_existente:
            return problema_existente
        
        # Crear nuevo problema
        problema = await self.problem_repo.create_problem(
            operacion=operacion,
            numero1=numero1,
            numero2=numero2,
            resultado=resultado,
            nivel_dificultad=nivel,
            cantidad_decimales=cantidad_decimales,
            signature=signature
        )
        
        return problema
    
    def _generate_numbers(
        self,
        operacion: Operacion,
        rango_min: int,
        rango_max: int,
        decimales_max: int,
        nivel: int = 1,
    ) -> Tuple[Decimal, Decimal]:
        """
        Genera dos números aleatorios según la operación.

        Para división, asegura que el resultado sea exacto (sin residuo infinito).
        La precisión del cociente depende del nivel de dificultad:
          - Nivel 3: cociente X.5 (mitades), divisor=2, dividendo entero
          - Nivel 4: cociente con 1 decimal, divisor entero ∈ {2, 4, 5}
          - Nivel 5: hasta 2 decimales; mix de escalamiento/vertical/normalización
          - Default: cociente entero (escalamiento puro)
        """
        if operacion == Operacion.DIVISION:
            if nivel == 3:
                # Cociente con 1 decimal; divisores {2, 5} para resultados "bonitos"
                divisor = Decimal(random.choice([2, 5]))
                cociente_entero = random.randint(1, 9)
                if divisor == Decimal(2):
                    cociente_dec = Decimal('0.5')
                else:  # divisor == 5
                    cociente_dec = Decimal(random.choice(['0.2', '0.4', '0.6', '0.8']))
                cociente = Decimal(cociente_entero) + cociente_dec
                dividendo = (divisor * cociente).quantize(
                    Decimal('0.1'), rounding=ROUND_HALF_UP
                )
                return dividendo, divisor

            elif nivel == 4:
                # Cociente con exactamente 1 decimal; divisor entero ∈ {2, 4, 5}
                # Estos divisores garantizan que dividendo tenga ≤ 1 decimal
                divisor = Decimal(random.choice([2, 4, 5]))
                cociente_entero = random.randint(1, 9)
                cociente_dec = random.randint(1, 9)   # parte decimal no nula
                cociente = Decimal(f"{cociente_entero}.{cociente_dec}")
                dividendo = (divisor * cociente).quantize(
                    Decimal('0.1'), rounding=ROUND_HALF_UP
                )
                return dividendo, divisor

            elif nivel == 5:
                # Variedad: escalamiento, vertical o normalización
                tipo = random.choice(['escalamiento', 'vertical', 'normalizacion'])

                if tipo == 'escalamiento':
                    # Ambos enteros, cociente entero
                    divisor = Decimal(random.randint(2, 20))
                    multiplicador = random.randint(2, 15)
                    dividendo = divisor * Decimal(multiplicador)
                    return dividendo, divisor

                elif tipo == 'vertical':
                    # Divisor entero ∈ {2,4,5,10}; dividendo con decimales;
                    # cociente con 1 ó 2 decimales
                    divisor = Decimal(random.choice([2, 4, 5, 10]))
                    cociente_entero = random.randint(1, 9)
                    num_decimals = random.choice([1, 2])
                    if num_decimals == 1:
                        d = random.randint(1, 9)
                        cociente = Decimal(f"{cociente_entero}.{d}")
                        dividendo = (divisor * cociente).quantize(
                            Decimal('0.1'), rounding=ROUND_HALF_UP
                        )
                    else:
                        d1 = random.randint(0, 9)
                        d2 = random.randint(1, 9)
                        cociente = Decimal(f"{cociente_entero}.{d1}{d2}")
                        dividendo = (divisor * cociente).quantize(
                            Decimal('0.01'), rounding=ROUND_HALF_UP
                        )
                    return dividendo, divisor

                else:   # normalizacion
                    # Divisor con 1 decimal; cociente entero (≤ 2 dec garantizado)
                    div_ent = random.randint(1, 9)
                    div_dec = random.randint(1, 9)
                    divisor = Decimal(f"{div_ent}.{div_dec}")
                    cociente = Decimal(random.randint(2, 9))
                    dividendo = (divisor * cociente).quantize(
                        Decimal('0.1'), rounding=ROUND_HALF_UP
                    )
                    return dividendo, divisor

            else:
                # Default (niveles 1-2): divisor pequeño, cociente entero
                divisor = Decimal(random.randint(2, 9))
                multiplicador = random.randint(2, 10)
                dividendo = divisor * Decimal(multiplicador)
                return dividendo, divisor
        
        elif operacion == Operacion.MULTIPLICACION:
            # Para multiplicación, usar rangos más pequeños para evitar resultados gigantes
            numero1 = self._random_decimal(rango_min, min(rango_max, 50), decimales_max)
            numero2 = self._random_decimal(rango_min, min(rango_max, 20), min(decimales_max, 1))
            return numero1, numero2
        
        else:
            # Suma y Resta: números normales
            numero1 = self._random_decimal(rango_min, rango_max, decimales_max)
            numero2 = self._random_decimal(rango_min, rango_max, decimales_max)
            
            # Para resta, asegurar que numero1 >= numero2 (no negativos)
            if operacion == Operacion.RESTA and numero1 < numero2:
                numero1, numero2 = numero2, numero1
            
            return numero1, numero2
    
    def _random_decimal(
        self,
        min_val: int,
        max_val: int,
        decimales_max: int
    ) -> Decimal:
        """Genera un número decimal aleatorio que no supera max_val."""
        if decimales_max == 0:
            # Entero
            return Decimal(random.randint(min_val, max_val))
        
        # Para números con decimales, asegurar que el total no supere max_val
        # Ajustamos el rango del entero para dejar espacio a los decimales
        entero = random.randint(min_val, max_val - 1)
        
        # Generar parte decimal
        if decimales_max == 1:
            decimal_part = random.choice([0, 5])  # .0 o .5
        else:
            # Aleatorio entre 0 y 10^decimales_max - 1
            decimal_part = random.randint(0, 10**decimales_max - 1)
        
        # Combinar
        numero = Decimal(f"{entero}.{decimal_part:0{decimales_max}d}")
        
        # Verificar que no supere max_val
        if numero > Decimal(max_val):
            numero = Decimal(max_val)
        
        return numero
    
    def _calculate_result(
        self,
        operacion: Operacion,
        numero1: Decimal,
        numero2: Decimal
    ) -> Decimal:
        """Calcula el resultado de la operación."""
        if operacion == Operacion.SUMA:
            return numero1 + numero2
        elif operacion == Operacion.RESTA:
            return numero1 - numero2
        elif operacion == Operacion.MULTIPLICACION:
            return numero1 * numero2
        elif operacion == Operacion.DIVISION:
            # Redondear a 3 decimales para evitar infinitos
            return (numero1 / numero2).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        else:
            raise ValueError(f"Operación no soportada: {operacion}")
    
    def _count_decimals(self, numero: Decimal) -> int:
        """Cuenta cuántos decimales tiene un número."""
        # Convertir a string y contar después del punto
        numero_str = str(numero)
        if '.' in numero_str:
            return len(numero_str.split('.')[1].rstrip('0'))
        return 0
    
    def _generate_signature(
        self,
        operacion: Operacion,
        numero1: Decimal,
        numero2: Decimal
    ) -> str:
        """
        Genera una signature única para el problema.
        
        Formato: "{operacion}_{numero1}_{numero2}"
        Ejemplo: "plus_12.50_8.30"
        """
        op_name = {
            Operacion.SUMA: "plus",
            Operacion.RESTA: "minus",
            Operacion.MULTIPLICACION: "times",
            Operacion.DIVISION: "div"
        }[operacion]
        
        return f"{op_name}_{numero1}_{numero2}"
    
    def _round_to_decimals(self, numero: Decimal, decimales: int) -> Decimal:
        """Redondea un número a N decimales."""
        if decimales == 0:
            return numero.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        formato = '0.' + '0' * decimales
        return numero.quantize(Decimal(formato), rounding=ROUND_HALF_UP)
    
    # ============================================
    # Validación de Respuestas
    # ============================================
    
    async def validate_answer(
        self,
        problema_id: int,
        respuesta_estudiante: Decimal
    ) -> ValidateAnswerResponse:
        """
        Valida la respuesta de un estudiante.
        
        Args:
            problema_id: ID del problema
            respuesta_estudiante: Respuesta del estudiante
            
        Returns:
            Resultado de la validación con mensaje
        """
        # Obtener problema
        problema = await self.problem_repo.get_problem_by_id(problema_id)
        
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problema no encontrado"
            )
        
        # Comparar respuestas (con tolerancia de 0.01 para decimales)
        tolerancia = Decimal("0.01")
        diferencia = abs(respuesta_estudiante - problema.resultado)
        es_correcto = diferencia <= tolerancia
        
        # Generar mensaje
        if es_correcto:
            mensaje = "¡Correcto! Excelente trabajo."
        else:
            mensaje = f"Incorrecto. La respuesta correcta es {problema.resultado}"
        
        return ValidateAnswerResponse(
            es_correcto=es_correcto,
            respuesta_correcta=problema.resultado,
            respuesta_estudiante=respuesta_estudiante,
            diferencia=diferencia if not es_correcto else None,
            mensaje=mensaje
        )
    
    async def submit_answer(
        self,
        estudiante_id: int,
        request: SubmitAnswerRequest
    ) -> IntentoResponse:
        """
        Registra el intento de un estudiante y valida la respuesta.
        
        Args:
            estudiante_id: ID del estudiante
            request: Datos del intento
            
        Returns:
            Intento registrado con validación
        """
        # Validar respuesta
        validacion = await self.validate_answer(
            problema_id=request.problema_id,
            respuesta_estudiante=request.respuesta_estudiante
        )
        
        # Registrar intento
        intento = await self.problem_repo.create_intento(
            estudiante_id=estudiante_id,
            problema_id=request.problema_id,
            respuesta_estudiante=request.respuesta_estudiante,
            es_correcto=validacion.es_correcto,
            tiempo_resolucion=request.tiempo_resolucion,
            solicito_pista=request.solicito_pista,
            tipo_sesion=request.tipo_sesion
        )
        
        # Obtener problema completo para response
        problema = await self.problem_repo.get_problem_by_id(request.problema_id)
        
        # Construir response
        return IntentoResponse(
            id=intento.id,
            problema_id=intento.problema_id,
            estudiante_id=intento.estudiante_id,
            respuesta_estudiante=intento.respuesta_estudiante,
            es_correcto=intento.es_correcto,
            tiempo_resolucion=intento.tiempo_resolucion,
            solicito_pista=intento.solicito_pista,
            tipo_sesion=intento.tipo_sesion.value,
            timestamp=intento.timestamp,
            problema=ProblemaResponse.model_validate(problema)
        )
    
    async def get_problem_by_id(self, problema_id: int) -> ProblemaResponse:
        """Obtiene un problema por ID."""
        problema = await self.problem_repo.get_problem_by_id(problema_id)
        
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problema no encontrado"
            )
        
        return ProblemaResponse.model_validate(problema)
