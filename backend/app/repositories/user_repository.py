"""
Repository para operaciones de base de datos de usuarios.

Autenticación basada en códigos únicos (codigo_estudiante, codigo_profesor).
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.user import Usuario, Estudiante, Profesor, TipoUsuario


class UserRepository:
    """Repository para operaciones CRUD de usuarios."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_codigo(self, codigo: str) -> Optional[Usuario]:
        """
        Busca un usuario por su código (estudiante o profesor).
        Para estudiantes puede haber varios con el mismo código en distintas
        organizaciones — devuelve el primero encontrado (la contraseña se
        verifica en auth_service usando get_all_students_by_codigo).
        """
        # Buscar como estudiante (puede haber más de uno → se resuelve en auth_service)
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.codigo_estudiante == codigo)
        )
        estudiante = result.scalars().first()
        if estudiante:
            return estudiante

        # Intentar buscar como profesor
        result = await self.db.execute(
            select(Profesor).where(Profesor.codigo_profesor == codigo)
        )
        return result.scalar_one_or_none()

    async def get_all_students_by_codigo(self, codigo: str) -> list[Estudiante]:
        """Devuelve TODOS los estudiantes con ese código (pueden ser de distintas orgs)."""
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.codigo_estudiante == codigo)
        )
        return list(result.scalars().all())
    
    async def get_by_id(self, user_id: int) -> Optional[Usuario]:
        """
        Busca un usuario por ID devolviendo el subtipo concreto (Estudiante o Profesor).
        Necesario para que isinstance() funcione correctamente en los guards de rol.
        """
        # Intentar como estudiante primero
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.id == user_id)
        )
        estudiante = result.scalar_one_or_none()
        if estudiante:
            return estudiante

        # Intentar como profesor
        result = await self.db.execute(
            select(Profesor).where(Profesor.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_student_by_codigo(self, codigo: str) -> Optional[Estudiante]:
        """Busca un estudiante específicamente por código."""
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.codigo_estudiante == codigo)
        )
        return result.scalar_one_or_none()
    
    async def get_teacher_by_codigo(self, codigo: str) -> Optional[Profesor]:
        """Busca un profesor específicamente por código."""
        result = await self.db.execute(
            select(Profesor).where(Profesor.codigo_profesor == codigo)
        )
        return result.scalar_one_or_none()
    
    async def create_student(
        self,
        codigo_estudiante: str,
        password_hash: str,
        nombre_completo: str,
        genero: str = "masculino",
        password_plain: Optional[str] = None,
        organizacion_id: Optional[int] = None,
        grado_academico: Optional[str] = None,
        anio_nacimiento: Optional[int] = None,
        mes_nacimiento: Optional[int] = None,
    ) -> Estudiante:
        """
        Crea un nuevo estudiante.

        Returns:
            Estudiante creado con ID asignado por la BD
        """
        estudiante = Estudiante(
            codigo_estudiante=codigo_estudiante,
            password_hash=password_hash,
            password_plain=password_plain,
            tipo_usuario=TipoUsuario.ESTUDIANTE,
            nombre_completo=nombre_completo,
            genero=genero,
            organizacion_id=organizacion_id,
            grado_academico=grado_academico,
            anio_nacimiento=anio_nacimiento,
            mes_nacimiento=mes_nacimiento,
            activo=True
        )

        self.db.add(estudiante)
        await self.db.commit()  # COMMIT en vez de flush
        await self.db.refresh(estudiante)

        return estudiante

    async def create_teacher(
        self,
        codigo_profesor: str,
        password_hash: str,
        nombre_completo: str,
        password_plain: Optional[str] = None,
        institucion: Optional[str] = None,
        organizacion_id: Optional[int] = None,
        grado_academico: Optional[str] = None,
    ) -> Profesor:
        """Crea un nuevo profesor."""
        profesor = Profesor(
            codigo_profesor=codigo_profesor,
            password_hash=password_hash,
            password_plain=password_plain,
            tipo_usuario=TipoUsuario.PROFESOR,
            nombre_completo=nombre_completo,
            institucion=institucion,
            organizacion_id=organizacion_id,
            grado_academico=grado_academico,
            activo=True
        )
        
        self.db.add(profesor)
        await self.db.commit()  # COMMIT en vez de flush
        await self.db.refresh(profesor)
        
        return profesor
    
    async def update_last_access(self, user_id: int) -> None:
        """Actualiza timestamp de último acceso."""
        from datetime import datetime
        
        user = await self.get_by_id(user_id)
        if user:
            user.ultimo_acceso = datetime.utcnow()
            await self.db.commit()  # COMMIT
    
    async def update_password(self, user_id: int, new_password_hash: str) -> None:
        """Actualiza la contraseña de un usuario."""
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            await self.db.commit()  # COMMIT
    
    async def deactivate_user(self, user_id: int) -> None:
        """Desactiva un usuario (soft delete)."""
        user = await self.get_by_id(user_id)
        if user:
            user.activo = False
            await self.db.commit()  # COMMIT
    
    async def activate_user(self, user_id: int) -> None:
        """Activa un usuario."""
        user = await self.get_by_id(user_id)
        if user:
            user.activo = True
            await self.db.commit()  # COMMIT
    
    async def codigo_estudiante_exists(self, codigo: str, organizacion_id: Optional[int] = None) -> bool:
        """
        Verifica si un código de estudiante ya existe.
        Si se pasa organizacion_id, verifica solo dentro de esa organización
        (un mismo código puede existir en distintas orgs).
        """
        query = select(Estudiante).where(Estudiante.codigo_estudiante == codigo)
        if organizacion_id is not None:
            query = query.where(Estudiante.organizacion_id == organizacion_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def codigo_profesor_exists(self, codigo: str) -> bool:
        """Verifica si un código de profesor ya existe."""
        result = await self.db.execute(
            select(Profesor).where(Profesor.codigo_profesor == codigo)
        )
        return result.scalar_one_or_none() is not None
