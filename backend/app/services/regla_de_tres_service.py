"""
Service de generación, evaluación y práctica adaptativa de Regla de Tres.

Módulo paralelo e independiente al de las 4 operaciones base: nivel único
(1-5), sin prerequisitos cruzados, sin medallas — solo puntos básicos.
"""

import random
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status

from app.repositories.regla_de_tres_repository import ReglaDeTresRepository
from app.repositories.gamification_repository import GamificationRepository
from app.models.regla_de_tres import (
    TipoProporcion,
    ProblemaReglaTres,
    SesionPracticaReglaTres,
    IntentoReglaTres,
    EstadoSesion,
)
from app.schemas.regla_de_tres import (
    ProblemaReglaTresDisplay,
    SesionReglaTresStartResponse,
    SubmitRespuestaR3Response,
    ResumenSesionR3,
    EstudianteNotaR3,
    NotasReglaTresResponse,
)


class ReglaDeTresService:
    """Service para generación, práctica y evaluación de Regla de Tres."""

    CANTIDAD_PROBLEMAS_DEFAULT = 10
    PROMOCION_CONSECUTIVAS = 5  # 5 correctas seguidas -> sube nivel (tope 5)
    PUNTOS_POR_CORRECTA = 10
    TOLERANCIA = Decimal("0.01")

    # Configuración por nivel de dificultad (1-5)
    NIVEL_CONFIG = {
        1: {"tipos": [TipoProporcion.DIRECTA], "rango_base": (2, 10), "rango_ratio": (2, 5), "decimales": 0},
        2: {"tipos": [TipoProporcion.DIRECTA], "rango_base": (2, 15), "rango_ratio": (2, 9), "decimales": 0},
        3: {"tipos": [TipoProporcion.DIRECTA, TipoProporcion.INVERSA], "rango_base": (2, 15), "rango_ratio": (2, 8), "decimales": 0},
        4: {"tipos": [TipoProporcion.DIRECTA, TipoProporcion.INVERSA], "rango_base": (2, 20), "rango_ratio": (2, 9), "decimales": 1},
        5: {"tipos": [TipoProporcion.DIRECTA, TipoProporcion.INVERSA], "rango_base": (2, 25), "rango_ratio": (2, 9), "decimales": 2},
    }

    def __init__(self, regla_repo: ReglaDeTresRepository, gamification_repo: GamificationRepository):
        self.regla_repo = regla_repo
        self.gamification_repo = gamification_repo

    # ============================================
    # Generación de Problemas
    # ============================================

    def _random_decimal(self, min_val: int, max_val: int, decimales: int) -> Decimal:
        """Genera un Decimal 'bonito' con exactamente `decimales` dígitos."""
        entero = random.randint(min_val, max_val)
        if decimales == 0:
            return Decimal(entero)
        frac = random.randint(0, 10 ** decimales - 1)
        return Decimal(f"{entero}.{frac:0{decimales}d}")

    def _count_decimals(self, numero: Decimal) -> int:
        numero_str = str(numero)
        if '.' in numero_str:
            return len(numero_str.split('.')[1].rstrip('0'))
        return 0

    def _generar_datos_problema(self, nivel: int) -> dict:
        """
        Genera a, b, c, x "hacia atrás" (se fija la razón/resultado primero
        y se derivan los operandos) para garantizar decimales exactos, igual
        estrategia que usa problem_service para división.
        """
        config = self.NIVEL_CONFIG[nivel]
        tipo = random.choice(config["tipos"])
        decimales = config["decimales"]
        base_min, base_max = config["rango_base"]
        ratio_min, ratio_max = config["rango_ratio"]

        if tipo == TipoProporcion.DIRECTA:
            r = self._random_decimal(ratio_min, ratio_max, decimales)
            a = Decimal(random.randint(base_min, base_max))
            c = Decimal(random.randint(base_min, base_max))
            b = a * r
            x = c * r
        else:  # INVERSA: a*b = c*x, con c = a*k (k entero) => b = k*x
            a = Decimal(random.randint(base_min, base_max))
            k = random.randint(ratio_min, ratio_max)
            c = a * k
            x = self._random_decimal(base_min, base_max, decimales)
            b = Decimal(k) * x

        cantidad_decimales = max(
            self._count_decimals(a), self._count_decimals(b),
            self._count_decimals(c), self._count_decimals(x),
        )
        return {"tipo": tipo, "a": a, "b": b, "c": c, "x": x, "decimales": cantidad_decimales}

    async def _generar_o_reusar_problema(self, nivel: int) -> ProblemaReglaTres:
        datos = self._generar_datos_problema(nivel)
        signature = f"r3_{datos['tipo'].value}_{datos['a']}_{datos['b']}_{datos['c']}"

        existente = await self.regla_repo.get_problema_by_signature(signature)
        if existente:
            return existente

        problema = ProblemaReglaTres(
            tipo=datos["tipo"],
            numero1=datos["a"],
            numero2=datos["b"],
            numero3=datos["c"],
            resultado=datos["x"],
            nivel_dificultad=nivel,
            cantidad_decimales=datos["decimales"],
            signature=signature,
        )
        return await self.regla_repo.create_problema(problema)

    def _to_display(self, problema: ProblemaReglaTres) -> ProblemaReglaTresDisplay:
        return ProblemaReglaTresDisplay(
            id=problema.id,
            tipo=problema.tipo.value,
            numero1=problema.numero1,
            numero2=problema.numero2,
            numero3=problema.numero3,
            nivel_dificultad=problema.nivel_dificultad,
        )

    # ============================================
    # Práctica
    # ============================================

    async def iniciar_practica(
        self, estudiante_id: int, cantidad: int = CANTIDAD_PROBLEMAS_DEFAULT
    ) -> SesionReglaTresStartResponse:
        perfil = await self.regla_repo.get_or_create_perfil(estudiante_id)
        nivel = perfil.nivel_actual

        problemas = [await self._generar_o_reusar_problema(nivel) for _ in range(cantidad)]

        sesion = SesionPracticaReglaTres(
            estudiante_id=estudiante_id,
            estado=EstadoSesion.INICIADA,
            nivel_al_iniciar=nivel,
            cantidad_problemas=cantidad,
            problemas_ids=[p.id for p in problemas],
            progreso_actual=0,
        )
        sesion = await self.regla_repo.create_sesion(sesion)

        return SesionReglaTresStartResponse(
            sesion_id=sesion.id,
            nivel_al_iniciar=nivel,
            cantidad_problemas=cantidad,
            progreso_actual=0,
            problema_actual=self._to_display(problemas[0]),
        )

    async def enviar_respuesta(
        self, sesion_id: int, estudiante_id: int, problema_id: int, respuesta: Decimal
    ) -> SubmitRespuestaR3Response:
        sesion = await self.regla_repo.get_sesion(sesion_id)
        if not sesion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta sesión no te pertenece")
        if sesion.estado == EstadoSesion.COMPLETADA:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La sesión ya fue completada")

        problemas_ids: List[int] = sesion.problemas_ids
        if sesion.progreso_actual >= len(problemas_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La sesión ya no tiene problemas pendientes")
        if problema_id != problemas_ids[sesion.progreso_actual]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ese no es el problema actual de la sesión")

        problema = await self.regla_repo.get_problema(problema_id)
        if not problema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problema no encontrado")

        es_correcto = abs(Decimal(respuesta) - problema.resultado) <= self.TOLERANCIA

        intento = IntentoReglaTres(
            sesion_id=sesion.id, problema_id=problema.id,
            respuesta_estudiante=respuesta, es_correcto=es_correcto,
        )
        await self.regla_repo.create_intento(intento)

        if es_correcto:
            sesion.problemas_correctos += 1
        else:
            sesion.problemas_incorrectos += 1
        sesion.progreso_actual += 1

        perfil = await self.regla_repo.get_or_create_perfil(estudiante_id)
        perfil.total_practicados += 1
        perfil.fecha_ultima_practica = datetime.utcnow()
        if es_correcto:
            perfil.consecutivas_correctas += 1
            if perfil.consecutivas_correctas >= self.PROMOCION_CONSECUTIVAS and perfil.nivel_actual < 5:
                perfil.nivel_actual += 1
                perfil.consecutivas_correctas = 0
        else:
            perfil.consecutivas_correctas = 0

        sesion_completada = sesion.progreso_actual >= len(problemas_ids)
        resumen: Optional[ResumenSesionR3] = None

        if sesion_completada:
            sesion.estado = EstadoSesion.COMPLETADA
            sesion.fecha_fin = datetime.utcnow()
            puntos = sesion.problemas_correctos * self.PUNTOS_POR_CORRECTA
            sesion.puntos_ganados = puntos

            # Puntos directos, sin pasar por verificar_y_otorgar_medallas
            await self.gamification_repo.agregar_puntos(
                estudiante_id=estudiante_id,
                cantidad=puntos,
                concepto="Práctica de Regla de Tres",
                sesion_id=None,
            )

            total = sesion.problemas_correctos + sesion.problemas_incorrectos
            resumen = ResumenSesionR3(
                correctos=sesion.problemas_correctos,
                total=total,
                nota_pct=round(sesion.problemas_correctos / total * 100, 1) if total else 0.0,
                nivel_actual=perfil.nivel_actual,
                puntos_ganados=puntos,
            )

        await self.regla_repo.update_sesion(sesion)
        await self.regla_repo.update_perfil(perfil)

        siguiente_problema = None
        if not sesion_completada:
            siguiente = await self.regla_repo.get_problema(problemas_ids[sesion.progreso_actual])
            siguiente_problema = self._to_display(siguiente)

        return SubmitRespuestaR3Response(
            es_correcto=es_correcto,
            resultado_correcto=problema.resultado,
            sesion_completada=sesion_completada,
            progreso_actual=sesion.progreso_actual,
            cantidad_problemas=len(problemas_ids),
            siguiente_problema=siguiente_problema,
            resumen=resumen,
        )

    # ============================================
    # Notas (profesor / admin)
    # ============================================

    async def obtener_notas(self, estudiante_ids: List[int]) -> NotasReglaTresResponse:
        filas = await self.regla_repo.get_notas_por_estudiantes(estudiante_ids)
        return NotasReglaTresResponse(estudiantes=[EstudianteNotaR3(**f) for f in filas])
