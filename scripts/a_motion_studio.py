#!/usr/bin/env python3
"""a_motion_studio · pasa los clips aprobados (o el animatic) a un proyecto de motion-studio.

Uso:
  python a_motion_studio.py <proyecto-flow> <proyecto-motion-studio> [--animatic] [--forzar] [--ajustar-duracion]

Para cada plano de plan.json, en orden:
  · clip 05-clips/aprobados/<P>.mp4 → tramo 'uso' como PNG en recursos/flow/<P>/0000.png… (fps nativos,
    ajustado al tamaño de motion.config.json) y su audio en audio/flow/<P>.wav;
  · con --animatic, el fotograma clave inicial del plano, quieto durante su tramo.
Escribe recursos/flow/clips.json (línea de tiempo con fundidos) y copia kit/flow_montaje.js.
Solo rehace los planos cuyo origen, tramo o tamaño cambiaron.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ASSETS, Proyecto, escribir_json, ffmpeg_disponible, ffprobe, leer_json, linea_de_tiempo, utf8_stdout  # noqa: E402


def sello(*partes) -> str:
    return hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:12]


def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proyecto")
    ap.add_argument("destino", help="carpeta del proyecto de motion-studio (con motion.config.json)")
    ap.add_argument("--animatic", action="store_true", help="usa los fotogramas clave quietos en vez de los clips")
    ap.add_argument("--forzar", action="store_true", help="rehace todos los planos")
    ap.add_argument("--ajustar-duracion", action="store_true", help="escribe la duración total en motion.config.json")
    args = ap.parse_args(argv)

    if not ffmpeg_disponible():
        raise SystemExit("Faltan ffmpeg/ffprobe en el PATH.")
    p = Proyecto(args.proyecto)
    destino = Path(args.destino).resolve()
    cfg_ruta = destino / "motion.config.json"
    if not cfg_ruta.exists():
        raise SystemExit(f"{destino} no es un proyecto de motion-studio (falta motion.config.json).\n"
                         "Créalo con: python <motion-studio>/scripts/nuevo.py <carpeta> --duracion N --fps 30 [--vertical]")
    cfg = leer_json(cfg_ruta)
    W, H = int(cfg["video"]["ancho"]), int(cfg["video"]["alto"])
    base = destino / "recursos" / "flow"
    base.mkdir(parents=True, exist_ok=True)
    (destino / "audio" / "flow").mkdir(parents=True, exist_ok=True)
    estado_ruta = base / "estado.json"
    estado = leer_json(estado_ruta) if estado_ruta.exists() else {}

    tl = {x["id"]: x for x in linea_de_tiempo(p.plan)}
    clips, faltan = [], []
    for pl in p.plan.get("planos", []):
        pid = pl["id"]
        t = tl[pid]
        uso = pl.get("uso") or [0, pl.get("duracion", 0)]
        carpeta = base / pid
        if args.animatic:
            k = p.ancla(pl.get("fotograma_inicial") or "")
            origen = p.raiz / k["archivo"] if k and k.get("archivo") else None
            if not origen or not origen.exists():
                faltan.append(f"{pid}: falta el fotograma clave {pl.get('fotograma_inicial')}")
                continue
            firma = sello("animatic", origen, origen.stat().st_mtime_ns, W, H)
            if args.forzar or estado.get(pid, {}).get("firma") != firma or not (carpeta / "0000.png").exists():
                shutil.rmtree(carpeta, ignore_errors=True)
                carpeta.mkdir(parents=True)
                ImageOps.fit(Image.open(origen).convert("RGB"), (W, H), Image.Resampling.LANCZOS).save(carpeta / "0000.png")
                estado[pid] = {"firma": firma, "cantidad": 1, "fps": 1, "audio": False}
                print(f"  {pid}: animatic con {origen.name}")
            else:
                print(f"  {pid}: sin cambios")
        else:
            origen = p.raiz / "05-clips" / "aprobados" / f"{pid}.mp4"
            if not origen.exists():
                faltan.append(f"{pid}: falta {origen.relative_to(p.raiz)}")
                continue
            info = ffprobe(origen)
            if info["duracion"] + 0.05 < uso[1]:
                faltan.append(f"{pid}: el clip dura {info['duracion']} s y 'uso' llega a {uso[1]} s")
                continue
            firma = sello("clip", origen, origen.stat().st_size, origen.stat().st_mtime_ns, uso, W, H)
            if args.forzar or estado.get(pid, {}).get("firma") != firma or not (carpeta / "0000.png").exists():
                shutil.rmtree(carpeta, ignore_errors=True)
                carpeta.mkdir(parents=True)
                vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
                r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{uso[0]:.4f}", "-to", f"{uso[1]:.4f}", "-i", str(origen),
                                    "-vf", vf, "-start_number", "0", str(carpeta / "%04d.png")], capture_output=True, text=True)
                if r.returncode != 0:
                    raise SystemExit(f"ffmpeg falló en {pid}: {r.stderr.strip()}")
                cantidad = len(list(carpeta.glob("*.png")))
                tiene_audio = False
                if info["audio"]:
                    wav = destino / "audio" / "flow" / f"{pid}.wav"
                    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{uso[0]:.4f}", "-to", f"{uso[1]:.4f}", "-i", str(origen),
                                        "-vn", "-ac", "2", "-ar", "48000", str(wav)], capture_output=True, text=True)
                    tiene_audio = r.returncode == 0
                estado[pid] = {"firma": firma, "cantidad": cantidad, "fps": info["fps"] or 24, "audio": tiene_audio}
                print(f"  {pid}: {cantidad} fotogramas a {info['fps']} fps" + (" + audio" if tiene_audio else ""))
            else:
                print(f"  {pid}: sin cambios")
        e = estado[pid]
        clips.append({"id": pid, "tipo": "secuencia", "ruta": f"recursos/flow/{pid}/", "cantidad": e["cantidad"],
                      "fps": e["fps"], "primero": 0, "digitos": 4, "extension": "png",
                      "inicio": t["inicio"], "duracion": t["duracion"], "fundido_entrada": t["fundido_entrada"],
                      "audio": f"audio/flow/{pid}.wav" if e.get("audio") else None})

    escribir_json(estado_ruta, estado)
    if faltan:
        print("\nNo se pudo preparar:")
        for f in faltan:
            print(f"  · {f}")
    if not clips:
        return 1
    total = round(clips[-1]["inicio"] + clips[-1]["duracion"], 3)
    escribir_json(base / "clips.json", {"version": 1, "modo": "animatic" if args.animatic else "clips",
                                        "proyecto": p.plan.get("proyecto"), "ancho": W, "alto": H,
                                        "duracion_total": total, "clips": clips})
    kit = destino / "kit"
    kit.mkdir(exist_ok=True)
    shutil.copy2(ASSETS / "kit" / "flow_montaje.js", kit / "flow_montaje.js")
    if not (kit / "secuencia.js").exists():
        print("  Aviso: falta kit/secuencia.js en el proyecto de motion-studio.")
    dur_cfg = cfg["video"].get("duracion")
    if args.ajustar_duracion and dur_cfg != total:
        cfg["video"]["duracion"] = total
        escribir_json(cfg_ruta, cfg)
        print(f"motion.config.json → video.duracion = {total}")
    elif dur_cfg != total:
        print(f"Aviso: motion.config.json dice {dur_cfg} s y el montaje suma {total} s (usa --ajustar-duracion).")
    print(f"\n{len(clips)} planos · {total} s → {base / 'clips.json'}")
    print("En index.html: kit/secuencia.js + kit/flow_montaje.js y `await (await crearMontajeFlow('recursos/flow/clips.json')).dibujar(ctx, t, W, H)`.")
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())
