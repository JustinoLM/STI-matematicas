"""
Service de estadísticas de grupo para el panel analítico del profesor.

Recopila en lotes (sin N+1) datos de PerfilEstudiante, SesionPractica,
AlertaEstudiante y aplica predicciones del MLService para construir
una vista completa del grupo.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date

from app.models.adaptive import (
    PerfilEstudiante,
    SesionPractica,
    EstadoSesion,
    AlertaEstudiante,
    PerfilAprendizaje,
)
from app.models.user import Estudiante
from app.models.group import EstudianteGrupo, Grupo
from app.services.ml_service import ml_service
from app.services.llm_service import LLMService
from app.schemas.stats import (
    GrupoStatsResponse,
    EstudianteStatsItem,
    DistribucionPerfiles,
    AlertaResumen,
    NivelesOperacion,
    ActividadDia,
    PrecisionSemana,
    AnalisisIAResponse,
)


class StatsService:
    """Servicio que recopila y agrega estadísticas de un grupo."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # Endpoint principal
    # ──────────────────────────────────────────────────────────────────────────

    async def get_grupo_stats(
        self, grupo_id: int, profesor_id: int
    ) -> Optional[GrupoStatsResponse]:
        """
        Construye el objeto GrupoStatsResponse para un grupo del profesor.

        Retorna None si el grupo no existe o no pertenece al profesor.
        """
        # 1. Verificar propiedad del grupo
        grupo_res = await self.db.execute(
            select(Grupo).where(
                and_(Grupo.id == grupo_id, Grupo.profesor_id == profesor_id)
            )
        )
        grupo = grupo_res.scalar_one_or_none()
        if not grupo:
            return None

        # 2. Estudiantes activos del grupo con sus perfiles (JOIN único)
        rows_res = await self.db.execute(
            select(Estudiante, PerfilEstudiante)
            .join(EstudianteGrupo, EstudianteGrupo.estudiante_id == Estudiante.id)
            .outerjoin(
                PerfilEstudiante,
                PerfilEstudiante.estudiante_id == Estudiante.id,
            )
            .where(
                and_(
                    EstudianteGrupo.grupo_id == grupo_id,
                    EstudianteGrupo.activo == True,
                )
            )
        )
        rows = rows_res.all()

        if not rows:
            return GrupoStatsResponse(
                grupo_id=grupo_id,
                grupo_nombre=grupo.nombre,
                total_estudiantes=0,
                distribucion_perfiles=DistribucionPerfiles(),
                resumen_alertas=AlertaResumen(),
                niveles_por_operacion=NivelesOperacion(),
                precision_semanal=[],
                actividad_grupal=[],
                estudiantes=[],
            )

        estudiante_ids = [e.id for e, _ in rows]
        ahora = datetime.utcnow()

        # 3. Alertas activas por estudiante (lote único)
        alertas_res = await self.db.execute(
            select(AlertaEstudiante.estudiante_id, AlertaEstudiante.tipo).where(
                and_(
                    AlertaEstudiante.estudiante_id.in_(estudiante_ids),
                    AlertaEstudiante.activa == True,
                )
            )
        )
        alertas_por_est: dict[int, list[str]] = {}
        for eid, tipo in alertas_res.all():
            tipo_str = tipo.value if hasattr(tipo, "value") else str(tipo)
            alertas_por_est.setdefault(eid, []).append(tipo_str)

        # 4. Sesiones por estudiante por día (últimas 2 semanas, lote único)
        # Usamos cast(fecha_fin, Date) en lugar de func.date() para que SQLAlchemy
        # genere CAST(...) consistente tanto en el SELECT como en el GROUP BY.
        hace_14 = ahora - timedelta(days=14)
        dia_col = cast(SesionPractica.fecha_fin, Date)
        sesiones_res = await self.db.execute(
            select(
                SesionPractica.estudiante_id,
                dia_col.label("dia"),
                func.count(SesionPractica.id).label("n"),
            )
            .where(
                and_(
                    SesionPractica.estudiante_id.in_(estudiante_ids),
                    SesionPractica.estado == EstadoSesion.COMPLETADA,
                    SesionPractica.fecha_fin >= hace_14,
                )
            )
            .group_by(
                SesionPractica.estudiante_id,
                dia_col,
            )
        )
        sesiones_por_est: dict[int, dict[str, int]] = {}
        sesiones_grupo_dia: dict[str, int] = {}
        for eid, dia, n in sesiones_res.all():
            dia_str = str(dia)
            sesiones_por_est.setdefault(eid, {})[dia_str] = n
            sesiones_grupo_dia[dia_str] = sesiones_grupo_dia.get(dia_str, 0) + n

        # 5. Sesiones de la última semana por estudiante (para columna de tabla)
        hace_7 = ahora - timedelta(days=7)
        semana_res = await self.db.execute(
            select(
                SesionPractica.estudiante_id,
                func.count(SesionPractica.id).label("n"),
            )
            .where(
                and_(
                    SesionPractica.estudiante_id.in_(estudiante_ids),
                    SesionPractica.estado == EstadoSesion.COMPLETADA,
                    SesionPractica.fecha_fin >= hace_7,
                )
            )
            .group_by(SesionPractica.estudiante_id)
        )
        sesiones_semana: dict[int, int] = {eid: n for eid, n in semana_res.all()}

        # 6. Precisión semanal del grupo (últimas 4 semanas)
        # Misma variable en SELECT, GROUP BY y ORDER BY → SQLAlchemy genera
        # la misma expresión SQL en los tres lugares, sin referencias sueltas a fecha_fin.
        hace_28 = ahora - timedelta(days=28)
        semana_col = func.date_trunc("week", SesionPractica.fecha_fin)
        weekly_res = await self.db.execute(
            select(
                semana_col.label("semana"),
                func.sum(
                    func.coalesce(SesionPractica.problemas_correctos, 0)
                ).label("correctos"),
                func.sum(
                    func.coalesce(SesionPractica.problemas_correctos, 0)
                    + func.coalesce(SesionPractica.problemas_incorrectos, 0)
                ).label("total"),
            )
            .where(
                and_(
                    SesionPractica.estudiante_id.in_(estudiante_ids),
                    SesionPractica.estado == EstadoSesion.COMPLETADA,
                    SesionPractica.fecha_fin >= hace_28,
                )
            )
            .group_by(semana_col)
            .order_by(semana_col)
        )
        precision_semanal: list[PrecisionSemana] = []
        for semana_ts, correctos, total in weekly_res.all():
            if total and int(total) > 0:
                pct = round((int(correctos) / int(total)) * 100, 1)
                semana_str = semana_ts.strftime("%Y-W%V") if semana_ts else "?"
                precision_semanal.append(PrecisionSemana(semana=semana_str, precision=pct))

        # 7. Construir datos por estudiante y agregados de grupo
        dist_perfiles = DistribucionPerfiles()
        resumen_alertas = AlertaResumen()
        niveles_op = NivelesOperacion()
        estudiantes_stats: list[EstudianteStatsItem] = []

        for estudiante, perfil in rows:
            # ── Actividad individual (14 días) ────────────────────────────────
            actividad_14: list[ActividadDia] = []
            for i in range(14):
                dia = (ahora - timedelta(days=13 - i)).date()
                dia_str = str(dia)
                n = sesiones_por_est.get(estudiante.id, {}).get(dia_str, 0)
                actividad_14.append(ActividadDia(fecha=dia_str, sesiones=n))

            # ── Probabilidad de avance (ML) ───────────────────────────────────
            prob = 0.0
            if perfil and ml_service._tiene_datos_suficientes(perfil):
                dias_desde_promo = 0
                if perfil.fecha_ultima_promocion:
                    dias_desde_promo = (ahora - perfil.fecha_ultima_promocion).days
                prob = ml_service.predecir_exito_nivel_siguiente(perfil, dias_desde_promo)

            # ── Distribución de perfiles ──────────────────────────────────────
            perfil_ap = (
                perfil.perfil_aprendizaje
                if perfil and perfil.perfil_aprendizaje
                else PerfilAprendizaje.NO_CLASIFICADO
            )
            if perfil_ap == PerfilAprendizaje.RAPIDO_PRECISO:
                dist_perfiles.rapido_preciso += 1
            elif perfil_ap == PerfilAprendizaje.CUIDADOSO_METODICO:
                dist_perfiles.cuidadoso_metodico += 1
            elif perfil_ap == PerfilAprendizaje.IMPULSIVO:
                dist_perfiles.impulsivo += 1
            elif perfil_ap == PerfilAprendizaje.EN_DESARROLLO:
                dist_perfiles.en_desarrollo += 1
            else:
                dist_perfiles.no_clasificado += 1

            # ── Alertas ───────────────────────────────────────────────────────
            student_alerts = alertas_por_est.get(estudiante.id, [])
            for alerta in student_alerts:
                if alerta == "posible_trampa":
                    resumen_alertas.posible_trampa += 1
                elif alerta == "rezagado":
                    resumen_alertas.rezagado += 1
                elif alerta == "inactivo":
                    resumen_alertas.inactivo += 1
                elif alerta == "promocion_rapida":
                    resumen_alertas.promocion_rapida += 1
                elif alerta == "dificultad_persistente":
                    resumen_alertas.dificultad_persistente += 1
                elif alerta == "excelencia":
                    resumen_alertas.excelencia += 1

            # ── Histogramas de niveles ────────────────────────────────────────
            if perfil:
                for nivel_val, lista in [
                    (perfil.nivel_suma, niveles_op.suma),
                    (perfil.nivel_resta, niveles_op.resta),
                    (perfil.nivel_multiplicacion, niveles_op.multiplicacion),
                    (perfil.nivel_division, niveles_op.division),
                ]:
                    idx = min(max(int(nivel_val or 1), 1), 5) - 1
                    lista[idx] += 1

            perfil_str = (
                perfil_ap.value if hasattr(perfil_ap, "value") else str(perfil_ap)
            )

            estudiantes_stats.append(
                EstudianteStatsItem(
                    id=estudiante.id,
                    nombre=estudiante.nombre_completo,
                    codigo=estudiante.codigo_estudiante,
                    nivel_suma=int(perfil.nivel_suma) if perfil else 1,
                    nivel_resta=int(perfil.nivel_resta) if perfil else 1,
                    nivel_multiplicacion=int(perfil.nivel_multiplicacion) if perfil else 1,
                    nivel_division=int(perfil.nivel_division) if perfil else 1,
                    nivel_actual=int(perfil.nivel_actual) if perfil else 1,
                    precision=round(float(perfil.precision_ultimos_15 or 0) * 100, 1)
                    if perfil
                    else 0.0,
                    velocidad_promedio=round(float(perfil.velocidad_promedio or 0), 1)
                    if perfil
                    else 0.0,
                    total_sesiones=int(perfil.total_sesiones) if perfil else 0,
                    sesiones_esta_semana=sesiones_semana.get(estudiante.id, 0),
                    dias_sin_practicar=int(perfil.dias_sin_practicar) if perfil else 0,
                    perfil_aprendizaje=perfil_str,
                    confianza_perfil=round(float(perfil.confianza_perfil or 0) * 100, 1)
                    if perfil
                    else 0.0,
                    probabilidad_avance=round(prob * 100, 1),
                    alertas=student_alerts,
                    actividad_14_dias=actividad_14,
                )
            )

        # 8. Actividad grupal (últimas 2 semanas)
        actividad_grupal: list[ActividadDia] = []
        for i in range(14):
            dia = (ahora - timedelta(days=13 - i)).date()
            dia_str = str(dia)
            actividad_grupal.append(
                ActividadDia(fecha=dia_str, sesiones=sesiones_grupo_dia.get(dia_str, 0))
            )

        return GrupoStatsResponse(
            grupo_id=grupo_id,
            grupo_nombre=grupo.nombre,
            total_estudiantes=len(rows),
            distribucion_perfiles=dist_perfiles,
            resumen_alertas=resumen_alertas,
            niveles_por_operacion=niveles_op,
            precision_semanal=precision_semanal,
            actividad_grupal=actividad_grupal,
            estudiantes=sorted(estudiantes_stats, key=lambda x: x.nombre),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Análisis IA bajo demanda
    # ──────────────────────────────────────────────────────────────────────────

    async def analizar_con_ia(
        self, grupo_id: int, profesor_id: int, llm: LLMService
    ) -> AnalisisIAResponse:
        """
        Genera análisis pedagógico del grupo usando DeepSeek V3 (bajo demanda, sin caché).
        """
        stats = await self.get_grupo_stats(grupo_id, profesor_id)
        if stats is None:
            return AnalisisIAResponse(
                texto="Grupo no encontrado.", generado_por_llm=False
            )

        prompt = self._construir_prompt_analisis(stats)
        try:
            texto = await llm.generate(
                prompt=prompt,
                use_reasoning=False,  # V3 es suficiente y más rápido
                max_tokens=450,
            )
            return AnalisisIAResponse(texto=texto.strip(), generado_por_llm=True)
        except Exception:
            return AnalisisIAResponse(
                texto="No se pudo generar el análisis en este momento. Verifica la conexión con DeepSeek.",
                generado_por_llm=False,
            )

    @staticmethod
    def _construir_prompt_analisis(stats: GrupoStatsResponse) -> str:
        """Construye el prompt enriquecido con todos los datos ML del grupo."""
        dist = stats.distribucion_perfiles
        alertas = stats.resumen_alertas
        ests = stats.estudiantes
        n = max(stats.total_estudiantes, 1)

        # Promedios de nivel por operación
        avg_suma = sum(e.nivel_suma for e in ests) / n
        avg_resta = sum(e.nivel_resta for e in ests) / n
        avg_mult = sum(e.nivel_multiplicacion for e in ests) / n
        avg_div = sum(e.nivel_division for e in ests) / n
        avg_prec = sum(e.precision for e in ests) / n

        # Estudiantes que necesitan atención
        necesitan = [
            e
            for e in ests
            if e.probabilidad_avance < 40 or e.dias_sin_practicar >= 5
        ]
        destacados = [e for e in ests if e.probabilidad_avance >= 70]

        atencion_str = (
            "\n".join(
                f"  - {e.nombre}: {e.probabilidad_avance:.0f}% avance, {e.dias_sin_practicar} días inactivo"
                for e in necesitan[:5]
            )
            or "  Ninguno"
        )
        destacados_str = (
            "\n".join(
                f"  - {e.nombre}: {e.probabilidad_avance:.0f}% probabilidad de avance"
                for e in destacados[:5]
            )
            or "  Ninguno"
        )

        # Líneas de alertas con nombres
        alerta_parts = []
        if alertas.posible_trampa > 0:
            nombres = [e.nombre for e in ests if "posible_trampa" in e.alertas]
            alerta_parts.append(
                f"- Posible trampa: {alertas.posible_trampa} ({', '.join(nombres[:3])})"
            )
        if alertas.inactivo > 0:
            nombres = [e.nombre for e in ests if "inactivo" in e.alertas]
            alerta_parts.append(
                f"- Inactivos: {alertas.inactivo} ({', '.join(nombres[:3])})"
            )
        if alertas.rezagado > 0:
            nombres = [e.nombre for e in ests if "rezagado" in e.alertas]
            alerta_parts.append(
                f"- Rezagados: {alertas.rezagado} ({', '.join(nombres[:3])})"
            )
        if alertas.dificultad_persistente > 0:
            nombres = [e.nombre for e in ests if "dificultad_persistente" in e.alertas]
            alerta_parts.append(
                f"- Dificultad persistente: {alertas.dificultad_persistente} ({', '.join(nombres[:3])})"
            )
        if alertas.excelencia > 0:
            alerta_parts.append(f"- Estudiantes destacados: {alertas.excelencia}")

        alertas_str = "\n".join(alerta_parts) or "Sin alertas activas"

        return f"""Eres un asesor pedagógico para profesores de matemáticas de 5to grado (decimales).

Analiza los datos del grupo "{stats.grupo_nombre}" ({stats.total_estudiantes} estudiantes) y genera recomendaciones concretas.

PERFILES DE APRENDIZAJE (clasificados por clustering ML):
- Rápido y Preciso: {dist.rapido_preciso} estudiantes
- Cuidadoso y Metódico: {dist.cuidadoso_metodico} estudiantes
- Impulsivo: {dist.impulsivo} estudiantes
- En Desarrollo: {dist.en_desarrollo} estudiantes
- Sin Clasificar (pocos datos): {dist.no_clasificado} estudiantes

ALERTAS ACTIVAS:
{alertas_str}

NIVELES PROMEDIO POR OPERACIÓN (escala 1-5):
- Suma: {avg_suma:.1f}
- Resta: {avg_resta:.1f}
- Multiplicación: {avg_mult:.1f}
- División: {avg_div:.1f}

PRECISIÓN PROMEDIO DEL GRUPO: {avg_prec:.1f}%

ESTUDIANTES QUE NECESITAN ATENCIÓN (baja probabilidad de avance o días inactivos):
{atencion_str}

ESTUDIANTES DESTACADOS (alta probabilidad de avance):
{destacados_str}

Genera un análisis pedagógico con:
1. Diagnóstico general del grupo (2-3 oraciones)
2. Máximo 3 puntos de acción prioritarios, concretos y accionables para el profesor
3. Una estrategia grupal recomendada

Responde en español, máximo 250 palabras, texto corrido sin bullets ni emojis."""
