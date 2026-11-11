#!/usr/bin/env python3
"""nuevo_proyecto · crea la carpeta de un video de Flow con su estructura y plantillas.

Uso:
  python nuevo_proyecto.py <carpeta> [--nombre N] [--aspecto 9:16|16:9] [--duracion S] [--ejemplo] [--forzar]

--ejemplo copia el proyecto de muestra «cafe-origen» (biblia, anclas y plan completos) para estudiarlo o probar los scripts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ASSETS, utf8_stdout  # noqa: E402

CARPETAS = [
    "01-biblia", "02-anclas/personajes", "02-anclas/lugares", "02-anclas/productos", "02-anclas/fotogramas",
    "02-anclas/relevos", "03-storyboard", "04-prompts", "05-clips/raw", "05-clips/aprobados", "06-audio",
    "07-qc", "08-montaje",
]
PLANTILLAS = ["BRIEF.md", "01-biblia/biblia.json", "02-anclas/anclas.json", "03-storyboard/plan.json", "07-qc/REVISION.md"]


def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--nombre")
    ap.add_argument("--aspecto", default="9:16", choices=["9:16", "16:9"])
    ap.add_argument("--duracion", type=float, default=30)
    ap.add_argument("--ejemplo", action="store_true")
    ap.add_argument("--forzar", action="store_true", help="escribe aunque la carpeta tenga archivos")
    args = ap.parse_args(argv)

    raiz = Path(args.carpeta).resolve()
    if raiz.exists() and any(raiz.iterdir()) and not args.forzar:
        raise SystemExit(f"{raiz} ya tiene archivos. Usa otra carpeta o --forzar (no se borra nada, pero se sobrescriben las plantillas).")
    nombre = args.nombre or raiz.name
    for c in CARPETAS:
        (raiz / c).mkdir(parents=True, exist_ok=True)
    reemplazos = {"{{NOMBRE}}": nombre, "{{ASPECTO}}": args.aspecto, "{{FECHA}}": dt.date.today().isoformat(),
                  "{{DURACION}}": f"{args.duracion:g}"}
    for rel in PLANTILLAS:
        origen = ASSETS / "plantilla" / rel
        texto = origen.read_text(encoding="utf-8")
        for k, v in reemplazos.items():
            texto = texto.replace(k, v)
        (raiz / rel).write_text(texto, encoding="utf-8")
    if args.ejemplo:
        ej = ASSETS / "ejemplo" / "cafe-origen"
        for archivo in ej.rglob("*"):
            if archivo.is_file():
                dest = raiz / archivo.relative_to(ej)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archivo, dest)
    (raiz / "bitacora.jsonl").touch()
    print(f"Proyecto creado: {raiz}")
    print("Siguiente: completa BRIEF.md (puerta 1), después 01-biblia/biblia.json y")
    print(f"  python {Path(__file__).parent / 'flowprompt.py'} validar \"{raiz}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
