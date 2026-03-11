"""
Script para insertar datos iniciales (seed data).

Inserta:
- 6 Narrativas
- Desbloqueables completos (temas, fondos, colores, músicas, efectos)
  alineados 1:1 con los definidos en frontend/src/types/shop.ts
- Medallas básicas
- 1 Profesor de prueba + 3 Estudiantes de prueba

Uso:
    cd backend
    poetry run python scripts/seed_data.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    Narrativa,
    CategoriaDesbloqueable,
    CategoriaMedalla,
    Desbloqueable,
    Medalla,
    Profesor,
    Estudiante,
    Usuario,
    TipoUsuario,
    Organizacion,
    Grupo,
    EstudianteGrupo,
)


# ============================================================
# NARRATIVAS
# ============================================================

async def seed_narrativas(db: AsyncSession):
    """Insertar las 6 narrativas del sistema."""
    result = await db.execute(select(Narrativa))
    if result.scalars().first():
        print("  → Narrativas ya existen, omitiendo.")
        return

    narrativas = [
        {"nombre": "Piratas",             "descripcion": "Aventuras en alta mar, tesoros y mapas",       "icono_url": "/assets/narrativas/piratas.svg"},
        {"nombre": "Astronautas",         "descripcion": "Exploración espacial, planetas y estrellas",   "icono_url": "/assets/narrativas/astronautas.svg"},
        {"nombre": "Magos",               "descripcion": "Magia, hechizos y pociones mágicas",           "icono_url": "/assets/narrativas/magos.svg"},
        {"nombre": "Caballeros",          "descripcion": "Castillos, dragones y espadas legendarias",    "icono_url": "/assets/narrativas/caballeros.svg"},
        {"nombre": "Cowboys",             "descripcion": "Oeste salvaje, caballos y desafíos del rancho","icono_url": "/assets/narrativas/cowboys.svg"},
        {"nombre": "Princesas Inventoras","descripcion": "Ciencia, invención y creatividad",             "icono_url": "/assets/narrativas/princesas.svg"},
    ]
    for data in narrativas:
        db.add(Narrativa(**data))
    await db.commit()
    print("  ✓ 6 narrativas insertadas")


# ============================================================
# DESBLOQUEABLES
# Alineados con frontend/src/types/shop.ts
# archivo_referencia = ID del frontend (ej: "tema-piratas")
# ============================================================

async def seed_desbloqueables(db: AsyncSession):
    """Insertar catálogo completo de desbloqueables."""
    result = await db.execute(select(Desbloqueable))
    if result.scalars().first():
        print("  → Desbloqueables ya existen, omitiendo.")
        return

    items = []

    # ----------------------------------------------------------
    # TEMAS (7)
    # ----------------------------------------------------------
    temas = [
        {"nombre": "Clásico",               "descripcion": "El tema predeterminado. Limpio y sin distracciones.",      "precio_puntos": 0,   "nivel_minimo_requerido": 1, "archivo_referencia": "tema-default",    "es_tema_inicial": True,  "orden": 1},
        {"nombre": "Piratas de los Mares",  "descripcion": "Aventuras en alta mar. ¡Arrr, matemático!",                "precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-piratas",    "es_tema_inicial": True,  "orden": 2},
        {"nombre": "Astronautas Galácticos","descripcion": "Explora el universo resolviendo problemas.",               "precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-astronautas","es_tema_inicial": True,  "orden": 3},
        {"nombre": "Magos de la Academia",  "descripcion": "Usa la magia de los números para hechizar problemas.",    "precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-magos",      "es_tema_inicial": True,  "orden": 4},
        {"nombre": "Caballeros del Reino",  "descripcion": "Defiende el castillo con tus habilidades matemáticas.",   "precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-caballeros", "es_tema_inicial": True,  "orden": 5},
        {"nombre": "Vaqueros del Oeste",    "descripcion": "Domina el salvaje oeste de los decimales.",                "precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-vaqueros",   "es_tema_inicial": True,  "orden": 6},
        {"nombre": "Princesas Inventoras",  "descripcion": "Inventa soluciones brillantes con ciencia y matemáticas.","precio_puntos": 500, "nivel_minimo_requerido": 1, "archivo_referencia": "tema-princesas",  "es_tema_inicial": True,  "orden": 7},
    ]
    for t in temas:
        items.append(Desbloqueable(categoria=CategoriaDesbloqueable.TEMA, **t))

    # ----------------------------------------------------------
    # FONDOS (21 = 3 genéricos + 18 temáticos)
    # ----------------------------------------------------------
    fondos = [
        # Genéricos
        {"nombre": "Fondo Cuadrícula",      "descripcion": "Fondo de cuadrícula clásica para enfocarse.",             "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-cuadricula",    "orden": 1},
        {"nombre": "Degradado Azul",        "descripcion": "Suave degradado azul, tranquilo y relajante.",            "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-degradado-azul","orden": 2},
        {"nombre": "Noche Estrellada",      "descripcion": "Cielo nocturno lleno de estrellas.",                       "precio_puntos": 75,  "nivel_minimo_requerido": 2, "archivo_referencia": "fondo-noche",         "orden": 3},
        # Piratas
        {"nombre": "Puerto Pirata",         "descripcion": "Un muelle con barcos piratas al amanecer.",               "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-piratas-1",     "orden": 4},
        {"nombre": "Mar Abierto",           "descripcion": "Océano infinito bajo el sol del mediodía.",               "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-piratas-2",     "orden": 5},
        {"nombre": "Isla del Tesoro",       "descripcion": "Una isla exótica con palmas y cofres escondidos.",         "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-piratas-3",     "orden": 6},
        # Astronautas
        {"nombre": "Estación Espacial",     "descripcion": "Vista desde una estación orbital.",                       "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-astronautas-1", "orden": 7},
        {"nombre": "Superficie Lunar",      "descripcion": "Caminando por la luna con la Tierra al fondo.",           "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-astronautas-2", "orden": 8},
        {"nombre": "Nebulosa Colorida",     "descripcion": "Una nebulosa llena de colores y estrellas.",              "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-astronautas-3", "orden": 9},
        # Magos
        {"nombre": "Biblioteca Mágica",     "descripcion": "Estantes infinitos de libros de hechizos.",               "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-magos-1",       "orden": 10},
        {"nombre": "Taller del Mago",       "descripcion": "Pociones y experimentos mágicos en curso.",               "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-magos-2",       "orden": 11},
        {"nombre": "Bosque Encantado",      "descripcion": "Árboles que brillan con magia antigua.",                  "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-magos-3",       "orden": 12},
        # Caballeros
        {"nombre": "Gran Salón del Castillo","descripcion": "Salón principal con estandartes y antorchas.",           "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-caballeros-1",  "orden": 13},
        {"nombre": "Campos de Torneo",      "descripcion": "Arena de torneos con público y banderas.",                "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-caballeros-2",  "orden": 14},
        {"nombre": "Montañas del Norte",    "descripcion": "Paisaje épico de montañas nevadas con un dragón.",        "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-caballeros-3",  "orden": 15},
        # Vaqueros
        {"nombre": "Pueblo del Oeste",      "descripcion": "Calle principal de un pueblo polvoriento.",               "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-vaqueros-1",    "orden": 16},
        {"nombre": "Gran Pradería",         "descripcion": "Llanura abierta bajo un cielo naranja.",                  "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-vaqueros-2",    "orden": 17},
        {"nombre": "Rancho al Atardecer",   "descripcion": "Un rancho tranquilo con caballos al fondo.",              "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-vaqueros-3",    "orden": 18},
        # Princesas Inventoras
        {"nombre": "Laboratorio Real",      "descripcion": "Laboratorio lleno de inventos y mecanismos.",             "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-princesas-1",   "orden": 19},
        {"nombre": "Jardín de Cristal",     "descripcion": "Un jardín futurista con plantas de cristal.",             "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-princesas-2",   "orden": 20},
        {"nombre": "Torre Observatorio",    "descripcion": "Torre astronómica con telescopios gigantes.",              "precio_puntos": 75,  "nivel_minimo_requerido": 1, "archivo_referencia": "fondo-princesas-3",   "orden": 21},
    ]
    for f in fondos:
        items.append(Desbloqueable(categoria=CategoriaDesbloqueable.FONDO, **f))

    # ----------------------------------------------------------
    # COLORES (12 = 6 básicos + 6 premium)
    # ----------------------------------------------------------
    colores = [
        {"nombre": "Azul Clásico",     "descripcion": "El azul tranquilo del tema predeterminado.",   "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-azul-clasico",    "orden": 1},
        {"nombre": "Verde Esmeralda",  "descripcion": "Verde vivo que denota crecimiento.",            "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-verde-esmeralda", "orden": 2},
        {"nombre": "Rojo Carmesí",     "descripcion": "Rojo intenso con energía y pasión.",            "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-rojo-carmesi",    "orden": 3},
        {"nombre": "Naranja Solar",    "descripcion": "Naranja cálido como el sol del mediodía.",      "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-naranja-solar",   "orden": 4},
        {"nombre": "Violeta Místico",  "descripcion": "Púrpura profundo lleno de misterio.",           "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-violeta-mistico", "orden": 5},
        {"nombre": "Turquesa",         "descripcion": "Azul verdoso refrescante como el mar.",         "precio_puntos": 50,  "nivel_minimo_requerido": 1, "archivo_referencia": "color-turquesa",        "orden": 6},
        {"nombre": "Dorado Real",      "descripcion": "Dorado brillante, el color de los campeones.",  "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "color-dorado-real",     "orden": 7},
        {"nombre": "Rosa Sakura",      "descripcion": "Rosa suave y delicado como flores de cerezo.",  "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "color-rosa-sakura",     "orden": 8},
        {"nombre": "Azul Medianoche",  "descripcion": "Azul profundo del cielo nocturno.",              "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "color-azul-medianoche", "orden": 9},
        {"nombre": "Verde Lima",       "descripcion": "Verde eléctrico lleno de energía.",              "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "color-verde-lima",      "orden": 10},
        {"nombre": "Marrón Cobre",     "descripcion": "Cobre cálido con un toque retro.",               "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "color-marron-cobre",    "orden": 11},
        {"nombre": "Arcoíris",         "descripcion": "Todos los colores del arcoíris en degradado.",   "precio_puntos": 150, "nivel_minimo_requerido": 3, "archivo_referencia": "color-arcoiris",        "orden": 12},
    ]
    for c in colores:
        items.append(Desbloqueable(categoria=CategoriaDesbloqueable.COLOR, **c))

    # ----------------------------------------------------------
    # MÚSICAS (18 = 3 por tema narrativo)
    # ----------------------------------------------------------
    musicas = [
        # Piratas
        {"nombre": "Melodía del Mar",        "descripcion": "Acordeón suave con olas de fondo.",                 "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-piratas-tranquila",     "orden": 1},
        {"nombre": "¡Al Abordaje!",          "descripcion": "Ritmo de tambores y cuerdas para la batalla.",      "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-piratas-energetica",    "orden": 2},
        {"nombre": "Puerto Brumoso",         "descripcion": "Niebla marina con gaviotas y cañones lejanos.",     "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-piratas-ambiente",      "orden": 3},
        # Astronautas
        {"nombre": "Galaxia Tranquila",      "descripcion": "Sintetizadores suaves en el silencio del espacio.", "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-astronautas-tranquila", "orden": 4},
        {"nombre": "Propulsores al Máximo",  "descripcion": "Ritmo electrónico para el despegue.",               "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-astronautas-energetica","orden": 5},
        {"nombre": "Estación Orbital",       "descripcion": "Zumbido de la estación y señales lejanas.",         "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-astronautas-ambiente",  "orden": 6},
        # Magos
        {"nombre": "Sala de Estudio",        "descripcion": "Clavicémbalo suave para concentrarse.",             "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-magos-tranquila",       "orden": 7},
        {"nombre": "Hechizo Mayor",          "descripcion": "Orquesta épica cuando el hechizo cobra vida.",       "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-magos-energetica",      "orden": 8},
        {"nombre": "Bosque Encantado",       "descripcion": "Grillos mágicos y viento entre ramas antiguas.",    "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-magos-ambiente",        "orden": 9},
        # Caballeros
        {"nombre": "Balada del Caballero",   "descripcion": "Laúd medieval para un héroe en reposo.",            "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-caballeros-tranquila",  "orden": 10},
        {"nombre": "Marcha de la Victoria",  "descripcion": "Fanfarria de trompetas antes del torneo.",          "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-caballeros-energetica", "orden": 11},
        {"nombre": "Viento del Castillo",    "descripcion": "Viento entre almenas y pájaros al amanecer.",       "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-caballeros-ambiente",   "orden": 12},
        # Vaqueros
        {"nombre": "Guitarra del Rancho",    "descripcion": "Guitarra acústica bajo las estrellas del desierto.","precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-vaqueros-tranquila",    "orden": 13},
        {"nombre": "Duelo al Mediodía",      "descripcion": "Silbido icónico y guitarra rítmica del duelo.",     "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-vaqueros-energetica",   "orden": 14},
        {"nombre": "Pradera al Atardecer",   "descripcion": "Grillos, viento y caballos al galope lejano.",      "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-vaqueros-ambiente",     "orden": 15},
        # Princesas Inventoras
        {"nombre": "Sinfonía del Lab",       "descripcion": "Piano suave con tics de mecanismos.",               "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-princesas-tranquila",   "orden": 16},
        {"nombre": "Máquina de Ideas",       "descripcion": "Ritmo mecánico y electrónico lleno de energía.",    "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-princesas-energetica",  "orden": 17},
        {"nombre": "Jardín Automático",      "descripcion": "Sonidos de inventos, ruedas y pájaros mecánicos.",  "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "musica-princesas-ambiente",    "orden": 18},
    ]
    for m in musicas:
        items.append(Desbloqueable(categoria=CategoriaDesbloqueable.MUSICA, **m))

    # ----------------------------------------------------------
    # EFECTOS (5)
    # ----------------------------------------------------------
    efectos = [
        {"nombre": "Lluvia de Estrellas", "descripcion": "Estrellas caen cuando aciertas.",                 "precio_puntos": 100, "nivel_minimo_requerido": 1, "archivo_referencia": "efecto-estrellas", "orden": 1},
        {"nombre": "Confeti Mágico",      "descripcion": "Confeti de colores explosivo al acertar.",        "precio_puntos": 100, "nivel_minimo_requerido": 2, "archivo_referencia": "efecto-confeti",   "orden": 2},
        {"nombre": "Fuegos Artificiales", "descripcion": "Explosión de fuegos artificiales en cada logro.", "precio_puntos": 150, "nivel_minimo_requerido": 3, "archivo_referencia": "efecto-fuegos",    "orden": 3},
        {"nombre": "Rayo de Poder",       "descripcion": "Un rayo eléctrico cruza la pantalla al acertar.", "precio_puntos": 150, "nivel_minimo_requerido": 4, "archivo_referencia": "efecto-rayo",      "orden": 4},
        {"nombre": "Aurora Boreal",       "descripcion": "Luces danzantes del norte iluminan el fondo.",    "precio_puntos": 150, "nivel_minimo_requerido": 5, "archivo_referencia": "efecto-aurora",    "orden": 5},
    ]
    for e in efectos:
        items.append(Desbloqueable(categoria=CategoriaDesbloqueable.EFECTO, **e))

    for item in items:
        db.add(item)
    await db.commit()
    print(f"  ✓ {len(items)} desbloqueables ({len(temas)} temas, {len(fondos)} fondos, {len(colores)} colores, {len(musicas)} músicas, {len(efectos)} efectos)")


# ============================================================
# MEDALLAS
# ============================================================

async def seed_medallas(db: AsyncSession):
    """Insertar (o reemplazar) el catálogo oficial de medallas."""
    # Borrar medallas existentes para poder re-ejecutar el seed limpiamente
    existing = await db.execute(select(Medalla))
    existing_medals = existing.scalars().all()
    if existing_medals:
        for m in existing_medals:
            await db.delete(m)
        await db.flush()
        print(f"  → {len(existing_medals)} medallas anteriores eliminadas.")

    A = CategoriaMedalla.APRENDIZAJE
    V = CategoriaMedalla.VOLUMEN
    E = CategoriaMedalla.EXPLORACION
    D = CategoriaMedalla.DESAFIOS

    medallas = [
        # ── Aprendizaje: Progresión general (5) ────────────────────────────
        {
            "nombre": "Principiante",
            "descripcion": "Completaste el diagnóstico inicial. ¡Bienvenido al viaje!",
            "categoria": A,
            "criterio": {"tipo": "diagnostico"},
            "imagen_url": "🌱",
            "orden": 1,
        },
        {
            "nombre": "Aprendiz",
            "descripcion": "Alcanzaste el Nivel 2. Vas aprendiendo bien.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "general", "nivel": 2},
            "imagen_url": "📗",
            "orden": 2,
        },
        {
            "nombre": "Competente",
            "descripcion": "Nivel 3 alcanzado. ¡Ya dominas las bases!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "general", "nivel": 3},
            "imagen_url": "📘",
            "orden": 3,
        },
        {
            "nombre": "Avanzado",
            "descripcion": "Nivel 4 alcanzado. Estás muy cerca de la cima.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "general", "nivel": 4},
            "imagen_url": "📙",
            "orden": 4,
        },
        {
            "nombre": "Maestro",
            "descripcion": "Nivel 5 alcanzado. ¡Eres un maestro de las matemáticas!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "general", "nivel": 5},
            "imagen_url": "🏆",
            "orden": 5,
        },
        # ── Aprendizaje: Dominio por operación (4) ──────────────────────────
        {
            "nombre": "Sumador",
            "descripcion": "Alcanzaste Nivel 3 en sumas de decimales.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "suma", "nivel": 3},
            "imagen_url": "➕",
            "orden": 6,
        },
        {
            "nombre": "Restador",
            "descripcion": "Alcanzaste Nivel 3 en restas de decimales.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "resta", "nivel": 3},
            "imagen_url": "➖",
            "orden": 7,
        },
        {
            "nombre": "Multiplicador",
            "descripcion": "Alcanzaste Nivel 3 en multiplicación de decimales.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "multiplicacion", "nivel": 3},
            "imagen_url": "✖️",
            "orden": 8,
        },
        {
            "nombre": "Divisor",
            "descripcion": "Alcanzaste Nivel 3 en división de decimales.",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "division", "nivel": 3},
            "imagen_url": "➗",
            "orden": 9,
        },
        {
            "nombre": "Matemático Completo",
            "descripcion": "Nivel 3 en todas las operaciones. ¡Dominio total!",
            "categoria": A,
            "criterio": {"tipo": "nivel_todas", "nivel": 3},
            "imagen_url": "🧮",
            "orden": 10,
        },
        # ── Volumen (3) ──────────────────────────────────────────────────────
        {
            "nombre": "100 Club",
            "descripcion": "Resolviste 100 problemas. ¡El esfuerzo da frutos!",
            "categoria": V,
            "criterio": {"tipo": "volumen", "cantidad": 100},
            "imagen_url": "💯",
            "orden": 11,
        },
        {
            "nombre": "500 Club",
            "descripcion": "500 problemas resueltos. ¡Eres increíble!",
            "categoria": V,
            "criterio": {"tipo": "volumen", "cantidad": 500},
            "imagen_url": "🔥",
            "orden": 12,
        },
        {
            "nombre": "1000 Club",
            "descripcion": "1000 problemas resueltos. ¡Leyenda!",
            "categoria": V,
            "criterio": {"tipo": "volumen", "cantidad": 1000},
            "imagen_url": "💎",
            "orden": 13,
        },
        # ── Exploración (2) ──────────────────────────────────────────────────
        {
            "nombre": "Explorador",
            "descripcion": "Completaste una práctica con cada uno de los 6 temas disponibles.",
            "categoria": E,
            "criterio": {"tipo": "exploracion_temas", "temas_requeridos": 6},
            "imagen_url": "🗺️",
            "orden": 14,
        },
        {
            "nombre": "Coleccionista",
            "descripcion": "Compraste 20 items diferentes en la tienda.",
            "categoria": E,
            "criterio": {"tipo": "coleccionista", "cantidad": 20},
            "imagen_url": "🛍️",
            "orden": 15,
        },
        # ── Desafíos (3) ─────────────────────────────────────────────────────
        {
            "nombre": "Colaborador",
            "descripcion": "Participaste en 1 desafío grupal completado.",
            "categoria": D,
            "criterio": {"tipo": "desafio_grupal", "cantidad": 1},
            "imagen_url": "🤝",
            "orden": 16,
        },
        {
            "nombre": "Cooperador",
            "descripcion": "Participaste en 3 desafíos grupales completados.",
            "categoria": D,
            "criterio": {"tipo": "desafio_grupal", "cantidad": 3},
            "imagen_url": "🫂",
            "orden": 17,
        },
        {
            "nombre": "Líder de Equipo",
            "descripcion": "Participaste en 5 desafíos grupales completados. ¡Un verdadero líder!",
            "categoria": D,
            "criterio": {"tipo": "desafio_grupal", "cantidad": 5},
            "imagen_url": "👑",
            "orden": 18,
        },
        # ── Secretas (7) ─────────────────────────────────────────────────────
        # Una por operación al llegar a Nivel 5
        {
            "nombre": "Suma Perfeccionada",
            "descripcion": "Alcanzaste el Nivel 5 en sumas de decimales. ¡Eres imparable!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "suma", "nivel": 5},
            "imagen_url": "➕",
            "orden": 19,
            "es_secreta": True,
        },
        {
            "nombre": "Resta Perfeccionada",
            "descripcion": "Alcanzaste el Nivel 5 en restas de decimales. ¡Maestría total!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "resta", "nivel": 5},
            "imagen_url": "➖",
            "orden": 20,
            "es_secreta": True,
        },
        {
            "nombre": "Multiplicación Perfeccionada",
            "descripcion": "Alcanzaste el Nivel 5 en multiplicación de decimales. ¡Extraordinario!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "multiplicacion", "nivel": 5},
            "imagen_url": "✖️",
            "orden": 21,
            "es_secreta": True,
        },
        {
            "nombre": "División Perfeccionada",
            "descripcion": "Alcanzaste el Nivel 5 en división de decimales. ¡Increíble dominio!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "division", "nivel": 5},
            "imagen_url": "➗",
            "orden": 22,
            "es_secreta": True,
        },
        # Nivel 5 global
        {
            "nombre": "¿Eres un profesor?",
            "descripcion": "Alcanzaste el Nivel 5 global. ¡Tu conocimiento no tiene límites!",
            "categoria": A,
            "criterio": {"tipo": "nivel", "operacion": "general", "nivel": 5},
            "imagen_url": "🌟",
            "orden": 23,
            "es_secreta": True,
        },
        # Coleccionista total de la tienda
        {
            "nombre": "¡Todo es Mío!",
            "descripcion": "Compraste absolutamente todos los items de la tienda. ¡El dueño del lugar!",
            "categoria": E,
            "criterio": {"tipo": "coleccionista", "cantidad": 63},
            "imagen_url": "🛒",
            "orden": 24,
            "es_secreta": True,
        },
        # Racha perfecta
        {
            "nombre": "Perfeccionista",
            "descripcion": "Lograste una racha de 50 sesiones perfectas consecutivas. ¡Leyenda!",
            "categoria": V,
            "criterio": {"tipo": "racha", "cantidad": 50},
            "imagen_url": "🚀",
            "orden": 25,
            "es_secreta": True,
        },
    ]

    for data in medallas:
        db.add(Medalla(**data))
    await db.commit()
    print(f"  ✓ {len(medallas)} medallas insertadas ({sum(1 for m in medallas if m.get('es_secreta'))} secretas, {sum(1 for m in medallas if not m.get('es_secreta'))} visibles)")


# ============================================================
# ORGANIZACIONES DE PRUEBA
# ============================================================

async def seed_organizaciones(db: AsyncSession):
    """Insertar 2 organizaciones de prueba."""
    result = await db.execute(select(Organizacion))
    if result.scalars().first():
        print("  → Organizaciones ya existen, omitiendo.")
        return

    orgs = [
        Organizacion(
            nombre="Escuela Primaria Central",
            codigo="EPC001",
            descripcion="Organización de prueba para tesis - colegio principal",
            ciudad="Ciudad de Panamá",
            pais="Panamá",
        ),
        Organizacion(
            nombre="Colegio San José",
            codigo="CSJ001",
            descripcion="Segunda organización de prueba - colegio externo",
            ciudad="David",
            pais="Panamá",
        ),
    ]
    for org in orgs:
        db.add(org)
    await db.commit()
    print("  ✓ 2 organizaciones insertadas (EPC001, CSJ001)")


# ============================================================
# USUARIOS DE PRUEBA
# ============================================================

async def seed_usuarios_prueba(db: AsyncSession):
    """Insertar 1 profesor y 3 estudiantes de prueba."""
    result = await db.execute(select(Usuario))
    if result.scalars().first():
        print("  → Usuarios ya existen, omitiendo.")
        return

    # Obtener organización principal para asignar al profesor
    org_result = await db.execute(select(Organizacion).where(Organizacion.codigo == "EPC001"))
    org_principal = org_result.scalar_one_or_none()

    # Profesor
    db.add(Profesor(
        tipo_usuario=TipoUsuario.PROFESOR,
        password_hash=get_password_hash("profesor123"),
        activo=True,
        codigo_profesor="PROF001",
        nombre_completo="María García",
        institucion="Escuela Primaria Central",
        email="profesor@sti.edu",
        organizacion_id=org_principal.id if org_principal else None,
    ))

    # Estudiantes
    estudiantes_data = [
        {"codigo_estudiante": "EST001", "nombre_completo": "Juan Pérez"},
        {"codigo_estudiante": "EST002", "nombre_completo": "Ana Martínez"},
        {"codigo_estudiante": "EST003", "nombre_completo": "Carlos López"},
    ]
    for data in estudiantes_data:
        db.add(Estudiante(
            tipo_usuario=TipoUsuario.ESTUDIANTE,
            password_hash=get_password_hash("estudiante123"),
            activo=True,
            email=None,
            organizacion_id=org_principal.id if org_principal else None,
            **data,
        ))

    await db.commit()
    print("  ✓ 1 profesor (PROF001) y 3 estudiantes (EST001-003) con password 'estudiante123'")
    if org_principal:
        print(f"    Asignados a organización: {org_principal.nombre}")


# ============================================================
# GRUPOS DE PRUEBA
# ============================================================

async def seed_grupos(db: AsyncSession):
    """Insertar 1 grupo de prueba con los 3 estudiantes asignados."""
    result = await db.execute(select(Grupo))
    if result.scalars().first():
        print("  → Grupos ya existen, omitiendo.")
        return

    # Obtener profesor PROF001
    prof_result = await db.execute(select(Profesor).where(Profesor.codigo_profesor == "PROF001"))
    profesor = prof_result.scalar_one_or_none()
    if not profesor:
        print("  ⚠ Profesor PROF001 no encontrado, omitiendo grupos.")
        return

    # Crear grupo
    grupo = Grupo(
        nombre="5to Grado A",
        codigo_grupo="5GA-2026",
        profesor_id=profesor.id,
        activo=True,
    )
    db.add(grupo)
    await db.flush()  # Para obtener grupo.id

    # Obtener estudiantes EST001-003 y asignarlos al grupo
    codigos = ["EST001", "EST002", "EST003"]
    est_result = await db.execute(
        select(Estudiante).where(Estudiante.codigo_estudiante.in_(codigos))
    )
    estudiantes = est_result.scalars().all()

    for est in estudiantes:
        db.add(EstudianteGrupo(estudiante_id=est.id, grupo_id=grupo.id))

    await db.commit()
    print(f"  ✓ Grupo '5to Grado A' (5GA-2026) creado con {len(estudiantes)} estudiantes")


# ============================================================
# MAIN
# ============================================================

async def main():
    """Ejecutar todos los seeds."""
    print()
    print("=" * 60)
    print("INSERTANDO DATOS INICIALES (SEED DATA)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        print("\n[1/6] Narrativas...")
        await seed_narrativas(db)

        print("\n[2/6] Desbloqueables (tienda)...")
        await seed_desbloqueables(db)

        print("\n[3/6] Medallas...")
        await seed_medallas(db)

        print("\n[4/6] Organizaciones de prueba...")
        await seed_organizaciones(db)

        print("\n[5/6] Usuarios de prueba...")
        await seed_usuarios_prueba(db)

        print("\n[6/6] Grupos de prueba...")
        await seed_grupos(db)

    print()
    print("=" * 60)
    print("SEED COMPLETADO")
    print()
    print("  Credenciales de prueba:")
    print("  Profesor   → PROF001      / profesor123")
    print("  Estudiante → EST001       / estudiante123")
    print("  Estudiante → EST002       / estudiante123")
    print("  Estudiante → EST003       / estudiante123")
    print("  Grupo      → 5to Grado A  (código: 5GA-2026)")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
