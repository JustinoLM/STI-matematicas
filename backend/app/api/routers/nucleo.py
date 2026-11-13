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

Profesor (sin interfaz hasta la fase 6):
- GET    /anios/{anio_id}/lecciones                      Lecciones habilitadas o deshabilitadas
- PUT    /anios/{anio_id}/lecciones/{leccion_id}         Habilitar o configurar
- DELETE /anios/{anio_id}/lecciones/{leccion_id}         Deshabilitar (conserva configuración y dominio)
- GET    /anios/{anio_id}/asignaciones                   Asignaciones individuales del salón
- POST   /anios/{anio_id}/asignaciones                   Asignar una lección a un estudiante
- DELETE /asignaciones/{asignacion_id}                   Cancelar una asignación
- PUT    /anios/{anio_id}/estudiantes/{estudiante_id}/ajustes   Forzar el banco
- GET    /anios/{anio_id}/estudiantes/{estudiante_id}/dominio   Dominio de un estudiante

Los errores de reglas responden con {"detail", "codigo"} (manejador de ErrorSalon).
"""

from fastapi import APIRouter, status

from app.api.dependencies import CurrentStudent, CurrentStudentConSalon, CurrentTeacher, DBSession
from app.nucleo.problema import problema_a_dict, problema_desde_dict
from app.nucleo.registro import tiene_generador
from app.nucleo.servicios.habilitacion import ServicioHabilitacion
from app.nucleo.servicios.practica import ServicioPractica
from app.schemas.nucleo import (
    AjustesIn,
    AjustesOut,
    AsignacionIn,
    AsignacionOut,
    DominioOut,
    EstadoNucleoOut,
    HabilitacionIn,
    HabilitacionOut,
    PistaIn,
    PistaOut,
    ProblemaOut,
    RespuestaIn,
    RespuestaOut,
    SesionOut,
)

router = APIRouter()


def _sesion_out(s) -> SesionOut:
    return SesionOut(sesion_id=s.id, estado=s.estado, cantidad_problemas=s.cantidad_problemas,
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


# ─── Profesor ────────────────────────────────────────────────────────────────

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
    return await ServicioHabilitacion(db).asignaciones(anio_id, profesor.id)


@router.post("/anios/{anio_id}/asignaciones", response_model=AsignacionOut, status_code=status.HTTP_201_CREATED)
async def asignar(anio_id: int, datos: AsignacionIn, db: DBSession, profesor: CurrentTeacher):
    return await ServicioHabilitacion(db).asignar(anio_id, profesor.id, datos.estudiante_id, datos.leccion_id)


@router.delete("/asignaciones/{asignacion_id}", response_model=AsignacionOut)
async def cancelar_asignacion(asignacion_id: int, db: DBSession, profesor: CurrentTeacher):
    return await ServicioHabilitacion(db).cancelar_asignacion(asignacion_id, profesor.id)


@router.put("/anios/{anio_id}/estudiantes/{estudiante_id}/ajustes", response_model=AjustesOut)
async def ajustes(anio_id: int, estudiante_id: int, datos: AjustesIn, db: DBSession, profesor: CurrentTeacher):
    return await ServicioHabilitacion(db).ajustar_estudiante(anio_id, profesor.id, estudiante_id, datos.banco_forzado)


@router.get("/anios/{anio_id}/estudiantes/{estudiante_id}/dominio", response_model=DominioOut)
async def dominio_estudiante(anio_id: int, estudiante_id: int, db: DBSession, profesor: CurrentTeacher):
    await ServicioHabilitacion(db).exigir_estudiante_del_profesor(anio_id, profesor.id, estudiante_id)
    return await ServicioPractica(db).resumen_dominio(estudiante_id, anio_id)
