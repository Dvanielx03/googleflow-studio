#!/usr/bin/env python3
"""bitacora · registro de generaciones, estadísticas y biblioteca de patrones.

Uso:
  python bitacora.py registrar <proyecto> --plano P01 --resultado aprobado|corregido|rechazado
                     [--tipo video|imagen] [--modo M] [--modelo M] [--prompt-id ID] [--version N]
                     [--defectos identidad,manos] [--nota "..."] [--puntos N] [--fecha ISO] [--archivo ruta]
  python bitacora.py resumen <proyecto> | --todos <carpeta-con-proyectos>
  python bitacora.py promover --tipo patron|antipatron --titulo T --contexto C --tecnica T --evidencia E

Lo que no se pasa se toma del plan y de 04-prompts/prompts.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ASSETS, RUTAS, Proyecto, utf8_stdout  # noqa: E402

DEFECTOS = {"identidad", "manos", "deformacion", "producto", "lugar", "movimiento", "continuidad",
            "storyboard", "texto", "audio", "cortes", "tecnico"}
RESULTADOS = {"aprobado", "corregido", "rechazado"}
PATRONES = ASSETS / "patrones" / "patrones-probados.md"


def registrar(args) -> int:
    p = Proyecto(args.proyecto)
    pl = p.plano(args.plano) or {}
    anc = p.ancla(args.plano) or {}
    defectos = [d.strip() for d in (args.defectos or "").split(",") if d.strip()]
    desconocidos = [d for d in defectos if d not in DEFECTOS]
    if desconocidos:
        raise SystemExit(f"Defectos no normalizados: {desconocidos}. Usa: {', '.join(sorted(DEFECTOS))}")
    if args.resultado not in RESULTADOS:
        raise SystemExit(f"--resultado debe ser {', '.join(sorted(RESULTADOS))}")
    prompt = {}
    ruta_prompts = p.ruta("prompts")
    pid = args.prompt_id or args.plano
    if ruta_prompts.exists():
        prompt = json.loads(ruta_prompts.read_text(encoding="utf-8")).get("prompts", {}).get(pid, {})
    tipo = args.tipo or ("video" if pl else "imagen")
    momento = (dt.datetime.fromisoformat(args.fecha.replace("Z", "+00:00")) if args.fecha else dt.datetime.now()).astimezone()
    entrada = {
        "fecha": momento.replace(tzinfo=None).isoformat(timespec="seconds"),
        "fecha_utc": momento.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "proyecto": p.plan.get("proyecto") or p.raiz.name,
        "plano": args.plano,
        "tipo": tipo,
        "modo": args.modo or pl.get("modo") or ("imagen" if anc else None),
        "modelo": args.modelo or pl.get("modelo") or anc.get("modelo"),
        "duracion": pl.get("duracion"),
        "salidas": pl.get("salidas") or anc.get("salidas"),
        "anclas": pl.get("anclas") or anc.get("padres") or [],
        "prompt_id": pid,
        "prompt_version": args.version or prompt.get("version"),
        "prompt_huella": prompt.get("huella"),
        "prompt": prompt.get("texto"),
        "ajustes": prompt.get("ajustes"),
        "resultado": args.resultado,
        "defectos": defectos,
        "nota": args.nota,
        "creditos": args.creditos,
        "archivo": args.archivo,
    }
    ruta = p.raiz / RUTAS["bitacora"]
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    print(f"Registrado {args.plano} · {entrada['modo']} · {entrada['modelo']} · {args.resultado}"
          + (f" · defectos: {', '.join(defectos)}" if defectos else "") + f"\n→ {ruta}")
    return 0


def leer(rutas: list[Path]) -> list[dict]:
    filas = []
    for r in rutas:
        for n, linea in enumerate(r.read_text(encoding="utf-8").splitlines(), 1):
            if linea.strip():
                try:
                    filas.append(json.loads(linea))
                except json.JSONDecodeError:
                    print(f"  (línea {n} de {r} ilegible, se omite)")
    return filas


def resumen(args) -> int:
    if args.todos:
        rutas = sorted(Path(args.todos).glob(f"**/{RUTAS['bitacora']}"))
    else:
        rutas = [Path(args.proyecto) / RUTAS["bitacora"]]
    rutas = [r for r in rutas if r.exists()]
    if not rutas:
        print("No hay bitácoras todavía.")
        return 0
    filas = leer(rutas)
    print(f"{len(filas)} generaciones en {len(rutas)} bitácora(s)\n")
    grupos: dict[tuple, list] = defaultdict(list)
    for f in filas:
        grupos[(f.get("tipo"), f.get("modo"), f.get("modelo"))].append(f)
    print(f"{'tipo':7} {'modo':14} {'modelo':16} {'gen':>4} {'ok':>4} {'ok%':>5} {'1ª':>4} {'int/ok':>7} {'créditos':>9}")
    for (tipo, modo, modelo), fs in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        ok = [f for f in fs if f.get("resultado") in ("aprobado", "corregido")]
        # intentos por plano hasta aprobarlo y aprobados a la primera
        por_plano: dict[tuple, list] = defaultdict(list)
        for f in fs:
            por_plano[(f.get("proyecto"), f.get("plano"))].append(f)
        primera = sum(1 for v in por_plano.values() if v and v[0].get("resultado") in ("aprobado", "corregido"))
        planos_ok = [v for v in por_plano.values() if any(x.get("resultado") in ("aprobado", "corregido") for x in v)]
        intentos = [next(i for i, x in enumerate(v, 1) if x.get("resultado") in ("aprobado", "corregido")) for v in planos_ok]
        cred = sum(f.get("creditos") or 0 for f in fs)
        print(f"{str(tipo):7} {str(modo):14} {str(modelo):16} {len(fs):>4} {len(ok):>4} {100 * len(ok) / len(fs):>4.0f}% "
              f"{primera:>4} {(sum(intentos) / len(intentos) if intentos else 0):>7.1f} {cred:>9}")
    defectos = Counter(d for f in filas for d in f.get("defectos") or [])
    if defectos:
        print("\nDefectos más frecuentes: " + ", ".join(f"{d} ({n})" for d, n in defectos.most_common(8)))
    por_def_modo = defaultdict(Counter)
    for f in filas:
        for d in f.get("defectos") or []:
            por_def_modo[d][f"{f.get('modo')}/{f.get('modelo')}"] += 1
    for d, c in sorted(por_def_modo.items(), key=lambda kv: -sum(kv[1].values()))[:5]:
        print(f"  {d}: " + ", ".join(f"{k} {n}" for k, n in c.most_common(3)))
    total_cred = sum(f.get("creditos") or 0 for f in filas)
    aprobados = {(f.get("proyecto"), f.get("plano")) for f in filas if f.get("resultado") in ("aprobado", "corregido") and f.get("tipo") == "video"}
    if aprobados and total_cred:
        cred_video = sum(f.get("creditos") or 0 for f in filas if f.get("tipo") == "video")
        print(f"\nCréditos de video por plano aprobado: {cred_video / len(aprobados):.1f}")
    notas = [f for f in filas if f.get("nota")]
    if notas:
        print("\nÚltimas notas:")
        for f in notas[-6:]:
            print(f"  {f.get('plano')} [{f.get('resultado')}] {f.get('nota')}")
    print("\nSi algo se repite con evidencia, promuévelo: python bitacora.py promover ...")
    return 0


def promover(args) -> int:
    if args.tipo not in ("patron", "antipatron"):
        raise SystemExit("--tipo debe ser patron o antipatron")
    if not args.evidencia.strip():
        raise SystemExit("Un patrón necesita evidencia (proyecto, planos, resultado).")
    texto = PATRONES.read_text(encoding="utf-8") if PATRONES.exists() else "# Patrones probados\n\n## Patrones\n\n## Antipatrones\n"
    hoy = dt.date.today().isoformat()
    bloque = (f"\n### {args.titulo}\n- **Estado:** confirmado · {hoy}\n- **Contexto:** {args.contexto}\n"
              f"- **{'Técnica' if args.tipo == 'patron' else 'Problema'}:** {args.tecnica}\n- **Evidencia:** {args.evidencia}\n")
    marca = "## Patrones" if args.tipo == "patron" else "## Antipatrones"
    if marca not in texto:
        texto += f"\n{marca}\n"
    # inserta al final de la sección elegida (antes del siguiente encabezado de nivel 2)
    i = texto.index(marca) + len(marca)
    siguiente = texto.find("\n## ", i)
    if siguiente == -1:
        texto = texto.rstrip("\n") + "\n" + bloque
    else:
        texto = texto[:siguiente].rstrip("\n") + "\n" + bloque + texto[siguiente:]
    PATRONES.write_text(texto, encoding="utf-8")
    print(f"Añadido a {PATRONES}:{bloque}")
    return 0


def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("registrar")
    r.add_argument("proyecto")
    r.add_argument("--plano", required=True, help="id del plano o del ancla (P01, K01, Valeria.A0)")
    r.add_argument("--resultado", required=True)
    r.add_argument("--tipo", choices=["video", "imagen"])
    r.add_argument("--modo")
    r.add_argument("--modelo")
    r.add_argument("--prompt-id")
    r.add_argument("--version", type=int)
    r.add_argument("--defectos")
    r.add_argument("--nota")
    r.add_argument("--creditos", "--puntos", dest="creditos", type=float, help="puntos de Flow que indicó la generación")
    r.add_argument("--fecha", help="ISO; por defecto, ahora (sirve para registrar algo ya generado)")
    r.add_argument("--archivo")
    s = sub.add_parser("resumen")
    s.add_argument("proyecto", nargs="?", default=".")
    s.add_argument("--todos", help="carpeta con varios proyectos")
    pr = sub.add_parser("promover")
    pr.add_argument("--tipo", required=True)
    pr.add_argument("--titulo", required=True)
    pr.add_argument("--contexto", required=True)
    pr.add_argument("--tecnica", required=True)
    pr.add_argument("--evidencia", required=True)
    args = ap.parse_args(argv)
    return {"registrar": registrar, "resumen": resumen, "promover": promover}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
