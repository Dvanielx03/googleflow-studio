#!/usr/bin/env python3
"""probar · prueba de regresión de los scripts de workflow-skill con material sintético.

Uso: python probar.py [--conservar]

Crea en una carpeta temporal el proyecto de ejemplo, fabrica anclas y clips con FFmpeg (uno correcto, uno con
un corte interno, uno con parpadeo y congelado, uno horizontal) y comprueba validación, prompts, QC, bitácora y
el paso al montaje. No usa Flow ni gasta créditos. Ejecútala después de cambiar cualquier script.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from comun import utf8_stdout  # noqa: E402

FALLOS: list[str] = []


def py(*args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8", cwd=cwd)


def ff(*args):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg falló: {r.stderr}")


def comprobar(nombre: str, condicion: bool, detalle: str = ""):
    print(f"  {'OK ' if condicion else 'FALLA'} {nombre}" + (f" · {detalle}" if detalle and not condicion else ""))
    if not condicion:
        FALLOS.append(nombre)


def main() -> int:
    utf8_stdout()
    conservar = "--conservar" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="workflow-skill-"))
    p = tmp / "proyecto"
    try:
        print(f"Carpeta de prueba: {tmp}")
        r = py(AQUI / "nuevo_proyecto.py", p, "--ejemplo", "--nombre", "cafe-origen")
        comprobar("nuevo_proyecto --ejemplo", r.returncode == 0 and (p / "03-storyboard/plan.json").exists(), r.stderr)

        # anclas y clips sintéticos (9:16, 720x1280, 24 fps)
        a = p / "02-anclas"
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280", "-frames:v", "1", a / "fotogramas/K01.png")
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280", "-frames:v", "1", "-vf", "hue=h=90", a / "fotogramas/K02.png")
        ff("-f", "lavfi", "-i", "smptehdbars=s=720x1280", "-frames:v", "1", a / "fotogramas/K03.png")
        shutil.copy(a / "fotogramas/K03.png", a / "fotogramas/K03f.png")
        for rel in ("personajes/Valeria.A0.png", "personajes/Valeria.A0-cuerpo.png", "personajes/Valeria.A1-perfil.png",
                    "lugares/TostaduriaSantaRita.A0.png", "productos/BolsaOrigen.A0.png"):
            ff("-f", "lavfi", "-i", "mandelbrot=s=600x800", "-frames:v", "1", a / rel)
        raw = p / "05-clips/raw"
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=8", "-f", "lavfi", "-i", "sine=f=440:d=8",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", raw / "P01_v1.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=3,hue=h=90", "-f", "lavfi", "-i", "mandelbrot=s=720x1280:r=24,trim=duration=3",
           "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", raw / "P02_corte.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=2", "-f", "lavfi", "-i", "color=c=0x406080:s=720x1280:r=24:d=2.5",
           "-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=1.5", "-filter_complex",
           "[0:v]eq=brightness='if(between(t,1,1.1),0.25,0)':eval=frame[x];[x][1:v][2:v]concat=n=3:v=1[v]",
           "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", raw / "P02_parpadeo.mp4")
        ff("-f", "lavfi", "-i", "smptehdbars=s=720x1280:r=24:d=6", "-f", "lavfi", "-i", "sine=f=220:d=6",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", raw / "P03_v1.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=24:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", raw / "P03_horizontal.mp4")

        fp = AQUI / "flowprompt.py"
        r = py(fp, "validar", p, "--para-video")
        comprobar("validar ejemplo sin errores", r.returncode == 0 and "0 errores" in r.stdout, r.stdout[-400:])
        r = py(fp, "prompts", p)
        datos = json.loads((p / "04-prompts/prompts.json").read_text(encoding="utf-8"))["prompts"]
        comprobar("prompts generados (9 anclas + 3 planos)", r.returncode == 0 and len(datos) == 12, str(len(datos)))
        p01 = datos["P01"]["texto"]
        comprobar("prompt Frames sin @ y con plano único", "@" not in p01 and "Single continuous shot" in p01)
        comprobar("prompt con línea de audio", "Audio: Dialogue: none." in p01 and "Music: none." in p01)
        comprobar("fotograma clave con referencias y orientación", "Using the attached references" in datos["K01"]["texto"]
                  and "Vertical 9:16" in datos["K01"]["texto"])
        r1, r2 = py(fp, "biblia", p), py(fp, "storyboard", p)
        comprobar("biblia y storyboard", r1.returncode == 0 and r2.returncode == 0 and (p / "03-storyboard/STORYBOARD.md").exists())

        # personaje animado (diseño de dibujo con extremidades): ancla de diseño y «quietos» sin prohibir patas
        bib_ruta, plan_ruta = p / "01-biblia/biblia.json", p / "03-storyboard/plan.json"
        bib_ok, plan_ok = bib_ruta.read_text(encoding="utf-8"), plan_ruta.read_text(encoding="utf-8")
        bib, plan = json.loads(bib_ok), json.loads(plan_ok)
        bib["personajes"][0]["forma"] = "animado"
        plan["planos"][0]["quietos"] = ["@Valeria"]
        bib_ruta.write_text(json.dumps(bib), encoding="utf-8")
        plan_ruta.write_text(json.dumps(plan), encoding="utf-8")
        r = py(fp, "prompts", p)
        datos = json.loads((p / "04-prompts/prompts.json").read_text(encoding="utf-8"))["prompts"]
        p01 = datos["P01"]["texto"]
        comprobar("animado: ancla de diseño fiel al dibujo", "Character design reference" in datos["Valeria.A0"]["texto"]
                  and "not turned into a realistic" in datos["Valeria.A0"]["texto"], datos["Valeria.A0"]["texto"][:200])
        comprobar("animado: quieto sin prohibir extremidades", "only blinking and breathing softly" in p01 and "never shows legs" not in p01,
                  p01[-400:])
        # referencia solo de estilo: el lugar aporta color y luz, no la composición
        anc_ruta = p / "02-anclas/anclas.json"
        anc_ok = anc_ruta.read_text(encoding="utf-8")
        anc = json.loads(anc_ok)
        k01 = next(x for x in anc["anclas"] if x["id"] == "K01")
        lugar = next(x for x in k01["padres"] if (next(a for a in anc["anclas"] if a["id"] == x).get("tipo") == "lugar"))
        k01["solo_estilo"] = [lugar]
        anc_ruta.write_text(json.dumps(anc), encoding="utf-8")
        py(fp, "prompts", p)
        k = json.loads((p / "04-prompts/prompts.json").read_text(encoding="utf-8"))["prompts"]["K01"]["texto"]
        comprobar("solo_estilo: referencia de color sin imponer el encuadre", "(style reference, image" in k
                  and "not its layout or framing" in k and "layout of" not in k.split("Keep", 1)[-1].replace("not its layout", ""), k[-300:])
        # fotograma derivado de otro fotograma: misma luz y fondo, solo cambia lo indicado
        anc = json.loads(anc_ok)
        k02 = next(x for x in anc["anclas"] if x["id"] == "K02")
        k02.update({"padres": ["K01"], "derivada_de": "K01", "cambio_en": "the bag is now open"})
        anc_ruta.write_text(json.dumps(anc), encoding="utf-8")
        py(fp, "prompts", p, "--forzar")
        d = json.loads((p / "04-prompts/prompts.json").read_text(encoding="utf-8"))["prompts"]["K02"]
        comprobar("fotograma derivado de otro fotograma", d["texto"].startswith("Using the attached image as the same shot")
                  and "Change only: the bag is now open" in d["texto"] and d["adjuntar"] and d["adjuntar"][0].endswith("K01.png"),
                  d["texto"][:200] + str(d["adjuntar"]))
        anc_ruta.write_text(anc_ok, encoding="utf-8")
        bib["personajes"][0]["forma"] = "dibujo"
        bib_ruta.write_text(json.dumps(bib), encoding="utf-8")
        r = py(fp, "validar", p)
        comprobar("validar detecta forma no válida", "no válida" in r.stdout, r.stdout[-300:])
        bib_ruta.write_text(bib_ok, encoding="utf-8")
        plan_ruta.write_text(plan_ok, encoding="utf-8")
        py(fp, "prompts", p)

        # plan roto
        plan_ruta = p / "03-storyboard/plan.json"
        plan_ok = plan_ruta.read_text(encoding="utf-8")
        plan = json.loads(plan_ok)
        plan["planos"][0].update({"modo": "ingredientes", "modelo": "veo-3.1-lite", "duracion": 6, "camara": "dolly, same as before"})
        plan["planos"][1]["estado_inicial"] = "light #E9B872 at 3200K"
        plan["planos"][2]["modo"] = "texto"
        plan_ruta.write_text(json.dumps(plan), encoding="utf-8")
        r = py(fp, "validar", p)
        for clave in ("no es válido para Veo 3.1 - Lite", "referencia vaga", "código hex", "Kelvin", "nada recurrente sale solo de texto"):
            comprobar(f"validar detecta: {clave}", clave in r.stdout, r.stdout[-300:])
        comprobar("validar devuelve error", r.returncode == 1)
        plan_ruta.write_text(plan_ok, encoding="utf-8")

        qc = AQUI / "qc_clips.py"
        r = py(qc, p, "P01", raw / "P01_v1.mp4")
        info = json.loads((p / "07-qc/P01/qc.json").read_text(encoding="utf-8"))
        comprobar("QC clip correcto sin bloqueantes", r.returncode == 0, r.stdout[-300:])
        comprobar("QC similitud con K01 alta", (info["metricas"]["sim_inicio"] or 0) > 0.8, str(info["metricas"]["sim_inicio"]))
        comprobar("QC hoja y último fotograma", (p / "07-qc/P01/hoja.jpg").exists() and (p / "07-qc/P01/ultimo.png").exists())
        r = py(qc, p, "P02", raw / "P02_corte.mp4")
        info = json.loads((p / "07-qc/P02/qc.json").read_text(encoding="utf-8"))
        comprobar("QC detecta corte interno", r.returncode == 1 and info["metricas"]["cortes"] == [3.0], str(info["metricas"]["cortes"]))
        py(qc, p, "P02", raw / "P02_parpadeo.mp4")
        m = json.loads((p / "07-qc/P02/qc.json").read_text(encoding="utf-8"))["metricas"]
        comprobar("QC parpadeo no es corte", 1.0 in m["parpadeos"] and 1.0 not in m["cortes"], f"{m['parpadeos']} / {m['cortes']}")
        comprobar("QC detecta congelado", any(a0 <= 2.2 and b0 >= 4.0 for a0, b0 in m["congelados"]), str(m["congelados"]))
        r = py(qc, p, "P03", raw / "P03_horizontal.mp4")
        comprobar("QC detecta relación de aspecto", r.returncode == 1 and "relación de aspecto 16:9" in r.stdout)
        # salto de luz sin corte: la misma imagen se oscurece de golpe a los 3 s y no vuelve
        ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=6", "-vf", "eq=brightness='if(gte(t,3),-0.25,0)':eval=frame",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", raw / "P03_salto.mp4")
        r = py(qc, p, "P03", raw / "P03_salto.mp4")
        comprobar("QC detecta salto de luz sin corte", "salto de luz o de escena" in r.stdout, r.stdout[-400:])
        r = py(qc, p, "P01", raw / "P01_v1.mp4")
        comprobar("QC sin falso salto en un clip limpio", "salto de luz" not in r.stdout, r.stdout[-300:])

        bt = AQUI / "bitacora.py"
        py(bt, "registrar", p, "--plano", "P02", "--resultado", "rechazado", "--defectos", "cortes", "--creditos", "20")
        py(bt, "registrar", p, "--plano", "P02", "--resultado", "aprobado", "--creditos", "20")
        r = py(bt, "registrar", p, "--plano", "P01", "--resultado", "aprobado", "--defectos", "inventado")
        comprobar("bitácora rechaza defectos no normalizados", r.returncode != 0)
        r = py(bt, "resumen", p)
        comprobar("bitácora resumen", "frames" in r.stdout and "cortes (1)" in r.stdout, r.stdout[-300:])

        # montaje: un proyecto mínimo con motion.config.json basta para preparar los recursos
        ms = p / "08-montaje"
        (ms / "kit").mkdir(parents=True, exist_ok=True)
        (ms / "motion.config.json").write_text(json.dumps({"video": {"ancho": 540, "alto": 960, "fps": 30, "duracion": 15}}), encoding="utf-8")
        apr = p / "05-clips/aprobados"
        shutil.copy(raw / "P01_v1.mp4", apr / "P01.mp4")
        shutil.copy(raw / "P02_corte.mp4", apr / "P02.mp4")
        shutil.copy(raw / "P03_v1.mp4", apr / "P03.mp4")
        am = AQUI / "a_motion_studio.py"
        r = py(am, p, ms, "--animatic")
        comprobar("animatic", r.returncode == 0 and (ms / "recursos/flow/P01/0000.png").exists(), r.stdout[-300:])
        r = py(am, p, ms, "--ajustar-duracion")
        clips = json.loads((ms / "recursos/flow/clips.json").read_text(encoding="utf-8"))
        comprobar("clips al montaje", r.returncode == 0 and len(clips["clips"]) == 3 and clips["duracion_total"] == 14.4, r.stdout[-300:])
        comprobar("fundido P02→P03", clips["clips"][2]["fundido_entrada"] == 0.5 and clips["clips"][2]["inicio"] == 9.4)
        comprobar("audio extraído", (ms / "audio/flow/P01.wav").exists() and not (ms / "audio/flow/P02.wav").exists())
        comprobar("ayudante JS copiado", (ms / "kit/flow_montaje.js").exists())
        r = py(am, p, ms)
        comprobar("caché de montaje", r.stdout.count("sin cambios") == 3, r.stdout)

        # costes: registro de sesión sintético (líneas repetidas del mismo mensaje se cuentan una vez)
        cp = tmp / "claude-projects" / "C--demo"
        cp.mkdir(parents=True)
        lineas = []
        for i, (ts, out) in enumerate([("2026-01-01T10:00:00Z", 100), ("2026-01-01T11:00:00Z", 200), ("2026-01-01T12:00:00Z", 400)]):
            linea = json.dumps({"sessionId": "s1", "timestamp": ts, "requestId": f"r{i}",
                                "message": {"id": f"m{i}", "model": "demo", "usage": {"input_tokens": 1, "output_tokens": out,
                                            "cache_creation_input_tokens": 10, "cache_read_input_tokens": 1000}}})
            lineas += [linea, linea]
        (cp / "s1.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        import os
        entorno = {**os.environ, "CLAUDE_PROJECTS_DIR": str(tmp / "claude-projects")}
        co = AQUI / "costos.py"
        for args in (["sesion", p, "--id", "s1", "--desde", "2026-01-01T09:00:00Z"],
                     ["hito", p, "--nombre", "Etapa B", "--fecha", "2026-01-01T10:30:00Z"],
                     ["saldo", p, "--puntos", "100", "--fecha", "2026-01-01T09:00:00Z"],
                     ["saldo", p, "--puntos", "60", "--fecha", "2026-01-01T12:30:00Z"]):
            subprocess.run([sys.executable, str(co), *map(str, args)], capture_output=True, env=entorno)
        r = subprocess.run([sys.executable, str(co), "informe", str(p), "--previo", "Etapa A"], capture_output=True,
                           text=True, encoding="utf-8", env=entorno)
        comprobar("costes: tokens por etapa sin duplicados", "| Etapa A |" in r.stdout and "| 1 | 111 |" in r.stdout
                  and "| Etapa B |" in r.stdout and "| 2 | 622 |" in r.stdout, r.stdout[:900])
        comprobar("costes: consumo medido de Flow", "**40 puntos**" in r.stdout, r.stdout[-400:])

        # mezcla de audio (sin llamar a ElevenLabs): música + efectos sintéticos a −14 LUFS
        au = p / "06-audio"
        (au / "sfx").mkdir(parents=True, exist_ok=True)
        (au / "musica").mkdir(parents=True, exist_ok=True)
        ff("-f", "lavfi", "-i", "sine=f=220:d=16", "-af", "volume=0.2", au / "musica/musica.mp3")
        ff("-f", "lavfi", "-i", "anoisesrc=d=1.2:c=pink:a=0.5", au / "sfx/golpe.mp3")
        (au / "sonido.json").write_text(json.dumps({"efectos": [{"id": "golpe", "texto_en": "x", "t": 2.0, "ganancia_db": -6}],
                                                    "voces": [], "musica": {"archivo": "06-audio/musica/musica.mp3", "ganancia_db": -12}}),
                                        encoding="utf-8")
        r = py(AQUI / "elevenlabs.py", "mezclar", p, "--duracion", "12")
        import re as _re
        lufs = _re.search(r"→ (-?[\d.]+) LUFS", r.stdout)
        comprobar("mezcla de audio a −14 LUFS", r.returncode == 0 and lufs and abs(float(lufs.group(1)) + 14) <= 1,
                  r.stdout[-300:] + r.stderr[-300:])
        # una voz que acaba pronto no debe cortar la música con el ducking (la-piscina-azul v3)
        (au / "voz").mkdir(parents=True, exist_ok=True)
        ff("-f", "lavfi", "-i", "sine=f=600:d=0.8", "-af", "volume=0.5", au / "voz/hola.mp3")
        (au / "sonido.json").write_text(json.dumps({"efectos": [], "voces": [{"id": "hola", "voice_id": "x", "texto": "x", "t": 1.0}],
                                                    "musica": {"archivo": "06-audio/musica/musica.mp3", "ganancia_db": -12,
                                                               "salida_s": 0.5, "ducking_ratio": 4}}), encoding="utf-8")
        r = py(AQUI / "elevenlabs.py", "mezclar", p, "--duracion", "12")
        fin = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p / "08-montaje/audio/final.wav"),
                              "-af", "atrim=9:11,ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
        i_fin = _re.findall(r"I:\s+(-?[\d.]+) LUFS", fin)
        comprobar("la música sigue sonando después de la última voz", r.returncode == 0 and i_fin and float(i_fin[-1]) > -25,
                  f"{i_fin[-1] if i_fin else '?'} LUFS a 9–11 s · {r.stdout[-200:]}{r.stderr[-200:]}")
    finally:
        if conservar:
            print(f"(se conserva {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODO OK' if not FALLOS else f'{len(FALLOS)} fallos: ' + ', '.join(FALLOS)}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
