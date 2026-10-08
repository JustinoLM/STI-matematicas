"""
Evalúa el número de clústeres (k) de K-means con el método del codo (inercia) y
el coeficiente de silueta, por organización.

Usa las mismas features y la misma normalización que el entrenamiento real
(`MLService._extraer_features_perfil` + `StandardScaler`). Solo lee la BD: no
modifica perfiles ni modelos.

Uso:
    cd backend
    poetry run python scripts/evaluar_k_clustering.py                 # k = 3..6, todas las orgs
    poetry run python scripts/evaluar_k_clustering.py --org-id 1 --k-min 2 --k-max 8
    poetry run python scripts/evaluar_k_clustering.py --csv k_clustering.csv

No imprime datos personales: solo agregados por organización.
"""

import argparse
import asyncio
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.adaptive import PerfilEstudiante  # noqa: E402
from app.models.user import Estudiante  # noqa: E402
from app.services.ml_service import MLService  # noqa: E402


async def main(args: argparse.Namespace) -> int:
    ml = MLService()
    async with AsyncSessionLocal() as db:
        q = select(PerfilEstudiante, Estudiante.organizacion_id).join(
            Estudiante, Estudiante.id == PerfilEstudiante.estudiante_id
        )
        if args.org_id:
            q = q.where(Estudiante.organizacion_id == args.org_id)
        filas = (await db.execute(q)).all()

    por_org: dict = defaultdict(list)
    for perfil, org_id in filas:
        por_org[org_id].append(perfil)

    if not por_org:
        print("No hay perfiles que evaluar.")
        return 0

    salida = []
    for org_id, perfiles in sorted(por_org.items(), key=lambda kv: (kv[0] is None, kv[0])):
        res = ml.evaluar_k(perfiles, args.k_min, args.k_max)
        print(f"\nOrganización {org_id}: {len(perfiles)} perfiles")
        if not res:
            print("  Datos insuficientes (se necesitan perfiles con ≥ 3 sesiones y más muestras que k).")
            continue
        print("  k  muestras  inercia   silueta")
        mejor = max(res, key=lambda r: r["silueta"])
        for r in res:
            marca = "  ← mayor silueta" if r is mejor else ""
            print(f"  {r['k']}  {r['muestras']:>8}  {r['inercia']:>8.2f}  {r['silueta']:>7.3f}{marca}")
            salida.append({"org_id": org_id, **r})

    if args.csv and salida:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["org_id", "k", "muestras", "inercia", "silueta"])
            w.writeheader()
            w.writerows(salida)
        print(f"\nResultados guardados en {args.csv}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org-id", type=int)
    ap.add_argument("--k-min", type=int, default=3)
    ap.add_argument("--k-max", type=int, default=6)
    ap.add_argument("--csv")
    sys.exit(asyncio.run(main(ap.parse_args())))
