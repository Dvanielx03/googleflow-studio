"""Utilidades compartidas por los scripts de workflow-skill (solo biblioteca estándar)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"

RUTAS = {
    "brief": "BRIEF.md",
    "biblia": "01-biblia/biblia.json",
    "anclas": "02-anclas/anclas.json",
    "plan": "03-storyboard/plan.json",
    "prompts": "04-prompts/prompts.json",
    "bitacora": "bitacora.jsonl",
}

HANDLE_RE = re.compile(r"^@[A-Z][A-Za-z0-9]*$")
INTERVALO_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*s\s*$")


def utf8_stdout() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def leer_json(ruta: Path):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Falta el archivo: {ruta}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"JSON inválido en {ruta}: línea {e.lineno}, columna {e.colno}: {e.msg}")


def escribir_json(ruta: Path, datos) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def capacidades() -> dict:
    return leer_json(ASSETS / "flow_capacidades.json")


class Proyecto:
    """Carga perezosa de los JSON de un proyecto de Flow."""

    def __init__(self, carpeta: str | Path):
        self.raiz = Path(carpeta).resolve()
        if not self.raiz.is_dir():
            raise SystemExit(f"No existe la carpeta del proyecto: {self.raiz}")
        self._cache: dict = {}

    def ruta(self, clave: str) -> Path:
        return self.raiz / RUTAS[clave]

    def _cargar(self, clave: str):
        if clave not in self._cache:
            self._cache[clave] = leer_json(self.ruta(clave))
        return self._cache[clave]

    @property
    def biblia(self) -> dict:
        return self._cargar("biblia")

    @property
    def anclas(self) -> list:
        return self._cargar("anclas").get("anclas", [])

    @property
    def plan(self) -> dict:
        return self._cargar("plan")

    def ancla(self, ident: str) -> dict | None:
        return next((a for a in self.anclas if a.get("id") == ident), None)

    def plano(self, ident: str) -> dict | None:
        return next((p for p in self.plan.get("planos", []) if p.get("id") == ident), None)

    def entidades(self) -> dict:
        """handle -> (tipo, ficha) para personajes, lugares y productos de la biblia."""
        out = {}
        for tipo, clave in (("personaje", "personajes"), ("lugar", "lugares"), ("producto", "productos")):
            for ficha in self.biblia.get(clave, []) or []:
                out[ficha.get("handle")] = (tipo, ficha)
        return out


def intervalo(texto: str):
    """'0-3s' -> (0.0, 3.0) o None."""
    m = INTERVALO_RE.match(str(texto))
    return (float(m.group(1)), float(m.group(2))) if m else None


def linea_de_tiempo(plan: dict) -> list[dict]:
    """Coloca los planos en el video según `uso` y los fundidos de `enlace`.

    Devuelve [{id, inicio, duracion, fundido_entrada}] en orden del plan.
    """
    out, cursor, fundido_sig = [], 0.0, 0.0
    for pl in plan.get("planos", []):
        uso = pl.get("uso") or [0, pl.get("duracion", 0)]
        dur = max(0.0, float(uso[1]) - float(uso[0]))
        fundido = min(fundido_sig, dur / 2) if out else 0.0
        inicio = max(0.0, cursor - fundido)
        out.append({"id": pl.get("id"), "inicio": round(inicio, 4), "duracion": round(dur, 4),
                    "fundido_entrada": round(fundido, 4)})
        cursor = inicio + dur
        enlace = pl.get("enlace") or {}
        fundido_sig = float(enlace.get("duracion", 0.5)) if enlace.get("tipo") == "fundido" else 0.0
    return out


def ffmpeg_disponible() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def ffprobe(ruta: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(ruta)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode != 0:
        raise SystemExit(f"ffprobe no pudo leer {ruta}: {r.stderr.strip()}")
    datos = json.loads(r.stdout)
    video = next((s for s in datos.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in datos.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video:
        raise SystemExit(f"{ruta} no tiene pista de video")
    num, _, den = (video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    duracion = float(datos.get("format", {}).get("duration") or video.get("duration") or 0)
    return {
        "ancho": int(video["width"]),
        "alto": int(video["height"]),
        "fps": round(fps, 3),
        "duracion": round(duracion, 3),
        "codec": video.get("codec_name"),
        "audio": bool(audio),
        "audio_codec": audio.get("codec_name") if audio else None,
    }


def aspecto_de(ancho: int, alto: int) -> str:
    r = ancho / alto
    candidatos = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:3": 4 / 3, "3:4": 3 / 4, "4:5": 4 / 5}
    nombre, valor = min(candidatos.items(), key=lambda kv: abs(kv[1] - r))
    return nombre if abs(valor - r) < 0.03 else f"{ancho}:{alto}"
