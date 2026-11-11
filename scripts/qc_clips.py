#!/usr/bin/env python3
"""qc_clips · revisión automática de un clip de Flow frente a su plano y sus anclas.

Uso:
  python qc_clips.py <proyecto> <plano> <clip.mp4> [--caras] [--muestras 11] [--fps-analisis 8]

Deja en <proyecto>/07-qc/<plano>/: hoja.jpg, ultimo.png, qc.json (y caras.jpg con --caras).
Las medidas son señales para saber dónde mirar; la decisión sale de mirar la hoja y reproducir el clip.
Requiere ffmpeg/ffprobe, numpy y Pillow. --caras requiere OpenCV; sin él:
  uv run --with "opencv-python-headless<5" --with numpy --with pillow python qc_clips.py ... --caras
Código de salida 1 si hay un fallo bloqueante.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import Proyecto, aspecto_de, escribir_json, ffmpeg_disponible, ffprobe, utf8_stdout  # noqa: E402

UMBRAL_SIM_INICIO = 0.55
UMBRAL_DELTA_E = 12.0


# ----------------------------------------------------------------------------- lectura

def decodificar(ruta: Path, fps: float, ancho: int, alto: int) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-i", str(ruta), "-vf", f"fps={fps},scale={ancho}:{alto}:flags=area",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    datos = subprocess.run(cmd, capture_output=True).stdout
    tam = ancho * alto * 3
    n = len(datos) // tam
    if n == 0:
        raise SystemExit(f"No se pudieron decodificar fotogramas de {ruta}")
    return np.frombuffer(datos[: n * tam], np.uint8).reshape(n, alto, ancho, 3)


def extraer_ultimo(ruta: Path, destino: Path) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.5", "-i", str(ruta), "-update", "1", str(destino)],
                       capture_output=True)
    return r.returncode == 0 and destino.exists()


def cargar_imagen(ruta: Path, ancho: int, alto: int) -> np.ndarray | None:
    if not ruta or not Path(ruta).exists():
        return None
    im = ImageOps.fit(Image.open(ruta).convert("RGB"), (ancho, alto), Image.Resampling.LANCZOS)
    return np.asarray(im)


# ----------------------------------------------------------------------------- medidas

def gris(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def lab_medio(rgb: np.ndarray) -> np.ndarray:
    c = rgb.reshape(-1, 3).astype(np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    lab = np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)
    return lab.mean(axis=0)


def ssim_bloques(a: np.ndarray, b: np.ndarray, bloque: int = 8) -> float:
    """SSIM en bloques no solapados sobre luminancia; suficiente como señal de parecido estructural."""
    ga, gb = gris(a.astype(np.float64)), gris(b.astype(np.float64))
    h, w = (ga.shape[0] // bloque) * bloque, (ga.shape[1] // bloque) * bloque
    ga = ga[:h, :w].reshape(h // bloque, bloque, w // bloque, bloque).swapaxes(1, 2).reshape(-1, bloque * bloque)
    gb = gb[:h, :w].reshape(h // bloque, bloque, w // bloque, bloque).swapaxes(1, 2).reshape(-1, bloque * bloque)
    ma, mb = ga.mean(1), gb.mean(1)
    va, vb = ga.var(1), gb.var(1)
    cov = ((ga - ma[:, None]) * (gb - mb[:, None])).mean(1)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    s = ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))
    return float(s.mean())


def histograma(rgb: np.ndarray, bins: int = 4) -> np.ndarray:
    q = (rgb // (256 // bins)).reshape(-1, 3).astype(np.int32)
    idx = q[:, 0] * bins * bins + q[:, 1] * bins + q[:, 2]
    h = np.bincount(idx, minlength=bins ** 3).astype(np.float64)
    return h / h.sum()


def analizar(fot: np.ndarray, fps: float) -> dict:
    n = len(fot)
    g = gris(fot.astype(np.float32))
    lum = g.mean(axis=(1, 2))
    hist = np.array([histograma(f) for f in fot])
    tv = np.r_[0, 0.5 * np.abs(np.diff(hist, axis=0)).sum(axis=1)]
    dif = np.r_[0, np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))]
    med_tv = float(np.median(tv[1:])) if n > 2 else 0.0
    # Correlación de la estructura (gris sin media) entre fotogramas seguidos: un corte cambia la
    # estructura; un parpadeo cambia el brillo y la conserva.
    planos = g.reshape(n, -1)
    centrados = planos - planos.mean(axis=1, keepdims=True)
    normas = np.linalg.norm(centrados, axis=1)
    corr = np.ones(n)
    for i in range(1, n):
        den = normas[i] * normas[i - 1]
        corr[i] = float((centrados[i] * centrados[i - 1]).sum() / den) if den > 1e-6 else (1.0 if normas[i] + normas[i - 1] < 1e-6 else 0.0)
    cortes = []
    for i in range(1, n):
        cambio = (tv[i] > 0.6) or (tv[i] > 0.4 and dif[i] > 18) or (tv[i] > 4 * med_tv + 0.25 and dif[i] > 12)
        if cambio and corr[i] < 0.6:
            cortes.append(round(i / fps, 2))
    parpadeos = []
    for i in range(1, n):
        if abs(lum[i] - lum[i - 1]) > 10 and corr[i] >= 0.6 and round(i / fps, 2) not in cortes:
            parpadeos.append(round(i / fps, 2))
    congelados, inicio = [], None
    for i in range(1, n):
        quieto = dif[i] < 0.5
        if quieto and inicio is None:
            inicio = i - 1
        if (not quieto or i == n - 1) and inicio is not None:
            fin = i if quieto else i - 1
            if (fin - inicio) / fps >= 1.0:
                congelados.append([round(inicio / fps, 2), round(fin / fps, 2)])
            inicio = None
    negros = [round(i / fps, 2) for i in range(n) if lum[i] < 10]
    # Saltos de escena: el fondo (mitad superior) cambia de luz o de color en ~0,5 s y no vuelve,
    # aunque la estructura se parezca. Pasa en Frames cuando inicio y fin no comparten luz:
    # el modelo «salta» de uno a otro sin corte (visto en la-piscina-azul, P04 v1 y v2).
    alto_fondo = max(1, int(fot.shape[1] * 0.5))
    labs = np.array([lab_medio(f[:alto_fondo]) for f in fot])
    w = max(1, int(round(0.5 * fps)))
    saltos: list[dict] = []
    if n > 2 * w + 1:
        de = np.zeros(n)
        for i in range(w, n):
            de[i] = float(np.linalg.norm(labs[i] - labs[i - w]))
        base = float(np.median(de[w:]))
        grupo: list[int] = []
        for i in range(w, n + 1):
            fin_grupo = i == n
            if not fin_grupo:
                persiste = float(np.linalg.norm(labs[min(i + w, n - 1)] - labs[i - w])) > 1.5
                # Umbral medido en la-piscina-azul: saltos reales 2,1 y 5,1; paneos limpios 0,7 y 1,0.
                es = de[i] > max(1.8, 4 * base) and persiste
            if not fin_grupo and es:
                grupo.append(i)
                continue
            if grupo:
                k = max(grupo, key=lambda j: de[j])
                t = round((k - w / 2) / fps, 2)
                if not any(abs(t - c) < 0.3 for c in cortes):
                    saltos.append({"t": t, "de": round(float(de[k]), 1)})
                grupo = []
    return {"cortes": cortes, "parpadeos": parpadeos, "congelados": congelados, "negros": negros,
            "saltos_escena": saltos, "movimiento_medio": round(float(dif[1:].mean()) if n > 1 else 0.0, 2)}


# ----------------------------------------------------------------------------- caras (opcional)

def caras(muestras: list[tuple[float, np.ndarray]], ancla: Path | None):
    try:
        import cv2  # type: ignore
    except ImportError:
        cv2 = None
    if cv2 is None or not hasattr(cv2, "CascadeClassifier"):
        return None, ("--caras necesita OpenCV 4 (OpenCV 5 retiró el detector clásico). Repite con\n"
                      '  uv run --with "opencv-python-headless<5" --with numpy --with pillow python qc_clips.py ... --caras')
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def detectar(rgb):
        gr = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        lado = min(gr.shape)
        return det.detectMultiScale(gr, scaleFactor=1.1, minNeighbors=6, minSize=(max(24, lado // 12),) * 2)

    def recorte(rgb, caja):
        x, y, w, h = caja
        m = int(0.25 * w)
        y0, y1, x0, x1 = max(0, y - m), min(rgb.shape[0], y + h + m), max(0, x - m), min(rgb.shape[1], x + w + m)
        return Image.fromarray(rgb[y0:y1, x0:x1]).resize((128, 128), Image.Resampling.LANCZOS)

    tiras, cuentas = [], []
    if ancla and ancla.exists():
        arr = np.asarray(Image.open(ancla).convert("RGB"))
        cs = detectar(arr)
        if len(cs):
            tiras.append(("ancla", recorte(arr, max(cs, key=lambda c: c[2] * c[3]))))
    for t, rgb in muestras:
        cs = detectar(rgb)
        cuentas.append({"t": round(t, 2), "caras": int(len(cs))})
        if len(cs):
            tiras.append((f"{t:.1f}s", recorte(rgb, max(cs, key=lambda c: c[2] * c[3]))))
    return {"cuentas": cuentas, "tiras": tiras}, None


# ----------------------------------------------------------------------------- hoja

def fuente(tam: int):
    for nombre in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


def hoja(titulo: str, refs: list[tuple[str, Path]], celdas: list[dict], celda_wh: tuple[int, int], cols: int, destino: Path):
    cw, ch = celda_wh
    pie = 22
    filas = -(-len(celdas) // cols)
    ref_h = max(1, len(refs)) * (ch + pie)
    alto = 40 + max(filas * (ch + pie), ref_h) + 10
    ancho = (cw + 12) + 16 + cols * (cw + 6) + 10
    lienzo = Image.new("RGB", (ancho, alto), (24, 24, 28))
    d = ImageDraw.Draw(lienzo)
    f, fb = fuente(14), fuente(17)
    d.text((10, 10), titulo, fill=(240, 240, 240), font=fb)
    y = 40
    for nombre, ruta in refs:
        im = ImageOps.fit(Image.open(ruta).convert("RGB"), (cw, ch), Image.Resampling.LANCZOS)
        lienzo.paste(im, (10, y))
        d.rectangle([10, y, 10 + cw - 1, y + ch - 1], outline=(90, 160, 255), width=2)
        d.text((12, y + ch + 3), nombre, fill=(140, 190, 255), font=f)
        y += ch + pie
    x0 = 10 + cw + 28
    d.line([(x0 - 14, 40), (x0 - 14, alto - 10)], fill=(70, 70, 80), width=2)
    for i, c in enumerate(celdas):
        x = x0 + (i % cols) * (cw + 6)
        y = 40 + (i // cols) * (ch + pie)
        im = Image.fromarray(c["rgb"]).resize((cw, ch), Image.Resampling.LANCZOS)
        if c.get("fuera"):
            im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.55)
        lienzo.paste(im, (x, y))
        color = (255, 70, 70) if c.get("corte") else (80, 80, 90)
        d.rectangle([x, y, x + cw - 1, y + ch - 1], outline=color, width=3 if c.get("corte") else 1)
        etiqueta = c["etiqueta"] + ("  · fuera de uso" if c.get("fuera") else "") + ("  · CORTE" if c.get("corte") else "")
        d.text((x + 2, y + ch + 3), etiqueta, fill=(220, 220, 220), font=f)
    destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(destino, quality=90)


def tira_caras(tiras: list, destino: Path):
    f = fuente(13)
    ancho = 10 + len(tiras) * 136
    lienzo = Image.new("RGB", (max(ancho, 200), 160), (24, 24, 28))
    d = ImageDraw.Draw(lienzo)
    for i, (nombre, im) in enumerate(tiras):
        x = 10 + i * 136
        lienzo.paste(im, (x, 10))
        if nombre == "ancla":
            d.rectangle([x, 10, x + 127, 137], outline=(90, 160, 255), width=3)
        d.text((x + 2, 140), nombre, fill=(220, 220, 220), font=f)
    lienzo.save(destino, quality=90)


# ----------------------------------------------------------------------------- principal

def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proyecto")
    ap.add_argument("plano")
    ap.add_argument("clip")
    ap.add_argument("--caras", action="store_true", help="detecta caras y compara recortes con el ancla (OpenCV)")
    ap.add_argument("--muestras", type=int, default=11, help="fotogramas en la hoja (más el último)")
    ap.add_argument("--fps-analisis", type=float, default=8.0)
    args = ap.parse_args(argv)

    if not ffmpeg_disponible():
        raise SystemExit("Faltan ffmpeg/ffprobe en el PATH.")
    p = Proyecto(args.proyecto)
    pl = p.plano(args.plano)
    if not pl:
        raise SystemExit(f"El plano {args.plano} no está en plan.json")
    clip = Path(args.clip)
    if not clip.is_absolute() and not clip.exists():
        clip = p.raiz / clip
    if not clip.exists():
        raise SystemExit(f"No existe el clip {clip}")
    salida = p.raiz / "07-qc" / pl["id"]
    salida.mkdir(parents=True, exist_ok=True)

    info = ffprobe(clip)
    avisos: list[dict] = []

    def aviso(grav, detalle, t=None):
        avisos.append({"gravedad": grav, "detalle": detalle, **({"t": t} if t is not None else {})})

    # formato frente al plan
    aspecto_plan = (p.plan.get("formato") or {}).get("aspecto")
    aspecto_clip = aspecto_de(info["ancho"], info["alto"])
    if aspecto_plan and aspecto_clip != aspecto_plan:
        aviso("bloqueante", f"relación de aspecto {aspecto_clip}; el plan pide {aspecto_plan}")
    uso = pl.get("uso") or [0, pl.get("duracion", info["duracion"])]
    if info["duracion"] + 0.05 < uso[1]:
        aviso("bloqueante", f"el clip dura {info['duracion']} s y el tramo 'uso' llega a {uso[1]} s")
    elif pl.get("duracion") and abs(info["duracion"] - pl["duracion"]) > 0.5:
        aviso("aviso", f"el clip dura {info['duracion']} s; se pidieron {pl['duracion']} s")
    if info["fps"] and info["fps"] < 23:
        aviso("aviso", f"{info['fps']} fps")
    if min(info["ancho"], info["alto"]) < 720:
        aviso("aviso", f"resolución {info['ancho']}×{info['alto']}: súbela en Flow si la entrega es 1080p o más")
    politica = (p.biblia.get("audio") or {}).get("politica")
    if politica in ("nativo", "mixto") and (pl.get("audio") or {}).get("dialogo") and not info["audio"]:
        aviso("aviso", "el plano tiene diálogo nativo y el clip no trae audio")

    # decodificación para medir
    an = 192
    al = int(round(info["alto"] * an / info["ancho"] / 2) * 2)
    fot = decodificar(clip, args.fps_analisis, an, al)
    med = analizar(fot, args.fps_analisis)
    dentro = lambda t: uso[0] - 1e-6 <= t <= uso[1] + 1e-6  # noqa: E731
    toma_unica = pl.get("toma_unica", True)
    for t in med["cortes"]:
        if toma_unica:
            aviso("bloqueante" if dentro(t) else "aviso",
                  f"corte interno a {t} s" + ("" if dentro(t) else " (fuera del tramo 'uso': se recorta)"), t)
    for t in med["parpadeos"]:
        if dentro(t):
            aviso("aviso", f"salto de luminancia (parpadeo) a {t} s", t)
    # Un paneo o una subida de mirada prevista en el plan también cambia el fondo deprisa (del suelo al cielo):
    # en ese caso el salto queda como aviso para revisar a ojo (la-piscina-azul P01: subida de mirada).
    texto_camara = " ".join([str(pl.get("camara", ""))] + [str(x.get("en", "")) for x in (pl.get("accion") or []) if isinstance(x, dict)]).lower()
    mueve = any(k in texto_camara for k in ("rising", "rises", "tilt", " pan ", " pan,", "panning", "looks up", "gaze"))
    for s in med.get("saltos_escena", []):
        if dentro(s["t"]):
            aviso("bloqueante" if s["de"] >= 4 and not mueve else "aviso",
                  f"salto de luz o de escena a {s['t']} s (ΔE {s['de']} del fondo en 0,5 s, sin corte): "
                  + ("el plano prevé un movimiento de mirada o paneo; comprueba a ojo que sea gradual"
                     if mueve else "el fondo cambia de golpe; suele venir de un inicio y un fin con luz distinta"), s["t"])
    for a, b in med["congelados"]:
        aviso("aviso", f"imagen casi congelada de {a} a {b} s", a)
    if med["negros"]:
        aviso("aviso", f"{len(med['negros'])} fotogramas casi negros (primero a {med['negros'][0]} s)", med["negros"][0])

    # fidelidad a los fotogramas clave y deriva de color
    k_ini = p.ancla(pl.get("fotograma_inicial") or "")
    k_fin = p.ancla(pl.get("fotograma_final") or "")
    ruta_ini = p.raiz / k_ini["archivo"] if k_ini and k_ini.get("archivo") else None
    ruta_fin = p.raiz / k_fin["archivo"] if k_fin and k_fin.get("archivo") else None
    img_ini = cargar_imagen(ruta_ini, an, al) if ruta_ini else None
    img_fin = cargar_imagen(ruta_fin, an, al) if ruta_fin else None
    med["sim_inicio"] = round(ssim_bloques(fot[0], img_ini), 3) if img_ini is not None else None
    med["sim_final"] = round(ssim_bloques(fot[-1], img_fin), 3) if img_fin is not None else None
    if pl.get("modo", "").startswith("frames"):
        if img_ini is None:
            aviso("aviso", "no se encontró el fotograma inicial para comparar")
        elif med["sim_inicio"] < UMBRAL_SIM_INICIO:
            aviso("aviso", f"el primer fotograma se parece poco al fotograma clave (similitud {med['sim_inicio']}); "
                           "¿se adjuntó como inicio o Flow lo recortó?", 0.0)
        if pl.get("modo") == "frames_ultimo" and img_fin is not None and med["sim_final"] < UMBRAL_SIM_INICIO:
            aviso("aviso", f"el último fotograma se parece poco al final pedido (similitud {med['sim_final']})", info["duracion"])
    ref_color = img_ini
    ref_nombre = pl.get("fotograma_inicial")
    if ref_color is None:
        for r in pl.get("anclas") or []:
            a = p.ancla(r) or {}
            if a.get("tipo") == "lugar" and a.get("archivo"):
                ref_color = cargar_imagen(p.raiz / a["archivo"], an, al)
                ref_nombre = r
                if ref_color is not None:
                    break
    if ref_color is not None:
        lab_ref = lab_medio(ref_color)
        de = np.array([np.linalg.norm(lab_medio(f) - lab_ref) for f in fot])
        en_uso = np.array([dentro(i / args.fps_analisis) for i in range(len(fot))])
        de_uso = np.where(en_uso, de, -1.0) if en_uso.any() else de
        imax = int(de_uso.argmax())
        med["deriva_color"] = {"referencia": ref_nombre, "max": round(float(de_uso[imax]), 2),
                               "t_max": round(imax / args.fps_analisis, 2), "inicio": round(float(de[0]), 2),
                               "max_clip_entero": round(float(de.max()), 2)}
        if de_uso[imax] > UMBRAL_DELTA_E:
            aviso("aviso", f"el color se aleja de {ref_nombre} (ΔE {de_uso[imax]:.1f} a {imax / args.fps_analisis:.1f} s): luz o grado cambió",
                  round(imax / args.fps_analisis, 2))

    # último fotograma (relevo) y muestras para la hoja
    ultimo = salida / "ultimo.png"
    extraer_ultimo(clip, ultimo)
    vertical = info["alto"] > info["ancho"]
    cw, ch = (200, int(200 * info["alto"] / info["ancho"])) if vertical else (320, int(320 * info["alto"] / info["ancho"]))
    n = max(2, args.muestras)
    fps_m = n / max(info["duracion"], 0.1)
    mw = cw * 2
    mh = int(round(info["alto"] * mw / info["ancho"] / 2) * 2)
    mues = decodificar(clip, fps_m, mw, mh)[:n]
    tiempos = [i / fps_m for i in range(len(mues))]
    # Una celda se marca si hubo un corte entre la muestra anterior y ella.
    celdas = [{"rgb": m, "etiqueta": f"{t:.2f} s", "fuera": not dentro(t),
               "corte": any((tiempos[i - 1] if i else -1) < c <= t + 0.06 for c in med["cortes"])}
              for i, (t, m) in enumerate(zip(tiempos, mues))]
    if ultimo.exists():
        u = np.asarray(ImageOps.fit(Image.open(ultimo).convert("RGB"), (mw, mh)))
        celdas.append({"rgb": u, "etiqueta": f"último · {info['duracion']:.2f} s", "fuera": not dentro(info["duracion"])})
    refs: list[tuple[str, Path]] = []
    if ruta_ini and ruta_ini.exists():
        refs.append((f"inicio {pl.get('fotograma_inicial')}", ruta_ini))
    if ruta_fin and ruta_fin.exists():
        refs.append((f"fin {pl.get('fotograma_final')}", ruta_fin))
    ancla_cara = None
    for r in pl.get("anclas") or []:
        a = p.ancla(r) or {}
        if a.get("tipo") in ("personaje", "producto") and a.get("archivo") and (p.raiz / a["archivo"]).exists():
            ruta_a = p.raiz / a["archivo"]
            if len(refs) < 4:
                refs.append((r, ruta_a))
            if a.get("tipo") == "personaje" and ancla_cara is None:
                maestra = next((x for x in p.anclas if x.get("entidad") == a.get("entidad") and x.get("nivel") == 0
                                and x.get("variante") != "cuerpo" and x.get("archivo") and (p.raiz / x["archivo"]).exists()), None)
                ancla_cara = p.raiz / maestra["archivo"] if maestra else ruta_a
    bloq = sum(1 for a in avisos if a["gravedad"] == "bloqueante")
    titulo = (f"{pl['id']} · {pl.get('modo')} · {pl.get('modelo')} · {info['duracion']:.2f} s · uso {uso} · "
              f"{bloq} bloqueantes · {len(avisos) - bloq} avisos")
    ruta_hoja = salida / "hoja.jpg"
    hoja(titulo, refs, celdas, (cw, ch), 6 if vertical else 4, ruta_hoja)

    # caras
    ruta_caras = None
    if args.caras:
        res, err = caras(list(zip(tiempos, mues)), ancla_cara)
        if err:
            print(err)
        else:
            esperadas = len({(p.ancla(r) or {}).get("entidad") for r in pl.get("anclas") or []
                             if (p.ancla(r) or {}).get("tipo") == "personaje"})
            med["caras"] = {"esperadas": esperadas, "cuentas": res["cuentas"]}
            sobra = [c["t"] for c in res["cuentas"] if dentro(c["t"]) and c["caras"] > esperadas]
            if len(sobra) >= 2:
                aviso("aviso", f"más caras de las previstas ({esperadas}) en {sobra}: ¿personas que sobran o caras deformadas?", sobra[0])
            if res["tiras"]:
                ruta_caras = salida / "caras.jpg"
                tira_caras(res["tiras"], ruta_caras)

    informe = {
        "plano": pl["id"], "clip": str(clip), "fecha": dt.datetime.now().isoformat(timespec="seconds"),
        "formato": info, "esperado": {"aspecto": aspecto_plan, "duracion": pl.get("duracion"), "uso": uso,
                                      "toma_unica": toma_unica, "modo": pl.get("modo"), "modelo": pl.get("modelo")},
        "metricas": med, "avisos": avisos, "hoja": str(ruta_hoja), "ultimo": str(ultimo) if ultimo.exists() else None,
        "caras": str(ruta_caras) if ruta_caras else None,
        "pendiente": "Revisión visual: identidad, manos, producto, lugar, movimiento, continuidad, texto y audio (07-control-calidad.md).",
    }
    escribir_json(salida / "qc.json", informe)

    print(f"QC de {pl['id']} · {clip.name} · {info['ancho']}×{info['alto']} · {info['fps']} fps · {info['duracion']} s · "
          f"audio {'sí' if info['audio'] else 'no'}")
    if med.get("sim_inicio") is not None:
        print(f"  similitud con {pl.get('fotograma_inicial')}: {med['sim_inicio']}")
    if med.get("deriva_color"):
        dc = med["deriva_color"]
        print(f"  deriva de color frente a {dc['referencia']}: máx ΔE {dc['max']} a {dc['t_max']} s")
    for a in avisos:
        print(f"  {a['gravedad'].upper():10} {a['detalle']}")
    print(f"\nHoja: {ruta_hoja}")
    if ruta_caras:
        print(f"Caras: {ruta_caras}")
    if ultimo.exists():
        print(f"Último fotograma (relevo): {ultimo}")
    print("Ahora mira la hoja y reproduce el clip: las medidas no ven manos, caras ni continuidad.")
    return 1 if bloq else 0


if __name__ == "__main__":
    sys.exit(main())
