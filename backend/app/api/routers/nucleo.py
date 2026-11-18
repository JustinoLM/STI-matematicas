"""
Núcleo de práctica (fase 3b). Prefijo /api/nucleo.

Estudiante (con salón activo):
- GET  /estado                                           ¿Practica en el núcleo? y su sesión a medias
- POST /sesiones                                         Iniciar sesión (o recuperar la activa)
- POST /sesiones/{sesion_id}/descartar                   Abandonar la sesión activa
- GET  /sesiones/{sesion_id}/siguiente                   Problema del turno (vista pública)
- POST /sesiones/{sesion_id}/problemas/{id}/respuesta    Enviar respuestas, tiempo, voz y eventos
- POST /sesiones/{sesion_id}/problemas/{id}/pista        Pedir una pista (nivel 1 a 3)
- GET  /dominio                                          Mi dominio por lección y experiencia
- GET  /progreso                                         Nivel de jugador, avance por camino y mapa (fase 7b)
- GET  /medallas                                         Medallas del núcleo del grado (fase 7b)

Profesor (pantalla "Lecciones del salón", fase 6a; solo sus propios salones):
- GET    /anios/{anio_id}/catalogo                       Todas las lecciones con habilitación y prerrequisitos del año
- GET    /anios/{anio_id}/lecciones                      Lecciones habilitadas o deshabilitadas
- PUT    /anios/{anio_id}/lecciones/{leccion_id}         Habilitar o configurar (MAX_PRIORITARIAS)
- DELETE /anios/{anio_id}/lecciones/{leccion_id}         Deshabilitar (conserva configuración y dominio)
- PUT    /anios/{anio_id}/lecciones/{leccion_id}/prerrequisitos  Editar en este año (PRERREQUISITO_CICLO)
- DELETE /anios/{anio_id}/lecciones/{leccion_id}/prerrequisitos  Volver a los del currículo
- GET    /anios/{anio_id}/asignaciones                   Asignaciones individuales del salón
- POST   /anios/{anio_id}/asignaciones                   Asignar una lección a un estudiante
- DELETE /asignaciones/{asignacion_id}                   Cancelar una asignación
- GET    /anios/{anio_id}/ajustes                        Banco forzado de cada estudiante del salón
- PUT    /anios/{anio_id}/estudiantes/{estudiante_id}/ajustes   Forzar el banco

Seguimiento (fase 6b):
- GET    /anios/{anio_id}/seguimiento?trimestre=N        Tabla por lección y por estudiante (hoy o en un trimestre)
- GET    /anios/{anio_id}/alertas                        Alertas de dificultad y excelencia del salón
- POST   /anios/{anio_id}/alertas/ocultar                Ocultar una alerta unos días
- GET    /alertas                                        Alertas de todos los salones activos del profesor
- GET    /anios/{anio_id}/estudiantes/{estudiante_id}/ficha?trimestre=N   Ficha del estudiante
- GET    /anios/{anio_id}/plan                           Plan por trimestre (lo aplica antes de responder)
- PUT    /anios/{anio_id}/plan                           Guardar el plan
- DELETE /anios/{anio_id}/plan/manual/{leccion_id}       Devolver una lección al plan
- GET    /anios/{anio_id}/estudiantes/{estudiante_id}/dominio   Dominio de un estudiante

Diagnóstico inicial (fase 7a; el del estudiante corre por las mismas rutas de sesión):
- POST   /anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico           Pedir que lo repita
- POST   /anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico/cerrar    Cerrar con lo obtenido
- POST   /anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico/cancelar  Cancelar sin aplicar nada

Los errores de reglas responden con {"detail", "codigo"} (manejador de ErrorSalon).
"""

from typing import Optional

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentStudent, CurrentStudentConSalon, CurrentTeacher, DBSession
from app.models.nucleo import SESION_DIAGNOSTICO
from app.nucleo.problema import problema_a_dict, problema_desde_dict
from app.nucleo.registro import tiene_generador
from app.nucleo.servicios.grafo import prerrequisitos_efectivos
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.motivacion import ServicioMotivacion
from app.nucleo.servicios.plan import ServicioPlan
from app.nucleo.servicios.practica import ServicioPractica
from app.nucleo.servicios.seguimiento import ServicioSeguimiento
from app.schemas.nucleo import (
    AjustesIn,
    AjustesOut,
    AsignacionIn,
    AsignacionOut,
    DominioOut,
    EstadoNucleoOut,
    HabilitacionIn,
    HabilitacionOut,
    LeccionSalonOut,
    OcultarAlertaIn,
    PistaIn,
    PistaOut,
    PlanIn,
    PrerrequisitosIn,
    PrerrequisitosOut,
    ProblemaOut,
    RespuestaIn,
    RespuestaOut,
    SesionOut,
)

router = APIRouter()


def _sesion_out(s) -> SesionOut:
    return SesionOut(sesion_id=s.id, estado=s.estado, tipo=s.tipo, cantidad_problemas=s.cantidad_problemas,
                     progreso=s.progreso, fecha_inicio=s.fecha_inicio)


# ─── Estudiante ──────────────────────────────────────────────────────────────

@router.get("/estado", response_model=EstadoNucleoOut)
async def estado(db: DBSession, estudiante: CurrentStudent):
    """No exige salón: sin salón responde disponible=false."""
    return await ServicioPractica(db).estado(estudiante.id)


@router.post("/sesiones/{sesion_id}/descartar", response_model=SesionOut)
async def descartar(sesion_id: int, db: DBSession, estudiante: CurrentStudentConSalon):
    return _sesion_out(await ServicioPractica(db).descartar(estudiante.id, sesion_id))


@router.post("/sesiones", response_model=SesionOut)
async def iniciar_sesion(db: DBSession, estudiante: CurrentStudentConSalon):
    return _sesion_out(await ServicioPractica(db).iniciar_sesion(estudiante.id))


@router.get("/sesiones/{sesion_id}/siguiente", response_model=ProblemaOut)
async def siguiente(sesion_id: int, db: DBSession, estudiante: CurrentStudentConSalon):
    servicio = ServicioPractica(db)
    ps = await servicio.siguiente(estudiante.id, sesion_id)
    if ps is None:
        return ProblemaOut(sesion_completada=True)
    p = await servicio.parametros()
    sesion = await servicio.sesion_del_estudiante(sesion_id, estudiante.id)
    if sesion.tipo == SESION_DIAGNOSTICO:
        servicio_diag = await servicio.diagnostico()
        estado_diag = await servicio_diag.calcular(await servicio_diag.de_la_sesion(sesion.id))
        return ProblemaOut(
            sesion_completada=False, problema_sesion_id=ps.id, orden=ps.orden,
            problema=problema_a_dict(problema_desde_dict(ps.problema), incluir_respuestas=False),
            intentos_restantes=1, pistas_habilitadas={"1": False, "2": False, "3": False},
            diagnostico=True, avance=estado_diag.avance(p),
        )
    return ProblemaOut(
        sesion_completada=False,
        problema_sesion_id=ps.id,
        orden=ps.orden,
        problema=problema_a_dict(problema_desde_dict(ps.problema), incluir_respuestas=False),
        intentos_restantes=p.intentos_por_problema - ps.intentos,
        pistas_habilitadas=await servicio.pistas_habilitadas(sesion, ps.leccion_id),
    )


@router.post("/sesiones/{sesion_id}/problemas/{problema_sesion_id}/respuesta", response_model=RespuestaOut)
async def responder(sesion_id: int, problema_sesion_id: int, datos: RespuestaIn,
                    db: DBSession, estudiante: CurrentStudentConSalon):
    return await ServicioPractica(db).responder(
        estudiante.id, sesion_id, problema_sesion_id, datos.respuestas, datos.tiempo_ms,
        datos.uso_voz, [e.model_dump() for e in datos.eventos],
    )


@router.post("/sesiones/{sesion_id}/problemas/{problema_sesion_id}/pista", response_model=PistaOut)
async def pedir_pista(sesion_id: int, problema_sesion_id: int, datos: PistaIn,
                      db: DBSession, estudiante: CurrentStudentConSalon):
    return await ServicioPractica(db).pista(estudiante.id, sesion_id, problema_sesion_id, datos.nivel)


@router.get("/dominio", response_model=DominioOut)
async def mi_dominio(db: DBSession, estudiante: CurrentStudentConSalon):
    return await ServicioPractica(db).resumen_dominio(estudiante.id)


@router.get("/progreso")
async def mi_progreso(db: DBSession, estudiante: CurrentStudent):
    """Nivel de jugador y experiencia, avance de cada camino y el mapa del grado. Sin salón, solo el nivel."""
    return await ServicioMotivacion(db).progreso(estudiante.id)


@router.get("/medallas")
async def mis_medallas(db: DBSession, estudiante: CurrentStudent):
    """Medallas del núcleo del grado del estudiante (ganadas y por ganar)."""
    return await ServicioMotivacion(db).medallas(estudiante.id)


# ─── Profesor ────────────────────────────────────────────────────────────────

@router.get("/anios/{anio_id}/catalogo", response_model=list[LeccionSalonOut])
async def catalogo(anio_id: int, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    await servicio.school.anio_del_profesor(anio_id, profesor.id)
    await ServicioPlan(db).aplicar(anio_id)
    return await servicio.catalogo(anio_id, profesor.id)


@router.put("/anios/{anio_id}/lecciones/{leccion_id}/prerrequisitos", response_model=PrerrequisitosOut)
async def editar_prerrequisitos(anio_id: int, leccion_id: str, datos: PrerrequisitosIn,
                                db: DBSession, profesor: CurrentTeacher):
    pres = await ServicioHabilitacion(db).editar_prerrequisitos(anio_id, profesor.id, leccion_id, datos.prerrequisitos)
    return PrerrequisitosOut(leccion_id=leccion_id, prerrequisitos=pres, editados=True)


@router.delete("/anios/{anio_id}/lecciones/{leccion_id}/prerrequisitos", response_model=PrerrequisitosOut)
async def restaurar_prerrequisitos(anio_id: int, leccion_id: str, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    await servicio.restaurar_prerrequisitos(anio_id, profesor.id, leccion_id)
    pres = (await prerrequisitos_efectivos(db, None)).get(leccion_id, ())
    return PrerrequisitosOut(leccion_id=leccion_id, prerrequisitos=list(pres), editados=False)


@router.get("/anios/{anio_id}/lecciones", response_model=list[HabilitacionOut])
async def lecciones_del_salon(anio_id: int, db: DBSession, profesor: CurrentTeacher):
    return [
        HabilitacionOut(
            leccion_id=h.leccion_id, titulo=lec.leccion_titulo, grado=lec.grado,
            habilitada=h.habilitada, signo=h.signo, iconos=h.iconos, pistas=h.pistas,
            prioritaria=h.prioritaria, tiene_generador=tiene_generador(h.leccion_id),
        )
        for h, lec in await ServicioHabilitacion(db).listar(anio_id, profesor.id)
    ]


async def _habilitacion_out(servicio: ServicioHabilitacion, anio_id: int, profesor_id: int, leccion_id: str):
    for h, lec in await servicio.listar(anio_id, profesor_id):
        if h.leccion_id == leccion_id:
            return HabilitacionOut(
                leccion_id=h.leccion_id, titulo=lec.leccion_titulo, grado=lec.grado,
                habilitada=h.habilitada, signo=h.signo, iconos=h.iconos, pistas=h.pistas,
                prioritaria=h.prioritaria, tiene_generador=tiene_generador(h.leccion_id),
            )


@router.put("/anios/{anio_id}/lecciones/{leccion_id}", response_model=HabilitacionOut)
async def habilitar(anio_id: int, leccion_id: str, datos: HabilitacionIn,
                    db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    await servicio.habilitar(anio_id, profesor.id, leccion_id, signo=datos.signo, iconos=datos.iconos,
                             pistas=datos.pistas, prioritaria=datos.prioritaria)
    return await _habilitacion_out(servicio, anio_id, profesor.id, leccion_id)


@router.delete("/anios/{anio_id}/lecciones/{leccion_id}", response_model=HabilitacionOut)
async def deshabilitar(anio_id: int, leccion_id: str, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    await servicio.deshabilitar(anio_id, profesor.id, leccion_id)
    return await _habilitacion_out(servicio, anio_id, profesor.id, leccion_id)


@router.get("/anios/{anio_id}/asignaciones", response_model=list[AsignacionOut])
async def asignaciones(anio_id: int, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    return await servicio.describir(await servicio.asignaciones(anio_id, profesor.id))


@router.post("/anios/{anio_id}/asignaciones", response_model=AsignacionOut, status_code=status.HTTP_201_CREATED)
async def asignar(anio_id: int, datos: AsignacionIn, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    asig = await servicio.asignar(anio_id, profesor.id, datos.estudiante_id, datos.leccion_id)
    return (await servicio.describir([asig]))[0]


@router.delete("/asignaciones/{asignacion_id}", response_model=AsignacionOut)
async def cancelar_asignacion(asignacion_id: int, db: DBSession, profesor: CurrentTeacher):
    servicio = ServicioHabilitacion(db)
    return (await servicio.describir([await servicio.cancelar_asignacion(asignacion_id, profesor.id)]))[0]


@router.get("/anios/{anio_id}/ajustes", response_model=list[AjustesOut])
async def ajustes_del_salon(anio_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioHabilitacion(db).ajustes(anio_id, profesor.id)


@router.put("/anios/{anio_id}/estudiantes/{estudiante_id}/ajustes", response_model=AjustesOut)
async def ajustes(anio_id: int, estudiante_id: int, datos: AjustesIn, db: DBSession, profesor: CurrentTeacher):
    return await ServicioHabilitacion(db).ajustar_estudiante(anio_id, profesor.id, estudiante_id, datos.banco_forzado)


@router.get("/anios/{anio_id}/estudiantes/{estudiante_id}/dominio", response_model=DominioOut)
async def dominio_estudiante(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher):
    await ServicioHabilitacion(db).exigir_estudiante_del_profesor(anio_id, profesor.id, estudiante_id)
    return await ServicioPractica(db).resumen_dominio(estudiante_id, anio_id)


# ─── Seguimiento (fase 6b) ───────────────────────────────────────────────────

Trimestre = Query(None, ge=1, le=3, description="Corte por trimestre; sin él, el estado de hoy")


@router.get("/anios/{anio_id}/seguimiento")
async def seguimiento(anio_id: int, db: DBSession, profesor: CurrentTeacher, trimestre: Optional[int] = Trimestre):
    return await ServicioSeguimiento(db).seguimiento(anio_id, profesor.id, trimestre)


@router.get("/anios/{anio_id}/alertas")
async def alertas_del_salon(anio_id: int, db: DBSession, profesor: CurrentTeacher, incluir_ocultas: bool = False):
    return await ServicioSeguimiento(db).alertas(anio_id, profesor.id, incluir_ocultas)


@router.post("/anios/{anio_id}/alertas/ocultar", status_code=status.HTTP_204_NO_CONTENT)
async def ocultar_alerta(anio_id: int, datos: OcultarAlertaIn, db: DBSession, profesor: CurrentTeacher):
    await ServicioSeguimiento(db).ocultar(anio_id, profesor.id, datos.estudiante_id, datos.leccion_id, datos.tipo)


@router.get("/alertas")
async def alertas_del_profesor(db: DBSession, profesor: CurrentTeacher):
    return await ServicioSeguimiento(db).alertas_del_profesor(profesor.id)


@router.get("/anios/{anio_id}/estudiantes/{estudiante_id}/ficha")
async def ficha(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher,
                trimestre: Optional[int] = Trimestre):
    return await ServicioSeguimiento(db).ficha(anio_id, profesor.id, estudiante_id, trimestre)


@router.get("/anios/{anio_id}/plan")
async def plan(anio_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioPlan(db).resumen(anio_id, profesor.id)


@router.put("/anios/{anio_id}/plan")
async def guardar_plan(anio_id: int, datos: PlanIn, db: DBSession, profesor: CurrentTeacher):
    return await ServicioPlan(db).guardar(anio_id, profesor.id, datos.plan)


@router.delete("/anios/{anio_id}/plan/manual/{leccion_id}")
async def devolver_al_plan(anio_id: int, leccion_id: str, db: DBSession, profesor: CurrentTeacher):
    return await ServicioPlan(db).devolver_al_plan(anio_id, profesor.id, leccion_id)


# ─── Diagnóstico (profesor) ──────────────────────────────────────────────────

@router.post("/anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico")
async def pedir_diagnostico(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioSeguimiento(db).diagnostico(anio_id, profesor.id, estudiante_id, "pedir")


@router.post("/anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico/cerrar")
async def cerrar_diagnostico(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioSeguimiento(db).diagnostico(anio_id, profesor.id, estudiante_id, "cerrar")


@router.post("/anios/{anio_id}/estudiantes/{estudiante_id}/diagnostico/cancelar")
async def cancelar_diagnostico(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioSeguimiento(db).diagnostico(anio_id, profesor.id, estudiante_id, "cancelar")
