"""
Service del sistema adaptativo.

Lógica central de diagnóstico, generación de prácticas, ajuste de niveles.
"""

import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException, status

from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.problem_repository import ProblemRepository
from app.services.ml_service import ml_service
from app.services.problem_service import ProblemService
from app.models.adaptive import PerfilEstudiante, PruebaDiagnostica, SesionPractica, EstadoDiagnostico
from app.models.user import Estudiante
from app.models.problem import Operacion, TipoSesion
from app.schemas.adaptive import (
    DiagnosticoResultado,
    SesionStartResponse,
    SesionCompleteResponse,
    CambioNivel,
    PerfilResponse,
    Recomendacion,
    EstadisticasGrupo
)
from app.schemas.problem import ProblemaDisplay


class AdaptiveService:
    """Service para sistema adaptativo y machine learning."""
    
    # Prerequisitos para cada operación
    PREREQUISITOS = {
        Operacion.SUMA: {},
        Operacion.RESTA: {},
        Operacion.MULTIPLICACION: {
            Operacion.SUMA: 2,
            Operacion.RESTA: 2
        },
        Operacion.DIVISION: {
            Operacion.SUMA: 2,
            Operacion.RESTA: 2,
            Operacion.MULTIPLICACION: 2
        }
    }
    
    # Ratios de dificultad por nivel general
    RATIOS = {
        1: {"faciles": 0.7, "desafiantes": 0.3},
        2: {"faciles": 0.6, "desafiantes": 0.4},
        3: {"faciles": 0.5, "desafiantes": 0.5},
        4: {"faciles": 0.4, "desafiantes": 0.6},
        5: {"faciles": 0.3, "desafiantes": 0.7}
    }
    
    # Cantidad de problemas por nivel
    PROBLEMAS_POR_NIVEL = {
        1: 10,
        2: 10,
        3: 15,
        4: 15,
        5: 20
    }
    
    def __init__(
        self,
        adaptive_repo: AdaptiveRepository,
        problem_repo: ProblemRepository,
        problem_service: ProblemService
    ):
        self.adaptive_repo = adaptive_repo
        self.problem_repo = problem_repo
        self.problem_service = problem_service
    
    # ============================================
    # Diagnóstico Inicial
    # ============================================
    
    async def generar_diagnostico(self, estudiante_id: int) -> Dict:
        """
        Genera prueba diagnóstica de 8 problemas.

        2 problemas por operación: 1 nivel 2, 1 nivel 3
        """
        # Verificar que no tenga diagnóstico previo
        diagnostico_previo = await self.adaptive_repo.get_diagnostico_by_estudiante(estudiante_id)
        if diagnostico_previo and diagnostico_previo.estado == EstadoDiagnostico.COMPLETADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya completaste el diagnóstico inicial"
            )

        # Generar 8 problemas (2 por operación)
        problemas = []
        operaciones = [Operacion.SUMA, Operacion.RESTA, Operacion.MULTIPLICACION, Operacion.DIVISION]

        for operacion in operaciones:
            # Problema nivel 2 (decimales de 1 cifra, rango 1-50)
            prob_n2 = await self.problem_service._generate_single_problem(
                nivel=2,
                operaciones=[operacion],
                decimales_max=1,
                rango_min=1,
                rango_max=50
            )
            problemas.append(prob_n2)

            # Problema nivel 3 (decimales de 2 cifras, rango 1-100)
            prob_n3 = await self.problem_service._generate_single_problem(
                nivel=3,
                operaciones=[operacion],
                decimales_max=2,
                rango_min=1,
                rango_max=100
            )
            problemas.append(prob_n3)
        
        # Crear registro de diagnóstico
        problemas_ids = [p.id for p in problemas]
        diagnostico = await self.adaptive_repo.create_diagnostico(estudiante_id, problemas_ids)
        
        # Convertir a display
        problemas_display = [
            ProblemaDisplay(
                id=p.id,
                operacion=p.operacion.value,
                numero1=p.numero1,
                numero2=p.numero2,
                nivel_dificultad=p.nivel_dificultad
            )
            for p in problemas
        ]
        
        return {
            "diagnostico_id": diagnostico.id,
            "problemas": problemas_display,
            "mensaje": "Resuelve estos 8 problemas para determinar tu nivel inicial"
        }
    
    async def evaluar_diagnostico(
        self,
        diagnostico_id: int,
        respuestas: Dict[int, Decimal]
    ) -> DiagnosticoResultado:
        """
        Evalúa diagnóstico y asigna niveles iniciales.
        
        Args:
            diagnostico_id: ID del diagnóstico
            respuestas: Mapa de problema_id -> respuesta
        """
        # Obtener diagnóstico
        diagnostico = await self.adaptive_repo.get_diagnostico(diagnostico_id)
        if not diagnostico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnóstico no encontrado"
            )
        
        # Obtener problemas
        problemas_ids = diagnostico.problemas_ids
        resultados = {
            "suma": [],
            "resta": [],
            "multiplicacion": [],
            "division": []
        }
        
        tiempos = {
            "suma": 0,
            "resta": 0,
            "multiplicacion": 0,
            "division": 0
        }
        
        # Evaluar cada respuesta
        for problema_id in problemas_ids:
            problema = await self.problem_repo.get_problem_by_id(problema_id)
            if not problema:
                continue
            
            respuesta = respuestas.get(problema_id)
            if respuesta is None:
                continue
            
            # Validar respuesta
            es_correcto = abs(respuesta - problema.resultado) <= Decimal("0.01")
            
            # Mapear operación a key
            op_key = problema.operacion.value
            if op_key == "+":
                op_key = "suma"
            elif op_key == "-":
                op_key = "resta"
            elif op_key == "×":
                op_key = "multiplicacion"
            elif op_key == "÷":
                op_key = "division"
            
            resultados[op_key].append(es_correcto)
        
        # Contar correctos por operación
        correctos_por_operacion = {
            op: sum(resultados[op])
            for op in resultados
        }
        
        # Asignar niveles
        total_correctos = sum(correctos_por_operacion.values())
        
        if total_correctos == 8:
            # CASO ESPECIAL: Todas correctas → Nivel 4, todas operaciones nivel 2
            niveles = {
                "suma": 2,
                "resta": 2,
                "multiplicacion": 2,
                "division": 2,
                "actual": 4
            }
            mensaje = "¡Perfecto! Empezarás en nivel avanzado 4"
            perfecto = True
        else:
            # Asignar nivel por operación
            niveles = {}
            for op, correctos in correctos_por_operacion.items():
                if correctos == 2:
                    niveles[op] = 3
                elif correctos == 1:
                    niveles[op] = 2
                else:
                    niveles[op] = 1
            
            # Calcular nivel actual (máximo practicable)
            niveles["actual"] = self._calcular_nivel_inicial(niveles)
            
            mensaje = f"Empezarás en nivel {niveles['actual']}"
            perfecto = False
        
        # Actualizar diagnóstico
        diagnostico.suma_nivel1_correcto = resultados["suma"][0] if len(resultados["suma"]) > 0 else False
        diagnostico.suma_nivel2_correcto = resultados["suma"][1] if len(resultados["suma"]) > 1 else False
        diagnostico.resta_nivel1_correcto = resultados["resta"][0] if len(resultados["resta"]) > 0 else False
        diagnostico.resta_nivel2_correcto = resultados["resta"][1] if len(resultados["resta"]) > 1 else False
        diagnostico.mult_nivel1_correcto = resultados["multiplicacion"][0] if len(resultados["multiplicacion"]) > 0 else False
        diagnostico.mult_nivel2_correcto = resultados["multiplicacion"][1] if len(resultados["multiplicacion"]) > 1 else False
        diagnostico.div_nivel1_correcto = resultados["division"][0] if len(resultados["division"]) > 0 else False
        diagnostico.div_nivel2_correcto = resultados["division"][1] if len(resultados["division"]) > 1 else False
        
        diagnostico.nivel_suma_asignado = niveles["suma"]
        diagnostico.nivel_resta_asignado = niveles["resta"]
        diagnostico.nivel_mult_asignado = niveles["multiplicacion"]
        diagnostico.nivel_div_asignado = niveles["division"]
        diagnostico.nivel_actual_asignado = niveles["actual"]
        diagnostico.perfecto = perfecto
        diagnostico.estado = EstadoDiagnostico.COMPLETADO
        diagnostico.fecha_fin = datetime.utcnow()
        
        await self.adaptive_repo.update_diagnostico(diagnostico)
        
        # Crear perfil del estudiante
        perfil = await self.adaptive_repo.get_or_create_perfil(diagnostico.estudiante_id)
        perfil.nivel_suma = niveles["suma"]
        perfil.nivel_resta = niveles["resta"]
        perfil.nivel_multiplicacion = niveles["multiplicacion"]
        perfil.nivel_division = niveles["division"]
        perfil.nivel_actual = niveles["actual"]
        perfil.diagnostico_completado = True
        perfil.fecha_diagnostico = datetime.utcnow()
        
        await self.adaptive_repo.update_perfil(perfil)
        
        return DiagnosticoResultado(
            estudiante_id=diagnostico.estudiante_id,
            perfecto=perfecto,
            nivel_suma=niveles["suma"],
            nivel_resta=niveles["resta"],
            nivel_multiplicacion=niveles["multiplicacion"],
            nivel_division=niveles["division"],
            nivel_actual=niveles["actual"],
            correctos_por_operacion=correctos_por_operacion,
            velocidad_por_operacion={},  # TODO: calcular si tenemos tiempos
            mensaje=mensaje
        )
    
    def _calcular_nivel_inicial(self, niveles: Dict[str, int]) -> int:
        """Calcula nivel actual inicial basado en niveles de operaciones."""
        return max(niveles.values())
    
    # ============================================
    # Generación de Práctica Adaptativa
    # ============================================
    
    async def iniciar_sesion(self, estudiante_id: int) -> SesionStartResponse:
        """
        Inicia una sesión de práctica adaptativa.
        
        El sistema decide automáticamente qué practicar.
        """
        # Obtener perfil
        perfil = await self.adaptive_repo.get_or_create_perfil(estudiante_id)
        
        # Verificar diagnóstico completado
        if not perfil.diagnostico_completado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes completar el diagnóstico inicial primero"
            )
        
        # Recalcular nivel actual
        perfil = await self._recalcular_nivel_actual(perfil)
        
        _nombre_a_op = {
            "suma": Operacion.SUMA,
            "resta": Operacion.RESTA,
            "multiplicacion": Operacion.MULTIPLICACION,
            "division": Operacion.DIVISION,
        }

        # Aplicar ConfiguracionPractica del grupo (tiene prioridad sobre prerrequisitos adaptativos)
        config_grupo = await self.adaptive_repo.get_config_practica_estudiante(estudiante_id)
        if config_grupo and config_grupo.operaciones_permitidas:
            # El profesor decide qué operaciones se practican — ignora prerrequisitos adaptativos
            ops_disponibles = [
                _nombre_a_op[nombre]
                for nombre in config_grupo.operaciones_permitidas
                if nombre in _nombre_a_op
            ]
        else:
            # Sin config del profesor → prerrequisitos adaptativos normales
            ops_disponibles = self._get_operaciones_disponibles(perfil)

        if not ops_disponibles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay operaciones disponibles. Contacta al profesor."
            )

        # Determinar operación más débil
        op_mas_debil = self._get_operacion_mas_debil(perfil, ops_disponibles)
        
        # Determinar cantidad de problemas
        cantidad = self.PROBLEMAS_POR_NIVEL[perfil.nivel_actual]
        
        # Distribuir operaciones
        distribucion = self._distribuir_operaciones(ops_disponibles, op_mas_debil, cantidad)
        
        # Obtener ratio de dificultad
        ratio = self.RATIOS[perfil.nivel_actual]
        
        # Generar problemas
        problemas = await self._generar_problemas_sesion(perfil, distribucion, ratio)
        
        # Mezclar aleatoriamente
        random.shuffle(problemas)
        
        # Crear sesión
        problemas_ids = [p.id for p in problemas]
        sesion = await self.adaptive_repo.create_sesion(
            estudiante_id=estudiante_id,
            perfil=perfil,
            cantidad_problemas=cantidad,
            problemas_ids=problemas_ids,
            operaciones_incluidas=distribucion,
            ratio_dificultad=ratio
        )
        
        # Convertir a display
        problemas_display = [
            {
                "id": p.id,
                "operacion": p.operacion.value,
                "numero1": str(p.numero1.normalize()),
                "numero2": str(p.numero2.normalize()),
                "nivel_dificultad": p.nivel_dificultad
            }
            for p in problemas
        ]
        
        mensaje = f"Hoy practicaremos {op_mas_debil.value} (tu operación más débil)"
        
        return SesionStartResponse(
            sesion_id=sesion.id,
            cantidad_problemas=cantidad,
            operaciones_incluidas=distribucion,
            nivel_actual=perfil.nivel_actual,
            problemas=problemas_display,
            mensaje_intro=mensaje
        )
    
    def _get_operaciones_disponibles(self, perfil: PerfilEstudiante) -> List[Operacion]:
        """Retorna operaciones que el estudiante puede practicar."""
        disponibles = []
        
        # Suma y resta siempre disponibles
        disponibles.append(Operacion.SUMA)
        disponibles.append(Operacion.RESTA)
        
        # Multiplicación si cumple prereqs
        if self._cumple_prerequisitos(perfil, Operacion.MULTIPLICACION):
            disponibles.append(Operacion.MULTIPLICACION)
        
        # División si cumple prereqs
        if self._cumple_prerequisitos(perfil, Operacion.DIVISION):
            disponibles.append(Operacion.DIVISION)
        
        return disponibles
    
    def _cumple_prerequisitos(self, perfil: PerfilEstudiante, operacion: Operacion) -> bool:
        """Verifica si cumple prerequisitos para una operación."""
        prereqs = self.PREREQUISITOS.get(operacion, {})
        
        if not prereqs:
            return True  # Sin prerequisitos
        
        for op_req, nivel_min in prereqs.items():
            nivel_actual = self._get_nivel_operacion(perfil, op_req)
            if nivel_actual < nivel_min:
                return False
        
        return True
    
    def _get_nivel_operacion(self, perfil: PerfilEstudiante, operacion: Operacion) -> int:
        """Obtiene nivel de una operación específica."""
        if operacion == Operacion.SUMA:
            return perfil.nivel_suma
        elif operacion == Operacion.RESTA:
            return perfil.nivel_resta
        elif operacion == Operacion.MULTIPLICACION:
            return perfil.nivel_multiplicacion
        elif operacion == Operacion.DIVISION:
            return perfil.nivel_division
        return 1
    
    def _get_operacion_mas_debil(
        self,
        perfil: PerfilEstudiante,
        ops_disponibles: List[Operacion]
    ) -> Operacion:
        """Identifica la operación más débil entre las disponibles."""
        niveles = {
            op: self._get_nivel_operacion(perfil, op)
            for op in ops_disponibles
        }
        
        return min(niveles, key=niveles.get)
    
    def _distribuir_operaciones(
        self,
        ops_disponibles: List[Operacion],
        op_mas_debil: Operacion,
        cantidad_total: int
    ) -> Dict[str, int]:
        """Distribuye problemas entre operaciones con énfasis en la más débil."""
        distribucion = {}

        if len(ops_disponibles) == 1:
            # Solo una operación disponible (ej: profesor configuró solo división)
            distribucion[ops_disponibles[0].value] = cantidad_total

        elif len(ops_disponibles) == 2:
            distribucion[op_mas_debil.value] = int(cantidad_total * 0.7)
            otra = [op for op in ops_disponibles if op != op_mas_debil][0]
            distribucion[otra.value] = cantidad_total - distribucion[op_mas_debil.value]

        elif len(ops_disponibles) == 3:
            distribucion[op_mas_debil.value] = int(cantidad_total * 0.5)
            restantes = cantidad_total - distribucion[op_mas_debil.value]
            otras = [op for op in ops_disponibles if op != op_mas_debil]
            distribucion[otras[0].value] = int(restantes * 0.6)
            distribucion[otras[1].value] = restantes - distribucion[otras[0].value]

        else:
            # 4 operaciones
            distribucion[op_mas_debil.value] = int(cantidad_total * 0.5)
            restantes = cantidad_total - distribucion[op_mas_debil.value]
            otras = [op for op in ops_disponibles if op != op_mas_debil]
            parte = restantes // 3
            distribucion[otras[0].value] = parte
            distribucion[otras[1].value] = parte
            distribucion[otras[2].value] = restantes - (parte * 2)

        return distribucion
    
    async def _generar_problemas_sesion(
        self,
        perfil: PerfilEstudiante,
        distribucion: Dict[str, int],
        ratio: Dict[str, float]
    ) -> List:
        """Genera problemas según distribución y ratio."""
        problemas = []
        
        for op_str, cantidad in distribucion.items():
            # Convertir string a Operacion
            operacion = self._str_to_operacion(op_str)
            nivel_op = self._get_nivel_operacion(perfil, operacion)
            
            # Dividir en fáciles y desafiantes
            faciles = int(cantidad * ratio["faciles"])
            desafiantes = cantidad - faciles
            
            # Generar fáciles (nivel actual)
            for _ in range(faciles):
                prob = await self.problem_service._generate_single_problem(
                    nivel=nivel_op,
                    operaciones=[operacion],
                    decimales_max=min(nivel_op, 3),
                    rango_min=1,
                    rango_max=min(100, 50 * nivel_op)
                )
                problemas.append(prob)
            
            # Generar desafiantes (nivel + 1)
            for _ in range(desafiantes):
                nivel_desafiante = min(nivel_op + 1, 5)
                prob = await self.problem_service._generate_single_problem(
                    nivel=nivel_desafiante,
                    operaciones=[operacion],
                    decimales_max=min(nivel_desafiante, 3),
                    rango_min=1,
                    rango_max=min(100, 50 * nivel_desafiante)
                )
                problemas.append(prob)
        
        return problemas
    
    def _str_to_operacion(self, op_str: str) -> Operacion:
        """Convierte string a Operacion enum."""
        if op_str == "+":
            return Operacion.SUMA
        elif op_str == "-":
            return Operacion.RESTA
        elif op_str == "×":
            return Operacion.MULTIPLICACION
        elif op_str == "÷":
            return Operacion.DIVISION
        return Operacion.SUMA
    
    # ============================================
    # Continúa en siguiente archivo...
    # ============================================
    
    # ============================================
    # Completar Sesión y Ajuste de Niveles
    # ============================================
    
    async def completar_sesion(self, sesion_id: int) -> SesionCompleteResponse:
        """
        Completa una sesión y evalúa cambios de nivel.
        
        Este es el método más importante del sistema adaptativo.
        """
        # Obtener sesión
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        # Obtener intentos de la sesión
        intentos = await self.adaptive_repo.get_intentos_sesion(sesion_id)
        
        if not intentos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay intentos registrados en esta sesión"
            )
        
        # Calcular métricas
        correctos = sum(1 for i in intentos if i.es_correcto)
        incorrectos = len(intentos) - correctos
        precision = correctos / len(intentos) if len(intentos) > 0 else 0
        tiempo_total = sum(i.tiempo_resolucion for i in intentos)
        velocidad_promedio = tiempo_total / len(intentos) if len(intentos) > 0 else 0
        
        # Verificar si es práctica perfecta
        es_perfecta = correctos == len(intentos)
        
        # Actualizar sesión
        sesion.problemas_correctos = correctos
        sesion.problemas_incorrectos = incorrectos
        sesion.tiempo_total_segundos = tiempo_total
        sesion.velocidad_promedio = velocidad_promedio
        sesion.es_practica_perfecta = es_perfecta
        sesion.fecha_fin = datetime.utcnow()
        
        # Obtener perfil
        perfil = await self.adaptive_repo.get_perfil(sesion.estudiante_id)

        # Obtener org_id del estudiante para ML por organización
        org_id = await self.adaptive_repo.get_org_id_estudiante(sesion.estudiante_id)

        # Evaluar cambios de nivel
        cambios = await self._evaluar_cambios_nivel(perfil, sesion, intentos)

        # Actualizar perfil
        await self._actualizar_metricas_perfil(perfil, sesion, intentos, org_id=org_id)
        
        # Guardar cambios en sesión
        sesion.cambios_nivel = {
            cambio.operacion: {
                "antes": cambio.nivel_anterior,
                "despues": cambio.nivel_nuevo,
                "razon": cambio.razon
            }
            for cambio in cambios
        }
        
        await self.adaptive_repo.update_sesion(sesion)
        await self.adaptive_repo.update_perfil(perfil)
        
        # Recalcular nivel actual
        perfil = await self._recalcular_nivel_actual(perfil)
        
        # Obtener operaciones disponibles/bloqueadas
        ops_disponibles = self._get_operaciones_disponibles(perfil)
        ops_bloqueadas = self._get_operaciones_bloqueadas(perfil)
        
        # Estadísticas de grupo (opcional)
        estadisticas_grupo = None  # TODO: implementar cuando tengamos grupos
        
        # Mensaje motivacional
        mensaje = self._generar_mensaje_motivacional(es_perfecta, precision, cambios)

        # Actualizar progreso de desafíos grupales activos del estudiante
        await self._actualizar_desafios_grupales(
            estudiante_id=sesion.estudiante_id,
            problemas_correctos=correctos,
            problemas_incorrectos=incorrectos,
            es_practica_perfecta=es_perfecta,
            tiempo_total_segundos=int(tiempo_total),
            velocidad_promedio=float(velocidad_promedio),
        )

        return SesionCompleteResponse(
            sesion_id=sesion.id,
            problemas_correctos=correctos,
            problemas_incorrectos=incorrectos,
            precision=precision,
            tiempo_total_segundos=tiempo_total,
            velocidad_promedio=velocidad_promedio,
            cambios_nivel=cambios,
            nivel_actual_nuevo=perfil.nivel_actual,
            estadisticas_grupo=estadisticas_grupo,
            es_practica_perfecta=es_perfecta,
            practicas_perfectas_consecutivas=perfil.practicas_perfectas_consecutivas,
            mensaje_motivacional=mensaje,
            operaciones_disponibles=[op.value for op in ops_disponibles],
            operaciones_bloqueadas=ops_bloqueadas
        )
    
    async def _evaluar_cambios_nivel(
        self,
        perfil: PerfilEstudiante,
        sesion: SesionPractica,
        intentos: List
    ) -> List[CambioNivel]:
        """Evalúa si el estudiante debe subir/bajar de nivel."""
        cambios = []
        
        # Agrupar intentos por operación
        intentos_por_op = {}
        for intento in intentos:
            problema = await self.problem_repo.get_problem_by_id(intento.problema_id)
            if problema:
                op = problema.operacion
                if op not in intentos_por_op:
                    intentos_por_op[op] = []
                intentos_por_op[op].append(intento)
        
        # Evaluar cada operación
        for operacion, intentos_op in intentos_por_op.items():
            cambio = await self._evaluar_nivel_operacion(perfil, operacion, intentos_op)
            if cambio:
                cambios.append(cambio)
        
        # Evaluar nivel general (prácticas perfectas consecutivas)
        if sesion.es_practica_perfecta:
            perfil.practicas_perfectas_consecutivas += 1
            
            if perfil.practicas_perfectas_consecutivas >= 3:
                # Subir nivel general
                if perfil.nivel_actual < 5:
                    nivel_anterior = perfil.nivel_actual
                    perfil.nivel_actual += 1
                    perfil.practicas_perfectas_consecutivas = 0
                    
                    cambios.append(CambioNivel(
                        operacion="nivel_general",
                        nivel_anterior=nivel_anterior,
                        nivel_nuevo=perfil.nivel_actual,
                        razon="3 prácticas perfectas consecutivas"
                    ))
        else:
            perfil.practicas_perfectas_consecutivas = 0
        
        return cambios
    
    async def _evaluar_nivel_operacion(
        self,
        perfil: PerfilEstudiante,
        operacion: Operacion,
        intentos: List
    ) -> Optional[CambioNivel]:
        """Evalúa si debe cambiar el nivel de una operación específica."""
        # Obtener nivel actual de la operación
        nivel_actual = self._get_nivel_operacion(perfil, operacion)
        
        # Contar consecutivos correctos
        consecutivos = 0
        for intento in reversed(intentos):
            if intento.es_correcto:
                consecutivos += 1
            else:
                break
        
        # Calcular precisión en esta operación
        correctos = sum(1 for i in intentos if i.es_correcto)
        precision_op = correctos / len(intentos) if len(intentos) > 0 else 0
        
        # Obtener umbral (puede ser personalizado por ML)
        umbral = ml_service.ajustar_umbral_segun_perfil(perfil)
        
        # TODO: Ajustar umbral según percentil de grupo
        # umbral_final = ml_service.calcular_umbral_dinamico(perfil, percentil)
        
        # SUBIR nivel
        if consecutivos >= umbral and nivel_actual < 5:
            self._set_nivel_operacion(perfil, operacion, nivel_actual + 1)
            self._reset_consecutivos(perfil, operacion)
            
            return CambioNivel(
                operacion=operacion.value,
                nivel_anterior=nivel_actual,
                nivel_nuevo=nivel_actual + 1,
                razon=f"{consecutivos} problemas consecutivos correctos"
            )
        
        # BAJAR nivel
        if precision_op < 0.50 and nivel_actual > 1:
            self._set_nivel_operacion(perfil, operacion, nivel_actual - 1)
            self._reset_consecutivos(perfil, operacion)
            
            return CambioNivel(
                operacion=operacion.value,
                nivel_anterior=nivel_actual,
                nivel_nuevo=nivel_actual - 1,
                razon=f"Precisión baja ({precision_op:.0%})"
            )
        
        # Actualizar consecutivos
        if consecutivos > 0:
            self._incrementar_consecutivos(perfil, operacion, consecutivos)
        else:
            self._reset_consecutivos(perfil, operacion)
        
        return None
    
    def _set_nivel_operacion(self, perfil: PerfilEstudiante, operacion: Operacion, nivel: int):
        """Establece el nivel de una operación."""
        if operacion == Operacion.SUMA:
            perfil.nivel_suma = nivel
        elif operacion == Operacion.RESTA:
            perfil.nivel_resta = nivel
        elif operacion == Operacion.MULTIPLICACION:
            perfil.nivel_multiplicacion = nivel
        elif operacion == Operacion.DIVISION:
            perfil.nivel_division = nivel
    
    def _reset_consecutivos(self, perfil: PerfilEstudiante, operacion: Operacion):
        """Resetea consecutivos de una operación."""
        if operacion == Operacion.SUMA:
            perfil.consecutivas_correctas_suma = 0
        elif operacion == Operacion.RESTA:
            perfil.consecutivas_correctas_resta = 0
        elif operacion == Operacion.MULTIPLICACION:
            perfil.consecutivas_correctas_mult = 0
        elif operacion == Operacion.DIVISION:
            perfil.consecutivas_correctas_div = 0
    
    def _incrementar_consecutivos(self, perfil: PerfilEstudiante, operacion: Operacion, cantidad: int):
        """Incrementa consecutivos de una operación."""
        if operacion == Operacion.SUMA:
            perfil.consecutivas_correctas_suma = cantidad
        elif operacion == Operacion.RESTA:
            perfil.consecutivas_correctas_resta = cantidad
        elif operacion == Operacion.MULTIPLICACION:
            perfil.consecutivas_correctas_mult = cantidad
        elif operacion == Operacion.DIVISION:
            perfil.consecutivas_correctas_div = cantidad
    
    async def _actualizar_metricas_perfil(
        self,
        perfil: PerfilEstudiante,
        sesion: SesionPractica,
        intentos: List,
        org_id: Optional[int] = None,
    ):
        """Actualiza métricas globales del perfil."""
        # Incrementar total de sesiones
        perfil.total_sesiones += 1
        perfil.sesiones_en_nivel_actual += 1
        
        # Actualizar última actividad
        perfil.ultima_actividad = datetime.utcnow()
        perfil.dias_sin_practicar = 0
        
        # Calcular precisión últimos 15
        ultimos_15 = await self.adaptive_repo.get_ultimos_intentos(sesion.estudiante_id, 15)
        if ultimos_15:
            correctos = sum(1 for i in ultimos_15 if i.es_correcto)
            perfil.precision_ultimos_15 = Decimal(correctos / len(ultimos_15))
        
        # Calcular velocidad promedio
        ultimos_20 = await self.adaptive_repo.get_ultimos_intentos(sesion.estudiante_id, 20)
        if ultimos_20:
            tiempos = [i.tiempo_resolucion for i in ultimos_20]
            perfil.velocidad_promedio = Decimal(sum(tiempos) / len(tiempos))
            
            # Calcular varianza
            media = float(perfil.velocidad_promedio)
            varianza = sum((t - media) ** 2 for t in tiempos) / len(tiempos)
            perfil.varianza_velocidad = Decimal(varianza ** 0.5)
        
        # Actualizar perfil ML si tiene suficientes datos
        if perfil.total_sesiones >= 3:
            perfil_ml, confianza = ml_service.predecir_perfil(perfil, org_id)
            perfil.perfil_aprendizaje = perfil_ml
            perfil.confianza_perfil = Decimal(confianza)
            perfil.fecha_ultima_clasificacion = datetime.utcnow()
            
            # Actualizar umbral personalizado
            perfil.umbral_promocion_personalizado = ml_service.ajustar_umbral_segun_perfil(perfil)
    
    async def _recalcular_nivel_actual(self, perfil: PerfilEstudiante) -> PerfilEstudiante:
        """
        Recalcula nivel_actual basado en operaciones practicables.
        
        El nivel_actual es un PISO que casi nunca baja.
        
        REGLA ESPECIAL NIVEL 5: Para alcanzar nivel 5, TODAS las operaciones
        disponibles deben estar en nivel 4 o superior.
        """
        ops_disponibles = self._get_operaciones_disponibles(perfil)
        niveles_practicables = [self._get_nivel_operacion(perfil, op) for op in ops_disponibles]
        
        nivel_calculado = max(niveles_practicables) if niveles_practicables else 1
        
        # REGLA ESPECIAL: Para nivel 5, TODAS las operaciones deben estar en 4+
        if nivel_calculado >= 5:
            if not all(nivel >= 4 for nivel in niveles_practicables):
                nivel_calculado = 4  # Limitar a nivel 4 hasta que todas suban
        
        # El nivel_actual solo SUBE o se mantiene
        if nivel_calculado > perfil.nivel_actual:
            perfil.nivel_actual = nivel_calculado
            perfil.sesiones_en_nivel_actual = 0  # Reset contador
            perfil.fecha_ultima_promocion = datetime.utcnow()
        
        # ÚNICA EXCEPCIÓN: Si TODO cae a nivel 1, bajar a nivel 1
        if all(nivel == 1 for nivel in niveles_practicables):
            perfil.nivel_actual = 1
        
        await self.adaptive_repo.update_perfil(perfil)
        return perfil
    
    def _get_operaciones_bloqueadas(self, perfil: PerfilEstudiante) -> List[str]:
        """Retorna lista de operaciones bloqueadas."""
        bloqueadas = []
        
        # Multiplicación
        if not self._cumple_prerequisitos(perfil, Operacion.MULTIPLICACION):
            faltantes = []
            if perfil.nivel_suma < 2:
                faltantes.append("suma nivel 2")
            if perfil.nivel_resta < 2:
                faltantes.append("resta nivel 2")
            bloqueadas.append(f"Multiplicación: requiere {', '.join(faltantes)}")
        
        # División
        if not self._cumple_prerequisitos(perfil, Operacion.DIVISION):
            faltantes = []
            if perfil.nivel_suma < 2:
                faltantes.append("suma nivel 2")
            if perfil.nivel_resta < 2:
                faltantes.append("resta nivel 2")
            if perfil.nivel_multiplicacion < 2:
                faltantes.append("multiplicación nivel 2")
            bloqueadas.append(f"División: requiere {', '.join(faltantes)}")
        
        return bloqueadas
    
    def _generar_mensaje_motivacional(
        self,
        es_perfecta: bool,
        precision: float,
        cambios: List[CambioNivel]
    ) -> str:
        """Genera mensaje motivacional según resultados."""
        if cambios:
            cambios_texto = ", ".join([
                f"{c.operacion} a nivel {c.nivel_nuevo}"
                for c in cambios if c.operacion != "nivel_general"
            ])
            return f"¡Felicidades! Subiste de nivel: {cambios_texto} 🎉"
        
        if es_perfecta:
            return "¡Práctica perfecta! Excelente trabajo 🌟"
        
        if precision >= 0.9:
            return "¡Muy bien! Solo unos pocos errores ⭐"
        
        if precision >= 0.7:
            return "Buen trabajo. Sigue practicando 💪"
        
        return "No te rindas. La práctica hace al maestro 📚"

    # ============================================
    # Recuperación de Sesión Activa
    # ============================================

    async def get_sesion_activa(self, estudiante_id: int):
        """
        Devuelve la sesión EN_PROGRESO del estudiante si existe y tiene
        menos de 90 minutos de inactividad, o None si no hay ninguna.
        """
        from app.schemas.adaptive import SesionActivaResponse
        sesion = await self.adaptive_repo.get_sesion_activa(estudiante_id)
        if not sesion:
            return None
        minutos = int((datetime.utcnow() - sesion.fecha_inicio).total_seconds() / 60)
        return SesionActivaResponse(
            sesion_id=sesion.id,
            problemas_completados=sesion.progreso_actual,
            cantidad_problemas=sesion.cantidad_problemas,
            operaciones_incluidas=sesion.operaciones_incluidas or {},
            nivel_actual=sesion.nivel_actual_inicio,
            minutos_transcurridos=minutos,
            fecha_inicio=sesion.fecha_inicio,
        )

    async def retomar_sesion(self, sesion_id: int, estudiante_id: int) -> SesionStartResponse:
        """
        Retoma una sesión EN_PROGRESO devolviendo solo los problemas restantes.
        Si la sesión no pertenece al estudiante o no está EN_PROGRESO, lanza 404.
        """
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        if sesion.estado != "en_progreso":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión ya no está activa"
            )

        # Problemas pendientes = desde progreso_actual hasta el final
        todos_ids: List[int] = sesion.problemas_ids or []
        ids_restantes = todos_ids[sesion.progreso_actual:]

        problemas = []
        for pid in ids_restantes:
            p = await self.problem_repo.get_problem_by_id(pid)
            if p:
                problemas.append(p)

        problemas_display = [
            {
                "id": p.id,
                "operacion": p.operacion.value,
                "numero1": str(p.numero1.normalize()),
                "numero2": str(p.numero2.normalize()),
                "nivel_dificultad": p.nivel_dificultad,
                "cantidad_decimales": p.cantidad_decimales,
            }
            for p in problemas
        ]

        completados = sesion.progreso_actual
        total = sesion.cantidad_problemas
        return SesionStartResponse(
            sesion_id=sesion.id,
            cantidad_problemas=total,
            operaciones_incluidas=sesion.operaciones_incluidas or {},
            nivel_actual=sesion.nivel_actual_inicio,
            problemas=problemas_display,
            mensaje_intro=(
                f"Retomando práctica… ya completaste {completados} de {total} problemas. ¡Sigue!"
            ),
        )

    async def descartar_sesion(self, sesion_id: int, estudiante_id: int) -> None:
        """
        Marca una sesión EN_PROGRESO como ABANDONADA.
        Solo el dueño puede descartarla.
        """
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        if sesion.estado != "en_progreso":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesión ya no está activa"
            )
        sesion.estado = "abandonada"
        sesion.fecha_fin = datetime.utcnow()
        await self.adaptive_repo.update_sesion(sesion)

    # ============================================
    # Redención
    # ============================================

    async def get_disponibilidad_redencion(self, estudiante_id: int) -> dict:
        """Verifica si el estudiante tiene problemas disponibles para redimir."""
        ids_fallados = await self.adaptive_repo.get_problemas_fallados(estudiante_id)
        return {
            "disponible": len(ids_fallados) > 0,
            "total_problemas_fallados": len(ids_fallados)
        }

    async def iniciar_sesion_redencion(self, estudiante_id: int) -> SesionStartResponse:
        """
        Inicia una sesión de redención con 5 problemas que el estudiante falló.

        Los problemas son exactamente los que el estudiante intentó pero nunca
        resolvió correctamente, elegidos al azar entre todos los disponibles.
        """
        perfil = await self.adaptive_repo.get_or_create_perfil(estudiante_id)

        if not perfil.diagnostico_completado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes completar el diagnóstico inicial primero"
            )

        # Obtener hasta 50 problemas fallados y elegir 5 al azar
        ids_fallados = await self.adaptive_repo.get_problemas_fallados(estudiante_id, limit=50)

        if not ids_fallados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes problemas pendientes de redención. ¡Buen trabajo!"
            )

        cantidad = min(5, len(ids_fallados))
        ids_elegidos = random.sample(ids_fallados, cantidad)

        # Cargar los objetos Problema
        problemas = []
        for pid in ids_elegidos:
            p = await self.problem_repo.get_problem_by_id(pid)
            if p:
                problemas.append(p)

        random.shuffle(problemas)

        # Calcular distribución por operación (para el JSON de la sesión)
        distribucion: Dict[str, int] = {}
        for p in problemas:
            op_str = p.operacion.value  # "+", "-", "×", "÷"
            distribucion[op_str] = distribucion.get(op_str, 0) + 1

        # Crear sesión reutilizando el repositorio existente
        sesion = await self.adaptive_repo.create_sesion(
            estudiante_id=estudiante_id,
            perfil=perfil,
            cantidad_problemas=len(problemas),
            problemas_ids=[p.id for p in problemas],
            operaciones_incluidas=distribucion,
            ratio_dificultad={"redencion": 1.0}
        )

        problemas_display = [
            {
                "id": p.id,
                "operacion": p.operacion.value,
                "numero1": str(p.numero1.normalize()),
                "numero2": str(p.numero2.normalize()),
                "nivel_dificultad": p.nivel_dificultad,
                "cantidad_decimales": p.cantidad_decimales,
            }
            for p in problemas
        ]

        return SesionStartResponse(
            sesion_id=sesion.id,
            cantidad_problemas=len(problemas),
            operaciones_incluidas=distribucion,
            nivel_actual=perfil.nivel_actual,
            problemas=problemas_display,
            mensaje_intro=(
                "¡Es hora de demostrar que aprendiste! "
                "Estos son los problemas que antes no pudiste resolver. 💪"
            )
        )

    # ============================================
    # Obtener Perfil y Estadísticas
    # ============================================
    
    async def get_perfil(self, estudiante_id: int) -> PerfilResponse:
        """Obtiene perfil completo del estudiante."""
        perfil = await self.adaptive_repo.get_or_create_perfil(estudiante_id)
        
        ops_disponibles = self._get_operaciones_disponibles(perfil)
        ops_bloqueadas_texto = self._get_operaciones_bloqueadas(perfil)
        
        # Prerequisitos faltantes
        prereqs_faltantes = {}
        if Operacion.MULTIPLICACION not in ops_disponibles:
            prereqs_faltantes["multiplicacion"] = ["suma>=2", "resta>=2"]
        if Operacion.DIVISION not in ops_disponibles:
            prereqs_faltantes["division"] = ["suma>=2", "resta>=2", "mult>=2"]
        
        # Consecutivas por operación
        consecutivas = {
            "suma": perfil.consecutivas_correctas_suma,
            "resta": perfil.consecutivas_correctas_resta,
            "multiplicacion": perfil.consecutivas_correctas_mult,
            "division": perfil.consecutivas_correctas_div
        }
        
        # Umbral de promoción
        umbral = perfil.umbral_promocion_personalizado or 10
        
        # Obtener grupo y profesor asignado
        grupo_info = await self.adaptive_repo.get_grupo_info(estudiante_id)

        return PerfilResponse(
            estudiante_id=estudiante_id,
            nivel_actual=perfil.nivel_actual,
            nivel_suma=perfil.nivel_suma,
            nivel_resta=perfil.nivel_resta,
            nivel_multiplicacion=perfil.nivel_multiplicacion,
            nivel_division=perfil.nivel_division,
            operaciones_disponibles=[op.value for op in ops_disponibles],
            operaciones_bloqueadas=ops_bloqueadas_texto,
            prerequisitos_faltantes=prereqs_faltantes,
            precision_ultimos_15=perfil.precision_ultimos_15 or Decimal("0"),
            velocidad_promedio=perfil.velocidad_promedio or Decimal("0"),
            varianza_velocidad=perfil.varianza_velocidad or Decimal("0"),
            total_sesiones=perfil.total_sesiones,
            sesiones_en_nivel_actual=perfil.sesiones_en_nivel_actual,
            practicas_perfectas_consecutivas=perfil.practicas_perfectas_consecutivas,
            perfil_aprendizaje=perfil.perfil_aprendizaje.value,
            confianza_perfil=perfil.confianza_perfil,
            consecutivas_por_operacion=consecutivas,
            umbral_promocion=umbral,
            ultima_actividad=perfil.ultima_actividad,
            dias_sin_practicar=perfil.dias_sin_practicar,
            diagnostico_completado=perfil.diagnostico_completado,
            grupo_nombre=grupo_info["grupo_nombre"] if grupo_info else None,
            profesor_nombre=grupo_info["profesor_nombre"] if grupo_info else None,
        )

    # ============================================
    # Desafíos Grupales
    # ============================================

    async def _actualizar_desafios_grupales(
        self,
        estudiante_id: int,
        problemas_correctos: int,
        problemas_incorrectos: int,
        es_practica_perfecta: bool,
        tiempo_total_segundos: int,
        velocidad_promedio: float,
    ) -> None:
        """Actualiza el progreso de desafíos grupales activos y otorga monedas si se completan.

        Tipos de desafío soportados:
        - problemas_resueltos    → +N correctos por sesión
        - sesiones_completadas   → +1 por sesión
        - practicas_sin_errores  → +1 si incorrectos <= parametro_adicional
        - problemas_rapidos      → +N correctos si velocidad <= parametro_adicional seg/problema
        - practicas_rapidas      → +1 si tiempo_total <= parametro_adicional * 60 seg

        Cuando un grupo completa un desafío por primera vez y hay recompensa_puntos,
        se otorgan monedas (puntos de tienda) a todos los estudiantes activos del grupo
        usando GamificationRepository para registrar la transacción correctamente.
        """
        from sqlalchemy import select, and_, func
        from app.models.group import EstudianteGrupo
        from app.models.challenge import DesafioGrupal, GrupoDesafio
        from app.repositories.gamification_repository import GamificationRepository

        db = self.adaptive_repo.db

        # Grupos activos a los que pertenece el estudiante
        result = await db.execute(
            select(EstudianteGrupo.grupo_id)
            .where(and_(
                EstudianteGrupo.estudiante_id == estudiante_id,
                EstudianteGrupo.activo == True,
            ))
        )
        grupos_ids = [row[0] for row in result.all()]

        if not grupos_ids:
            return

        # Desafíos activos asignados a esos grupos
        result = await db.execute(
            select(GrupoDesafio, DesafioGrupal)
            .join(DesafioGrupal, GrupoDesafio.desafio_id == DesafioGrupal.id)
            .where(and_(
                GrupoDesafio.grupo_id.in_(grupos_ids),
                DesafioGrupal.completado == False,
                DesafioGrupal.eliminado == False,
            ))
        )
        relaciones = result.all()

        if not relaciones:
            return

        for gd, desafio in relaciones:
            # ── Calcular incremento según tipo ────────────────────────────────
            incremento = 0
            max_param = desafio.parametro_adicional or 0

            if desafio.tipo == "problemas_resueltos":
                incremento = problemas_correctos

            elif desafio.tipo == "sesiones_completadas":
                incremento = 1

            elif desafio.tipo == "practicas_sin_errores":
                # Cuenta solo si esta sesión tuvo <= Y errores
                if problemas_incorrectos <= max_param:
                    incremento = 1

            elif desafio.tipo == "problemas_rapidos":
                # Cuenta los correctos solo si la velocidad fue <= Y seg/problema
                if max_param > 0 and velocidad_promedio <= max_param:
                    incremento = problemas_correctos

            elif desafio.tipo == "practicas_rapidas":
                # Cuenta la sesión solo si duró <= Y minutos
                if max_param > 0 and tiempo_total_segundos <= max_param * 60:
                    incremento = 1

            if incremento > 0:
                gd.progreso_actual = min(
                    gd.progreso_actual + incremento,
                    desafio.objetivo_cantidad,
                )

            # ── Detectar primera compleción y otorgar monedas de tienda ─────────
            grupo_completo = gd.progreso_actual >= desafio.objetivo_cantidad
            if grupo_completo and not gd.puntos_otorgados:
                desafio.completado = True
                gd.puntos_otorgados = True

                # Otorgar monedas solo a estudiantes que participaron activamente
                # (completaron al menos 1 sesión dentro de la ventana del desafío)
                if desafio.recompensa_puntos and desafio.recompensa_puntos > 0:
                    from app.models.adaptive import SesionPractica, EstadoSesion

                    # 1. Todos los miembros activos del grupo
                    est_result = await db.execute(
                        select(EstudianteGrupo.estudiante_id)
                        .where(and_(
                            EstudianteGrupo.grupo_id == gd.grupo_id,
                            EstudianteGrupo.activo == True,
                        ))
                    )
                    miembros_ids = [row[0] for row in est_result.all()]

                    # 2. Filtrar solo los que completaron ≥ MIN sesiones en la ventana
                    #    (mismo umbral que el router de estudiante)
                    MIN_SESIONES = 3
                    cond_ventana = [
                        SesionPractica.estudiante_id.in_(miembros_ids),
                        SesionPractica.estado == EstadoSesion.COMPLETADA,
                        SesionPractica.fecha_fin >= desafio.fecha_creacion,
                    ]
                    if desafio.fecha_limite:
                        cond_ventana.append(SesionPractica.fecha_fin <= desafio.fecha_limite)

                    part_result = await db.execute(
                        select(
                            SesionPractica.estudiante_id,
                            func.count(SesionPractica.id).label("cnt"),
                        )
                        .where(and_(*cond_ventana))
                        .group_by(SesionPractica.estudiante_id)
                        .having(func.count(SesionPractica.id) >= MIN_SESIONES)
                    )
                    participantes_ids = [row[0] for row in part_result.all()]

                    # 3. Solo los participantes reciben la recompensa
                    gamif_repo = GamificationRepository(db)
                    for part_id in participantes_ids:
                        await gamif_repo.agregar_puntos(
                            estudiante_id=part_id,
                            cantidad=desafio.recompensa_puntos,
                            concepto=f"Desafío grupal completado: {desafio.nombre}",
                        )

        await db.flush()
