"""
Service para lógica de gamificación.

Gestiona puntos, medallas, compras y personalización.
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.repositories.gamification_repository import GamificationRepository
from app.repositories.adaptive_repository import AdaptiveRepository
from app.models.gamification import (
    CategoriaDesbloqueable,
    Desbloqueable,
    Medalla,
    CategoriaMedalla,
)
from app.models.adaptive import SesionPractica, PerfilEstudiante
from app.schemas.gamification import (
    DesbloqueableResponse,
    ComprarItemResponse,
    TiendaResponse,
    SaldoPuntosResponse,
    HistorialPuntosResponse,
    TransaccionPuntosResponse,
    DesglosePuntosResponse,
    MedallaResponse,
    MedallasResponse,
    MedallaProgresoResponse,
    MedallasProgresoResponse,
    PersonalizacionResponse,
    RecompensasSesionResponse,
    MedallaNuevaResponse,
    TemaInicialResponse,
    TemasInicialesResponse,
)


class GamificationService:
    """Service para lógica de gamificación."""
    
    def __init__(
        self,
        gamification_repo: GamificationRepository,
        adaptive_repo: AdaptiveRepository
    ):
        self.gamification_repo = gamification_repo
        self.adaptive_repo = adaptive_repo
    
    # ============================================
    # Cálculo de Puntos por Sesión
    # ============================================
    
    async def calcular_puntos_sesion(
        self,
        sesion: SesionPractica,
        perfil: PerfilEstudiante
    ) -> Dict:
        """
        Calcula los puntos ganados en una sesión.
        
        Returns:
            Dict con 'total' y 'desglose'
        """
        puntos = 0
        desglose = {}
        
        # Base por precisión
        if sesion.cantidad_problemas == 0:
            return {"total": 0, "desglose": {}}
        
        precision = sesion.problemas_correctos / sesion.cantidad_problemas
        
        if precision == 1.0:
            puntos += 100
            desglose["practica_perfecta"] = 100
        elif precision >= 0.9:
            puntos += 75
            desglose["precision_alta"] = 75
        elif precision >= 0.7:
            puntos += 50
            desglose["precision_media"] = 50
        else:
            puntos += 25
            desglose["participacion"] = 25
        
        # Bonus velocidad (más rápido que promedio personal)
        if perfil.velocidad_promedio and sesion.velocidad_promedio:
            if float(sesion.velocidad_promedio) < float(perfil.velocidad_promedio):
                puntos += 20
                desglose["bonus_velocidad"] = 20
        
        # Bonus primera práctica del día
        if await self._es_primera_practica_del_dia(sesion.estudiante_id, sesion.fecha_inicio):
            puntos += 10
            desglose["primera_del_dia"] = 10
        
        # Bonus por subida de nivel
        if sesion.cambios_nivel:
            for operacion, cambio in sesion.cambios_nivel.items():
                if cambio.get("despues", 0) > cambio.get("antes", 0):
                    if operacion == "nivel_general":
                        puntos += 150
                        desglose["nivel_general_subio"] = 150
                    else:
                        puntos += 75
                        desglose[f"subio_{operacion}"] = 75
        
        return {
            "total": puntos,
            "desglose": desglose
        }
    
    async def _es_primera_practica_del_dia(
        self,
        estudiante_id: int,
        fecha_sesion: datetime
    ) -> bool:
        """Verifica si es la primera práctica del día."""
        inicio_dia = fecha_sesion.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)
        
        sesiones_hoy = await self.adaptive_repo.count_sesiones_en_rango(
            estudiante_id,
            inicio_dia,
            fin_dia
        )
        
        return sesiones_hoy <= 1  # Esta es la primera (o única)
    
    async def registrar_puntos_sesion(
        self,
        sesion_id: int,
        estudiante_id: int
    ) -> DesglosePuntosResponse:
        """
        Calcula y registra los puntos ganados en una sesión.
        
        Actualiza sesion.puntos_ganados y sesion.desglose_puntos.
        Agrega los puntos al estudiante.
        """
        # Obtener sesión y perfil
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        perfil = await self.adaptive_repo.get_perfil(estudiante_id)
        
        if not sesion or not perfil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión o perfil no encontrado"
            )
        
        # Calcular puntos
        resultado = await self.calcular_puntos_sesion(sesion, perfil)
        
        # Actualizar sesión
        sesion.puntos_ganados = resultado["total"]
        sesion.desglose_puntos = resultado["desglose"]
        await self.adaptive_repo.update_sesion(sesion)
        
        # Agregar puntos al estudiante
        await self.gamification_repo.agregar_puntos(
            estudiante_id=estudiante_id,
            cantidad=resultado["total"],
            concepto=f"Sesión #{sesion_id} completada",
            sesion_id=sesion_id
        )
        
        return DesglosePuntosResponse(
            total=resultado["total"],
            desglose=resultado["desglose"]
        )
    
    # ============================================
    # Gestión de Puntos
    # ============================================
    
    async def get_saldo(self, estudiante_id: int) -> SaldoPuntosResponse:
        """Obtiene el saldo actual de puntos."""
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        
        return SaldoPuntosResponse(
            estudiante_id=estudiante_id,
            puntos_totales=saldo
        )
    
    async def get_historial_transacciones(
        self,
        estudiante_id: int,
        limit: int = 50
    ) -> HistorialPuntosResponse:
        """Obtiene historial de transacciones."""
        transacciones = await self.gamification_repo.get_historial_transacciones(
            estudiante_id,
            limit
        )
        
        items = [
            TransaccionPuntosResponse(
                id=t.id,
                tipo=t.tipo.value,
                cantidad=t.cantidad,
                concepto=t.concepto,
                saldo_resultante=t.saldo_resultante,
                fecha=t.fecha
            )
            for t in transacciones
        ]
        
        return HistorialPuntosResponse(
            total=len(items),
            transacciones=items
        )
    
    # ============================================
    # Tienda de Desbloqueables
    # ============================================
    
    async def get_tienda_completa(
        self,
        estudiante_id: int
    ) -> TiendaResponse:
        """
        Obtiene el catálogo completo de la tienda.
        
        Marca los items que el estudiante ya posee.
        """
        # Obtener todos los desbloqueables
        catalogo = await self.gamification_repo.get_catalogo_completo()
        
        # Obtener items poseídos
        items_poseidos = await self.gamification_repo.get_items_poseidos(estudiante_id)
        poseidos_ids = {item.desbloqueable_id for item in items_poseidos}
        poseidos_dict = {
            item.desbloqueable_id: item.fecha_compra
            for item in items_poseidos
        }
        
        # Categorizar
        temas = []
        fondos = []
        colores = []
        musicas = []
        efectos = []
        
        for item in catalogo:
            response = DesbloqueableResponse(
                id=item.id,
                categoria=item.categoria.value,
                nombre=item.nombre,
                descripcion=item.descripcion,
                precio_puntos=item.precio_puntos,
                nivel_minimo_requerido=item.nivel_minimo_requerido,
                archivo_referencia=item.archivo_referencia,
                orden=item.orden,
                es_tema_inicial=item.es_tema_inicial,
                poseido=item.id in poseidos_ids,
                fecha_compra=poseidos_dict.get(item.id)
            )
            
            if item.categoria == CategoriaDesbloqueable.TEMA:
                temas.append(response)
            elif item.categoria == CategoriaDesbloqueable.FONDO:
                fondos.append(response)
            elif item.categoria == CategoriaDesbloqueable.COLOR:
                colores.append(response)
            elif item.categoria == CategoriaDesbloqueable.MUSICA:
                musicas.append(response)
            elif item.categoria == CategoriaDesbloqueable.EFECTO:
                efectos.append(response)
        
        return TiendaResponse(
            temas=temas,
            fondos=fondos,
            colores=colores,
            musicas=musicas,
            efectos=efectos,
            total_items=len(catalogo)
        )
    
    async def get_items_poseidos(self, estudiante_id: int) -> List[DesbloqueableResponse]:
        """Obtiene solo los items que el estudiante posee."""
        items_poseidos = await self.gamification_repo.get_items_poseidos(estudiante_id)
        
        responses = []
        for item_rel in items_poseidos:
            desbloqueable = await self.gamification_repo.get_desbloqueable(
                item_rel.desbloqueable_id
            )
            
            if desbloqueable:
                responses.append(DesbloqueableResponse(
                    id=desbloqueable.id,
                    categoria=desbloqueable.categoria.value,
                    nombre=desbloqueable.nombre,
                    descripcion=desbloqueable.descripcion,
                    precio_puntos=desbloqueable.precio_puntos,
                    nivel_minimo_requerido=desbloqueable.nivel_minimo_requerido,
                    archivo_referencia=desbloqueable.archivo_referencia,
                    orden=desbloqueable.orden,
                    es_tema_inicial=desbloqueable.es_tema_inicial,
                    poseido=True,
                    fecha_compra=item_rel.fecha_compra
                ))
        
        return responses
    
    async def comprar_item(
        self,
        estudiante_id: int,
        desbloqueable_id: int
    ) -> ComprarItemResponse:
        """
        Compra un item de la tienda.
        
        Valida:
        - Que el item exista
        - Que no lo posea ya
        - Que tenga suficientes puntos
        - Que tenga el nivel requerido
        """
        # Obtener item
        item = await self.gamification_repo.get_desbloqueable(desbloqueable_id)
        
        if not item or not item.activo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item no encontrado o no disponible"
            )
        
        # Verificar si ya lo posee
        ya_posee = await self.gamification_repo.estudiante_posee_item(
            estudiante_id,
            desbloqueable_id
        )
        
        if ya_posee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya posees este item"
            )
        
        # Verificar nivel requerido
        perfil = await self.adaptive_repo.get_perfil(estudiante_id)
        
        if perfil.nivel_actual < item.nivel_minimo_requerido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requieres nivel {item.nivel_minimo_requerido} para comprar este item (tienes nivel {perfil.nivel_actual})"
            )
        
        # Verificar saldo
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        
        if saldo < item.precio_puntos:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Puntos insuficientes. Tienes {saldo}, necesitas {item.precio_puntos}"
            )
        
        # Gastar puntos
        nuevo_saldo = await self.gamification_repo.gastar_puntos(
            estudiante_id=estudiante_id,
            cantidad=item.precio_puntos,
            concepto=f"Compra: {item.nombre}",
            desbloqueable_id=desbloqueable_id
        )
        
        # Desbloquear item
        await self.gamification_repo.desbloquear_item(
            estudiante_id=estudiante_id,
            desbloqueable_id=desbloqueable_id,
            puntos_gastados=item.precio_puntos
        )
        
        # Preparar response
        item_response = DesbloqueableResponse(
            id=item.id,
            categoria=item.categoria.value,
            nombre=item.nombre,
            descripcion=item.descripcion,
            precio_puntos=item.precio_puntos,
            nivel_minimo_requerido=item.nivel_minimo_requerido,
            archivo_referencia=item.archivo_referencia,
            orden=item.orden,
            es_tema_inicial=item.es_tema_inicial,
            poseido=True,
            fecha_compra=datetime.utcnow()
        )
        
        mensaje = f"¡Desbloqueaste {item.nombre}!"
        
        return ComprarItemResponse(
            exito=True,
            mensaje=mensaje,
            item_comprado=item_response,
            puntos_gastados=item.precio_puntos,
            saldo_nuevo=nuevo_saldo
        )
    
    # ============================================
    # Gestión de Medallas
    # ============================================
    
    async def get_medallas_estudiante(self, estudiante_id: int) -> MedallasResponse:
        """Obtiene todas las medallas con estado de obtención."""
        # Obtener todas las medallas
        todas_medallas = await self.gamification_repo.get_todas_medallas()

        # Obtener medallas del estudiante
        medallas_obtenidas = await self.gamification_repo.get_medallas_estudiante(estudiante_id)
        obtenidas_ids = {m.medalla_id for m in medallas_obtenidas}
        obtenidas_dict = {
            m.medalla_id: m.fecha_obtencion
            for m in medallas_obtenidas
        }

        # Obtener medalla destacada de la personalización
        personalizacion = await self.gamification_repo.get_personalizacion(estudiante_id)
        medalla_destacada_id = personalizacion.medalla_destacada_id if personalizacion else None

        responses = []
        for medalla in todas_medallas:
            responses.append(MedallaResponse(
                id=medalla.id,
                nombre=medalla.nombre,
                descripcion=medalla.descripcion,
                categoria=medalla.categoria.value,
                imagen_url=medalla.imagen_url,
                es_secreta=medalla.es_secreta,
                orden=medalla.orden,
                obtenida=medalla.id in obtenidas_ids,
                fecha_obtencion=obtenidas_dict.get(medalla.id)
            ))

        return MedallasResponse(
            total_medallas=len(todas_medallas),
            medallas_obtenidas=len(obtenidas_ids),
            medallas=responses,
            medalla_destacada_id=medalla_destacada_id,
        )

    async def set_medalla_destacada(self, estudiante_id: int, medalla_id: Optional[int]) -> None:
        """Establece la medalla destacada en el dashboard del estudiante."""
        from sqlalchemy import select
        from app.models.gamification import PersonalizacionEstudiante

        result = await self.gamification_repo.db.execute(
            select(PersonalizacionEstudiante).where(
                PersonalizacionEstudiante.estudiante_id == estudiante_id
            )
        )
        personalizacion = result.scalar_one_or_none()

        if not personalizacion:
            personalizacion = PersonalizacionEstudiante(
                estudiante_id=estudiante_id,
                medalla_destacada_id=medalla_id,
            )
            self.gamification_repo.db.add(personalizacion)
        else:
            personalizacion.medalla_destacada_id = medalla_id

        await self.gamification_repo.db.commit()
    
    async def verificar_y_otorgar_medallas(
        self,
        estudiante_id: int
    ) -> List[Medalla]:
        """
        Verifica si el estudiante cumple criterios para nuevas medallas.
        
        Otorga automáticamente las medallas ganadas.
        
        Returns:
            Lista de medallas recién otorgadas.
        """
        medallas_nuevas = []
        
        # Obtener todas las medallas
        todas_medallas = await self.gamification_repo.get_todas_medallas()
        
        # Obtener perfil y stats
        perfil = await self.adaptive_repo.get_perfil(estudiante_id)
        
        for medalla in todas_medallas:
            # Verificar si ya la tiene
            ya_tiene = await self.gamification_repo.estudiante_tiene_medalla(
                estudiante_id,
                medalla.id
            )
            
            if ya_tiene:
                continue
            
            # Verificar criterio
            if await self._cumple_criterio_medalla(estudiante_id, perfil, medalla):
                # Otorgar medalla
                await self.gamification_repo.otorgar_medalla(
                    estudiante_id,
                    medalla.id
                )
                medallas_nuevas.append(medalla)
        
        return medallas_nuevas
    
    async def _cumple_criterio_medalla(
        self,
        estudiante_id: int,
        perfil: PerfilEstudiante,
        medalla: Medalla
    ) -> bool:
        """Verifica si cumple el criterio de una medalla."""
        criterio = medalla.criterio
        tipo = criterio.get("tipo")
        
        if tipo == "diagnostico":
            # Completar diagnóstico
            return perfil.diagnostico_completado
        
        elif tipo == "nivel":
            # Alcanzar nivel específico
            nivel_req = criterio.get("nivel", 2)
            operacion = criterio.get("operacion")
            
            if operacion == "general":
                return perfil.nivel_actual >= nivel_req
            elif operacion == "suma":
                return perfil.nivel_suma >= nivel_req
            elif operacion == "resta":
                return perfil.nivel_resta >= nivel_req
            elif operacion == "multiplicacion":
                return perfil.nivel_multiplicacion >= nivel_req
            elif operacion == "division":
                return perfil.nivel_division >= nivel_req
        
        elif tipo == "nivel_todas":
            # Nivel X en todas las operaciones
            nivel_req = criterio.get("nivel", 3)
            return all([
                perfil.nivel_suma >= nivel_req,
                perfil.nivel_resta >= nivel_req,
                perfil.nivel_multiplicacion >= nivel_req,
                perfil.nivel_division >= nivel_req
            ])
        
        elif tipo == "volumen":
            # Total de problemas resueltos
            cantidad_req = criterio.get("cantidad", 100)
            # Calcular total de problemas
            total_problemas = await self.adaptive_repo.get_total_problemas_resueltos(estudiante_id)
            return total_problemas >= cantidad_req
        
        elif tipo == "exploracion_temas":
            # Completar práctica con cada tema
            temas_req = criterio.get("temas_requeridos", 6)
            # TODO: Implementar cuando tengamos tracking de temas por sesión
            return False
        
        elif tipo == "racha":
            # Mejor racha histórica de sesiones perfectas consecutivas
            cantidad_req = criterio.get("cantidad", 20)
            mejor_racha = await self.adaptive_repo.get_mejor_racha_perfectas(estudiante_id)
            return mejor_racha >= cantidad_req

        elif tipo == "coleccionista":
            # Comprar X items
            cantidad_req = criterio.get("cantidad", 20)
            items_poseidos = await self.gamification_repo.get_items_poseidos(estudiante_id)
            return len(items_poseidos) >= cantidad_req

        elif tipo == "desafio_grupal":
            # Participar en desafíos (preparado para futuro)
            return False

        return False
    
    # ============================================
    # Personalización
    # ============================================
    
    async def get_personalizacion(
        self,
        estudiante_id: int
    ) -> PersonalizacionResponse:
        """Obtiene la configuración actual de personalización."""
        personalizacion = await self.gamification_repo.get_personalizacion(estudiante_id)
        
        if not personalizacion:
            # Crear configuración por defecto
            personalizacion = await self.gamification_repo.crear_personalizacion(estudiante_id)
        
        # Obtener nombres de items activos
        tema_nombre = None
        fondo_nombre = None
        musica_nombre = None
        
        if personalizacion.tema_activo_id:
            tema = await self.gamification_repo.get_desbloqueable(personalizacion.tema_activo_id)
            tema_nombre = tema.nombre if tema else None
        
        if personalizacion.fondo_activo_id:
            fondo = await self.gamification_repo.get_desbloqueable(personalizacion.fondo_activo_id)
            fondo_nombre = fondo.nombre if fondo else None
        
        if personalizacion.musica_activa_id:
            musica = await self.gamification_repo.get_desbloqueable(personalizacion.musica_activa_id)
            musica_nombre = musica.nombre if musica else None
        
        return PersonalizacionResponse(
            estudiante_id=estudiante_id,
            tema_activo_id=personalizacion.tema_activo_id,
            fondo_activo_id=personalizacion.fondo_activo_id,
            musica_activa_id=personalizacion.musica_activa_id,
            tema_activo_nombre=tema_nombre,
            fondo_activo_nombre=fondo_nombre,
            musica_activa_nombre=musica_nombre,
            color_fondo=personalizacion.color_fondo,
            color_texto=personalizacion.color_texto,
            color_botones=personalizacion.color_botones,
            efectos_activos=personalizacion.efectos_activos or [],
            fecha_actualizacion=personalizacion.fecha_actualizacion
        )
    
    async def actualizar_personalizacion(
        self,
        estudiante_id: int,
        **campos
    ) -> PersonalizacionResponse:
        """Actualiza la personalización del estudiante."""
        # Validar posesión del TEMA (ítem premium — no tiene acceso cruzado).
        # Fondos y músicas usan acceso cruzado entre temas: si el estudiante posee
        # el fondo/música nº1 de cualquier tema, puede activar el equivalente en
        # cualquier otro tema. La validación de esos ítems se hace en el frontend;
        # el backend solo verifica que el tema en sí esté desbloqueado.
        if "tema_activo_id" in campos and campos["tema_activo_id"]:
            if not await self.gamification_repo.estudiante_posee_item(
                estudiante_id,
                campos["tema_activo_id"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No posees este tema"
                )
        
        # Actualizar
        await self.gamification_repo.actualizar_personalizacion(
            estudiante_id,
            **campos
        )
        
        # Retornar configuración actualizada
        return await self.get_personalizacion(estudiante_id)
    
    # ============================================
    # Tema Inicial Gratis
    # ============================================
    
    async def get_temas_iniciales(self) -> TemasInicialesResponse:
        """Obtiene los temas disponibles para selección inicial."""
        temas = await self.gamification_repo.get_temas_iniciales()
        
        responses = [
            TemaInicialResponse(
                id=tema.id,
                nombre=tema.nombre,
                descripcion=tema.descripcion,
                archivo_referencia=tema.archivo_referencia,
                preview_url=tema.archivo_referencia  # Mismo path por ahora
            )
            for tema in temas
        ]
        
        return TemasInicialesResponse(
            temas=responses,
            mensaje="Elige tu primer tema (gratis)"
        )
    
    async def seleccionar_tema_inicial(
        self,
        estudiante_id: int,
        tema_id: int
    ) -> ComprarItemResponse:
        """
        Selecciona el tema inicial gratis.
        
        Solo se puede hacer una vez.
        """
        # Verificar que es un tema inicial
        tema = await self.gamification_repo.get_desbloqueable(tema_id)
        
        if not tema or not tema.es_tema_inicial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este no es un tema inicial válido"
            )
        
        # Verificar que no tenga ya un tema
        items = await self.gamification_repo.get_items_poseidos(estudiante_id)
        temas_poseidos = [
            item for item in items
            if item.desbloqueable.categoria == CategoriaDesbloqueable.TEMA
        ]
        
        if temas_poseidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya seleccionaste tu tema inicial"
            )
        
        # Desbloquear gratis
        await self.gamification_repo.desbloquear_item(
            estudiante_id=estudiante_id,
            desbloqueable_id=tema_id,
            puntos_gastados=0  # Gratis
        )
        
        # Activar automáticamente
        await self.gamification_repo.actualizar_personalizacion(
            estudiante_id,
            tema_activo_id=tema_id
        )
        
        item_response = DesbloqueableResponse(
            id=tema.id,
            categoria=tema.categoria.value,
            nombre=tema.nombre,
            descripcion=tema.descripcion,
            precio_puntos=tema.precio_puntos,
            nivel_minimo_requerido=tema.nivel_minimo_requerido,
            archivo_referencia=tema.archivo_referencia,
            orden=tema.orden,
            es_tema_inicial=tema.es_tema_inicial,
            poseido=True,
            fecha_compra=datetime.utcnow()
        )
        
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        
        return ComprarItemResponse(
            exito=True,
            mensaje=f"¡Bienvenido al tema {tema.nombre}!",
            item_comprado=item_response,
            puntos_gastados=0,
            saldo_nuevo=saldo
        )
    
    # ============================================
    # Recompensas Post-Sesión
    # ============================================
    
    async def get_recompensas_sesion(
        self,
        sesion_id: int,
        estudiante_id: int
    ) -> RecompensasSesionResponse:
        """
        Obtiene todas las recompensas de una sesión completada.
        
        Incluye puntos ganados y medallas nuevas.
        """
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        # Puntos
        puntos_ganados = sesion.puntos_ganados or 0
        desglose = sesion.desglose_puntos or {}
        
        # Saldo actual
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        
        # Verificar medallas nuevas
        medallas_nuevas_objs = await self.verificar_y_otorgar_medallas(estudiante_id)
        
        medallas_nuevas = [
            MedallaNuevaResponse(
                id=m.id,
                nombre=m.nombre,
                descripcion=m.descripcion,
                imagen_url=m.imagen_url
            )
            for m in medallas_nuevas_objs
        ]
        
        # Mensaje motivacional
        mensaje = self._generar_mensaje_motivacional(sesion, medallas_nuevas)
        
        return RecompensasSesionResponse(
            sesion_id=sesion_id,
            puntos_ganados=puntos_ganados,
            desglose_puntos=desglose,
            saldo_total=saldo,
            medallas_nuevas=medallas_nuevas,
            mensaje_motivacional=mensaje
        )
    
    def _generar_mensaje_motivacional(
        self,
        sesion: SesionPractica,
        medallas_nuevas: List[MedallaNuevaResponse]
    ) -> str:
        """Genera un mensaje motivacional según el desempeño."""
        if medallas_nuevas:
            return f"¡Increíble! Ganaste {len(medallas_nuevas)} medalla(s) nueva(s)."
        
        if sesion.es_practica_perfecta:
            return "¡Perfecto! No cometiste ningún error."
        
        if sesion.problemas_correctos and sesion.cantidad_problemas:
            precision = sesion.problemas_correctos / sesion.cantidad_problemas
            
            if precision >= 0.9:
                return "¡Excelente trabajo! Sigue así."
            elif precision >= 0.7:
                return "¡Buen esfuerzo! Cada día mejoras más."
            else:
                return "Sigue practicando, ¡tú puedes!"
        
        return "¡Gracias por practicar!"
