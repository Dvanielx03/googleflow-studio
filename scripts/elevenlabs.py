#!/usr/bin/env python3
"""elevenlabs · efectos, voces y música con ElevenLabs, y la mezcla final del video.

Uso:
  python elevenlabs.py generar <proyecto> [--solo id1,id2] [--musica]
  python elevenlabs.py mezclar <proyecto> --duracion 15 [--salida 08-montaje/audio/final.wav]
  python elevenlabs.py saldo   <proyecto>

Lee 06-audio/sonido.json:
  {"efectos": [{"id": "puerta", "texto_en": "...", "duracion": 1.5, "t": 2.8, "ganancia_db": -4}],
   "voces":   [{"id": "v1", "voice_id": "...", "texto": "[whispers] ...", "modelo": "eleven_v4", "t": 0.0, "ganancia_db": 0,
                "filtro": "highpass=f=250,aecho=0.8:0.6:180:0.4" (opcional, FFmpeg),
                "ajustes": {"stability": 0.4, "similarity_boost": 0.8}}],
   "clips_audio": [{"archivo": "05-clips/aprobados/P01.mp4", "entrada": 0.0, "salida": 5.0, "t": 0.0, "ganancia_db": 0}],
   "musica":  {"archivo": "06-audio/musica/musica.mp3", "inicio_pista_s": 0, "prompt_en": "...", "duracion_ms": 16000,
               "ganancia_db": -10, "entrada_s": 0.8, "salida_s": 1.5, "ducking_ratio": 6}}
`clips_audio` conserva el sonido nativo de los clips (los efectos de Flow). La música baja bajo las voces (ducking).
Clave: variable ELEVENLABS_API_KEY o archivo de credenciales con ELEVENLABS_API_KEY=... (ruta en ELEVENLABS_ENV, o
~/.config/googleflow-studio/elevenlabs.env por defecto). Nunca se imprime ni se guarda en el proyecto.
No vuelve a pagar lo que ya existe. Anota en costos.json los caracteres o créditos consumidos.
La mezcla deja la música de fondo, los efectos y las voces en su instante, a −14 LUFS y −1 dBTP.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import escribir_json, ffmpeg_disponible, leer_json, utf8_stdout  # noqa: E402

API = "https://api.elevenlabs.io/v1"
CRED_DEFECTO = Path.home() / ".config" / "googleflow-studio" / "elevenlabs.env"


def clave() -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    ruta = Path(os.environ.get("ELEVENLABS_ENV") or CRED_DEFECTO)
    if not ruta.exists():
        raise SystemExit("No hay clave de ElevenLabs: define ELEVENLABS_API_KEY, o ELEVENLABS_ENV con la ruta de un archivo "
                         f"con ELEVENLABS_API_KEY=..., o crea {CRED_DEFECTO}.")
    datos = dict(l.strip().split("=", 1) for l in ruta.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
    vence = datos.get("ELEVENLABS_API_KEY_VENCE")
    if vence and dt.date.fromisoformat(vence) <= dt.date.today() + dt.timedelta(days=7):
        print(f"Aviso: la clave de ElevenLabs vence el {vence}.")
    return datos["ELEVENLABS_API_KEY"]


def pedir(ruta: str, cuerpo: dict | None = None, binario: bool = False):
    req = urllib.request.Request(API + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers={"xi-api-key": clave(), "Content-Type": "application/json", "Accept": "*/*"},
                                 method="POST" if cuerpo is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            datos = r.read()
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300]
        raise SystemExit(f"ElevenLabs respondió {e.code} en {ruta.split('?')[0]}: {detalle}")
    return datos if binario else json.loads(datos)


def uso_actual() -> dict | None:
    try:
        s = pedir("/user/subscription")
        return {"caracteres_usados": s.get("character_count"), "limite": s.get("character_limit")}
    except SystemExit as e:
        print(f"(no se pudo leer el consumo: {e})")
        return None


def anotar_costo(raiz: Path, antes: dict | None, despues: dict | None, que: list[str]) -> None:
    ruta = raiz / "costos.json"
    datos = leer_json(ruta) if ruta.exists() else {}
    datos.setdefault("elevenlabs", []).append({
        "fecha": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generado": que,
        "antes": antes, "despues": despues,
        "consumo": (despues["caracteres_usados"] - antes["caracteres_usados"]) if antes and despues and
                   antes.get("caracteres_usados") is not None and despues.get("caracteres_usados") is not None else None,
    })
    escribir_json(ruta, datos)


def generar(raiz: Path, solo: set[str] | None, con_musica: bool) -> int:
    son = leer_json(raiz / "06-audio" / "sonido.json")
    pendientes = []
    for e in son.get("efectos", []):
        destino = raiz / "06-audio" / "sfx" / f"{e['id']}.mp3"
        if (not solo or e["id"] in solo) and not destino.exists():
            pendientes.append(("sfx", e, destino))
    for v in son.get("voces", []):
        destino = raiz / "06-audio" / "voz" / f"{v['id']}.mp3"
        if (not solo or v["id"] in solo) and not destino.exists():
            pendientes.append(("voz", v, destino))
    m = son.get("musica") or {}
    if con_musica and m.get("prompt_en"):
        destino = raiz / (m.get("archivo") or "06-audio/musica/musica.mp3")
        if not destino.exists():
            pendientes.append(("musica", m, destino))
    if not pendientes:
        print("Nada que generar: todo existe ya (no se vuelve a pagar).")
        return 0
    antes = uso_actual()
    hechos = []
    for tipo, item, destino in pendientes:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if tipo == "sfx":
            audio = pedir("/sound-generation?output_format=mp3_44100_128",
                          {"text": item["texto_en"], "duration_seconds": item.get("duracion"),
                           "prompt_influence": item.get("influencia", 0.5)}, binario=True)
        elif tipo == "voz":
            cuerpo = {"text": item["texto"], "model_id": item.get("modelo", "eleven_v4")}
            if item.get("ajustes"):
                cuerpo["voice_settings"] = item["ajustes"]
            # Contexto que no se lee: da a la frase una entonación natural (mejor que las etiquetas de susurro).
            for k in ("previous_text", "next_text"):
                if item.get(k):
                    cuerpo[k] = item[k]
            audio = pedir(f"/text-to-speech/{item['voice_id']}?output_format=mp3_44100_128", cuerpo, binario=True)
        else:
            audio = pedir("/music?output_format=mp3_44100_128",
                          {"prompt": item["prompt_en"], "music_length_ms": int(item.get("duracion_ms", 16000))}, binario=True)
        destino.write_bytes(audio)
        hechos.append(f"{tipo}:{item.get('id', 'musica')}")
        print(f"  {tipo:6} {item.get('id', 'musica'):14} {len(audio) // 1024} KB → {destino.relative_to(raiz)}")
    import time
    # El contador de la cuenta tarda en reflejar el consumo (8 s no bastaron en la-piscina-azul): hasta ~40 s.
    despues = None
    for _ in range(5):
        time.sleep(8)
        despues = uso_actual()
        if not antes or not despues or (despues.get("caracteres_usados") or 0) > (antes.get("caracteres_usados") or 0):
            break
    anotar_costo(raiz, antes, despues, hechos)
    if antes and despues and antes.get("caracteres_usados") is not None:
        print(f"Consumo de ElevenLabs: {despues['caracteres_usados'] - antes['caracteres_usados']} "
              f"(de {despues.get('limite')} en el periodo)")
    return 0


def mezclar(raiz: Path, duracion: float, salida: Path) -> int:
    if not ffmpeg_disponible():
        raise SystemExit("Faltan ffmpeg/ffprobe.")
    son = leer_json(raiz / "06-audio" / "sonido.json")
    entradas, filtros, etiquetas = [], [], []

    def entrada(ruta: Path) -> int:
        entradas.extend(["-i", str(ruta)])
        return len(entradas) // 2 - 1

    m = son.get("musica") or {}
    musica = raiz / m["archivo"] if m.get("archivo") else None
    hay_musica = False
    if musica and musica.exists():
        i = entrada(musica)
        fin = max(0.1, duracion - float(m.get("salida_s", 1.5)))
        # La pista empieza en su segundo `inicio_pista_s` (0 = desde el principio de la canción).
        ini = float(m.get("inicio_pista_s", 0))
        filtros.append(f"[{i}:a]aresample=48000,atrim=start={ini:.3f},asetpts=PTS-STARTPTS,aloop=loop=-1:size=2e9,"
                       f"atrim=0:{duracion:.3f},"
                       f"afade=t=in:d={float(m.get('entrada_s', 0.8)):.2f},afade=t=out:st={fin:.3f}:d={float(m.get('salida_s', 1.5)):.2f},"
                       f"volume={float(m.get('ganancia_db', -10))}dB[mus]")
        hay_musica = True
    elif m:
        print("Aviso: no hay archivo de música; la mezcla sale sin música de fondo.")
    # Audio nativo de los clips (p. ej. los efectos que generó Flow), en su lugar de la línea de tiempo.
    for k, c in enumerate(son.get("clips_audio", [])):
        ruta = raiz / c["archivo"]
        if not ruta.exists():
            print(f"Aviso: falta {c['archivo']}; se omite.")
            continue
        i = entrada(ruta)
        a0, a1 = float(c.get("entrada", 0)), float(c["salida"])
        fd = float(c.get("fundido", 0.04))
        ms = int(float(c.get("t", 0)) * 1000)
        et = f"[c{k}]"
        filtros.append(f"[{i}:a]aresample=48000,atrim={a0:.3f}:{a1:.3f},asetpts=PTS-STARTPTS,"
                       f"afade=t=in:d={fd:.3f},afade=t=out:st={max(0.0, a1 - a0 - fd):.3f}:d={fd:.3f},"
                       f"adelay={ms}|{ms},volume={float(c.get('ganancia_db', 0))}dB{et}")
        etiquetas.append(et)
    voces = []
    for grupo, carpeta in (("efectos", "sfx"), ("voces", "voz")):
        for k, it in enumerate(son.get(grupo, [])):
            ruta = raiz / "06-audio" / carpeta / f"{it['id']}.mp3"
            if not ruta.exists():
                print(f"Aviso: falta {ruta.relative_to(raiz)}; se omite.")
                continue
            i = entrada(ruta)
            ms = int(float(it.get("t", 0)) * 1000)
            et = f"[{grupo[0]}{k}]"
            # "filtro": cadena de FFmpeg opcional por capa (p. ej. eco lejano de un recuerdo: highpass,lowpass,aecho).
            extra = f"{it['filtro']}," if it.get("filtro") else ""
            filtros.append(f"[{i}:a]aresample=48000,{extra}adelay={ms}|{ms},volume={float(it.get('ganancia_db', 0))}dB{et}")
            # Las voces, y los efectos con "ducking": true (un suspiro, una respiración), bajan la música.
            (voces if grupo == "voces" or it.get("ducking") else etiquetas).append(et)
    # Ducking: la música baja mientras suena una voz.
    if voces:
        if len(voces) > 1:
            filtros.append(f"{''.join(voces)}amix=inputs={len(voces)}:normalize=0:dropout_transition=0[vz]")
        else:
            filtros.append(f"{voces[0]}anull[vz]")
        if hay_musica:
            # La señal de control del ducking debe durar todo el video: si termina antes (la última voz acaba a
            # mitad), sidechaincompress corta la música ahí (visto en la-piscina-azul v3: música muda desde 26,4 s).
            filtros.append(f"[vz]apad=whole_dur={duracion:.3f},asplit=2[vz1][vz2]")
            filtros.append(f"[mus][vz1]sidechaincompress=threshold=0.02:ratio={float(m.get('ducking_ratio', 6))}:"
                           "attack=20:release=500[musd]")
            etiquetas += ["[musd]", "[vz2]"]
        else:
            etiquetas.append("[vz]")
    elif hay_musica:
        etiquetas.append("[mus]")
    if not etiquetas:
        raise SystemExit("No hay nada que mezclar (ni música ni efectos ni voces).")
    filtros.append(f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0:dropout_transition=0,"
                   f"atrim=0:{duracion:.3f},apad=whole_dur={duracion:.3f}[pre]")
    base = ["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex"]
    # 1ª pasada: medir sonoridad (loudnorm informa a nivel info, así que esta pasada no puede ir con -v error)
    medir = ["ffmpeg", "-hide_banner", "-nostats", "-y", *entradas, "-filter_complex"]
    r = subprocess.run(medir + [";".join(filtros) + ";[pre]loudnorm=I=-14:TP=-1:LRA=11:print_format=json[o]", "-map", "[o]",
                               "-f", "null", "-"], capture_output=True, text=True)
    medida = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not medida:
        raise SystemExit(f"No se pudo medir la mezcla: {r.stderr[-400:]}")
    md = json.loads(medida.group(0))
    # Ganancia exacta hasta −14 LUFS y limitador de picos a −1 dBFS (loudnorm lineal se queda corto con mucha ganancia).
    ganancia = -14.0 - float(md["input_i"])
    salida.parent.mkdir(parents=True, exist_ok=True)
    # Hasta dos pasadas: si el limitador baja la sonoridad (voces y transitorios fuertes), se compensa la diferencia.
    for _ in range(2):
        norm = f"volume={ganancia:.2f}dB,aresample=192000,alimiter=limit=0.82:attack=5:release=60:level=false"  # x4: controla el pico real
        r = subprocess.run(base + [";".join(filtros) + f";[pre]{norm},aresample=48000[o]", "-map", "[o]", "-ac", "2",
                                   "-c:a", "pcm_s16le", str(salida)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"ffmpeg falló al mezclar: {r.stderr[-400:]}")
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(salida), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True)
        i_final = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        pico = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
        final = float(i_final[-1]) if i_final else None
        if final is None or abs(final + 14) <= 0.2:
            break
        ganancia += -14.0 - final
    print(f"Mezcla: {salida} · {duracion} s · {len(etiquetas)} capas · {md['input_i']} LUFS → "
          f"{final if final is not None else '?'} LUFS · pico real {pico[-1] if pico else '?'} dBFS")
    if final is not None and abs(final + 14) > 1:
        print("Aviso: la mezcla queda a más de 1 LU de −14 (el limitador recortó mucho): baja la música o los efectos más fuertes.")
    return 0


def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generar")
    g.add_argument("proyecto")
    g.add_argument("--solo")
    g.add_argument("--musica", action="store_true", help="genera también la música con ElevenLabs Music")
    mz = sub.add_parser("mezclar")
    mz.add_argument("proyecto")
    mz.add_argument("--duracion", type=float, required=True)
    mz.add_argument("--salida", default="08-montaje/audio/final.wav")
    s = sub.add_parser("saldo")
    s.add_argument("proyecto")
    args = ap.parse_args(argv)
    raiz = Path(args.proyecto).resolve()
    if args.cmd == "generar":
        return generar(raiz, set(args.solo.split(",")) if args.solo else None, args.musica)
    if args.cmd == "mezclar":
        salida = Path(args.salida)
        return mezclar(raiz, args.duracion, salida if salida.is_absolute() else raiz / salida)
    uso = uso_actual()
    if not uso:
        return 1
    print(f"ElevenLabs: {uso['caracteres_usados']} de {uso['limite']} créditos usados en el periodo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
