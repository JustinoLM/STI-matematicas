"""
Restablece las contraseñas de estudiantes y/o profesores.

Genera una contraseña aleatoria por usuario, guarda solo su hash Argon2 en la
BD y escribe las contraseñas nuevas en un CSV local (permisos 0600). Las
contraseñas NO se imprimen en pantalla.

Por defecto es una simulación (no modifica la BD). Usa --execute para aplicar.

Uso:
    cd backend
    # Producción: exportar antes la DATABASE_URL de Railway (no la guardes en .env)
    poetry run python scripts/reset_passwords.py --org-id 1 --salida credenciales_org1.csv
    poetry run python scripts/reset_passwords.py --org-id 1 --salida credenciales_org1.csv --execute

El CSV contiene claves en claro: entrégalo y bórralo. El patrón
credenciales_*.csv está en .gitignore.
"""

import argparse
import asyncio
import csv
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.organization import Organizacion  # noqa: E402
from app.models.user import Estudiante, Profesor  # noqa: E402

# Sin caracteres ambiguos (0/O, 1/l/I) para que sea fácil de dictar o copiar
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
LONGITUD = 10


def generar_password() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD))


async def main(args: argparse.Namespace) -> int:
    salida = Path(args.salida)
    if salida.exists():
        print(f"❌ {salida} ya existe; elige otro nombre para no sobrescribir claves.")
        return 1

    async with AsyncSessionLocal() as db:
        filas: list[tuple[str, str, str, str, str]] = []  # tipo, codigo, nombre, org, password
        usuarios = []

        if args.tipo in ("estudiantes", "todos"):
            q = select(Estudiante, Organizacion).outerjoin(
                Organizacion, Organizacion.id == Estudiante.organizacion_id
            )
            if args.org_id:
                q = q.where(Estudiante.organizacion_id == args.org_id)
            for est, org in (await db.execute(q)).all():
                usuarios.append((est, "estudiante", est.codigo_estudiante, org.nombre if org else ""))

        if args.tipo in ("profesores", "todos"):
            q = select(Profesor, Organizacion).outerjoin(
                Organizacion, Organizacion.id == Profesor.organizacion_id
            )
            if args.org_id:
                q = q.where(Profesor.organizacion_id == args.org_id)
            for prof, org in (await db.execute(q)).all():
                usuarios.append((prof, "profesor", prof.codigo_profesor, org.nombre if org else ""))

        if not usuarios:
            print("No hay usuarios que coincidan con el filtro.")
            return 0

        for user, tipo, codigo, org_nombre in usuarios:
            nueva = generar_password()
            filas.append((tipo, codigo, user.nombre_completo, org_nombre, nueva))
            if args.execute:
                user.password_hash = get_password_hash(nueva)

        resumen = {}
        for f in filas:
            resumen[f[0]] = resumen.get(f[0], 0) + 1
        detalle = ", ".join(f"{n} {t}(s)" for t, n in resumen.items())

        if not args.execute:
            await db.rollback()
            print(f"Simulación: se restablecerían {detalle}. No se modificó nada.")
            print("Agrega --execute para aplicar.")
            return 0

        await db.commit()

    fd = os.open(salida, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tipo", "codigo", "nombre_completo", "organizacion", "password_nueva"])
        w.writerows(filas)

    print(f"✅ Restablecidas {detalle}. Contraseñas escritas en {salida} (0600).")
    print("   Entrega las claves y borra el archivo.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org-id", type=int, help="Solo usuarios de esta organización")
    parser.add_argument("--tipo", choices=["estudiantes", "profesores", "todos"], default="todos")
    parser.add_argument("--salida", required=True, help="CSV de salida con las contraseñas nuevas")
    parser.add_argument("--execute", action="store_true", help="Aplicar los cambios (por defecto simula)")
    sys.exit(asyncio.run(main(parser.parse_args())))
