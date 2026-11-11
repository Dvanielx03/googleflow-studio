#!/usr/bin/env python3
"""flowprompt · valida un proyecto de Flow y arma sus prompts y documentos.

Uso (desde cualquier carpeta):
  python flowprompt.py validar    <proyecto> [--para-video]
  python flowprompt.py prompts    <proyecto> [--solo P01,K01] [--forzar]
  python flowprompt.py biblia     <proyecto>
  python flowprompt.py storyboard <proyecto>

Fuente de verdad: 01-biblia/biblia.json, 02-anclas/anclas.json y 03-storyboard/plan.json.
Solo biblioteca estándar. Código de salida 1 si hay errores bloqueantes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (HANDLE_RE, Proyecto, capacidades, escribir_json, intervalo,  # noqa: E402
                   linea_de_tiempo, utf8_stdout)

TIPOS_ENTIDAD = {"personaje": "personajes", "lugar": "lugares", "producto": "productos"}
TIPO_EN = {"personaje": "character", "lugar": "location", "producto": "product"}
ESTADOS = {"pendiente", "propuesta", "aprobada", "rechazada"}
MODO_UI = {
    "frames": "Frames (inicio)",
    "frames_ultimo": "Frames (inicio y fin)",
    "ingredientes": "Ingredients",
    "texto": "Texto a video",
    "extender": "Extend",
    "editar": "Editar video",
}
NOMBRE_IMAGEN = {
    "nano-banana-pro": "Nano Banana Pro",
    "nano-banana-2.1": "Nano Banana 2.1",
    "nano-banana-2-lite": "Nano Banana 2 Lite",
}

# Texto que se cuela en la imagen o que el modelo no puede resolver.
PROHIBIDO = [
    (re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b"), "código hex (usa el nombre del color)"),
    (re.compile(r"\b\d{4,5}\s?K\b"), "temperatura en Kelvin (descríbela con palabras)"),
    (re.compile("—"), "raya larga (—): usa coma, dos puntos o punto"),
    (re.compile(r"\b(same as before|as before|like before|as in the previous|like the previous|"
                r"previous (?:shot|scene|clip)|the same (?:woman|man|person|girl|boy|guy|place|room|one))\b", re.I),
     "referencia vaga a otro plano: describe el estado visible"),
]
PRESTIGIO = re.compile(r"\b(masterpiece|stunning|breathtaking|award[- ]winning|8k|ultra[- ]?hd|best quality|hyper[- ]?detailed)\b", re.I)


# ----------------------------------------------------------------------------- utilidades de texto

def frase(s: str) -> str:
    s = (s or "").strip()
    return s if not s or s.endswith((".", "!", "?")) else s + "."


def sin_punto(s: str) -> str:
    return (s or "").strip().rstrip(".").strip()


def mayus(s: str) -> str:
    s = (s or "").strip()
    return s[:1].upper() + s[1:]


def sin_arrobas(s: str) -> str:
    return re.sub(r"@([A-Z][A-Za-z0-9]*)", r"\1", s)


def lista_en(items: list[str], conj: str = "and") -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]


FORMAS = {"humano", "criatura", "animado"}


def es_criatura(ficha: dict) -> bool:
    return (ficha or {}).get("forma") == "criatura"


def es_animado(ficha: dict) -> bool:
    """Personaje de dibujo o de animación 3D con extremidades que conserva su diseño original (no se vuelve realista)."""
    return (ficha or {}).get("forma") == "animado"


def rasgos(ficha: dict) -> str:
    if es_criatura(ficha):
        return "shape, colors and eyes"
    if es_animado(ficha):
        return "design, proportions, colors, eyes and outfit"
    return "face, hair and clothing"


def nombres_en_frames(texto: str, entidades: dict) -> str:
    """En Frames no hay referencias adjuntas: cada @Handle pasa a su nombre_en (o al nombre sin @)."""
    for h, (_, ficha) in entidades.items():
        if h and ficha.get("nombre_en"):
            texto = re.sub(re.escape(h) + r"(?![A-Za-z0-9])", ficha["nombre_en"], texto)
    texto = sin_arrobas(texto)
    # mayúscula al empezar línea, tras un intervalo [0-3s] o tras punto
    return re.sub(r"(^|\] |\. )([a-z])", lambda m: m.group(1) + m.group(2).upper(), texto, flags=re.M)


def huella(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]


def palabras(texto: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", texto))


# ----------------------------------------------------------------------------- validación

class Informe:
    def __init__(self):
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def e(self, msg):
        self.errores.append(msg)

    def a(self, msg):
        self.avisos.append(msg)

    def texto(self, donde: str, valor):
        if not valor:
            return
        valores = valor if isinstance(valor, list) else [valor]
        for v in valores:
            if not isinstance(v, str):
                continue
            for patron, motivo in PROHIBIDO:
                if patron.search(v):
                    self.e(f"{donde}: {motivo} → «{patron.search(v).group(0)}»")
            if PRESTIGIO.search(v):
                self.a(f"{donde}: adjetivo vacío «{PRESTIGIO.search(v).group(0)}»; usa dirección concreta")


def validar(p: Proyecto, cap: dict, para_video: bool = False) -> Informe:
    inf = Informe()
    b, plan, anclas = p.biblia, p.plan, p.anclas
    hoy = dt.date.today()

    # --- biblia
    estilo = b.get("estilo") or {}
    if not estilo.get("prefijo_en"):
        inf.e("biblia: falta estilo.prefijo_en")
    inf.texto("biblia.estilo.prefijo_en", estilo.get("prefijo_en"))
    luces = b.get("iluminaciones") or {}
    for k, v in luces.items():
        if not (v or {}).get("en"):
            inf.e(f"biblia.iluminaciones.{k}: falta 'en'")
        inf.texto(f"biblia.iluminaciones.{k}", (v or {}).get("en"))
    for col in b.get("paleta") or []:
        if not col.get("nombre_en"):
            inf.a(f"biblia.paleta: el color {col.get('hex')} no tiene nombre_en para los prompts")

    entidades: dict[str, tuple[str, dict]] = {}
    for tipo, clave in TIPOS_ENTIDAD.items():
        for f in b.get(clave) or []:
            h = f.get("handle", "")
            if not HANDLE_RE.match(h or ""):
                inf.e(f"biblia.{clave}: handle inválido «{h}» (formato @PascalCase, sin espacios ni tildes)")
            if h in entidades:
                inf.e(f"biblia: handle duplicado {h}")
            entidades[h] = (tipo, f)
            campo = {"personaje": "identidad_en", "lugar": "disposicion_en", "producto": "descripcion_en"}[tipo]
            if not f.get(campo):
                inf.e(f"biblia {h}: falta {campo}")
            inf.texto(f"biblia {h}.{campo}", f.get(campo))
            if tipo == "personaje":
                if f.get("forma") and f["forma"] not in FORMAS:
                    inf.e(f"biblia {h}: forma «{f['forma']}» no válida ({', '.join(sorted(FORMAS))})")
                if not f.get("vestuario") and f.get("forma") not in ("criatura", "animado"):
                    inf.a(f"biblia {h}: sin vestuario definido")
                for vk, vv in (f.get("vestuario") or {}).items():
                    inf.texto(f"biblia {h}.vestuario.{vk}", vv)
                if not f.get("no_cambiar"):
                    inf.a(f"biblia {h}: sin rasgos 'no_cambiar' para vigilar en el QC")
                if f.get("forma") == "criatura" and not f.get("movimiento_en"):
                    inf.a(f"biblia {h}: criatura sin 'movimiento_en'; al animarla el modelo puede inventarle patas o brazos")
                inf.texto(f"biblia {h}.movimiento_en", f.get("movimiento_en"))
            if tipo == "lugar" and f.get("luz_base") and f["luz_base"] not in luces:
                inf.e(f"biblia {h}: luz_base {f['luz_base']} no existe en iluminaciones")
            if tipo == "producto" and f.get("texto_real"):
                inf.a(f"biblia {h}: el texto de la etiqueta («{f['texto_real']}») va en el montaje, no en los prompts")
    politica = ((b.get("audio") or {}).get("politica"))
    if politica not in {"post", "nativo", "mixto"}:
        inf.e("biblia.audio.politica debe ser post, nativo o mixto")
    pendientes = json.dumps(b, ensure_ascii=False).count("TODO")
    if pendientes:
        inf.a(f"biblia: {pendientes} campos con TODO")

    # --- anclas
    ids: dict[str, dict] = {}
    for a in anclas:
        i = a.get("id")
        if not i:
            inf.e("anclas: una entrada sin id")
            continue
        if i in ids:
            inf.e(f"anclas: id duplicado {i}")
        ids[i] = a
    planos_ids = {pl.get("id") for pl in plan.get("planos", [])}
    for i, a in ids.items():
        tipo = a.get("tipo")
        estado = a.get("estado", "pendiente")
        if estado not in ESTADOS:
            inf.e(f"ancla {i}: estado «{estado}» no válido ({', '.join(sorted(ESTADOS))})")
        for padre in a.get("padres") or []:
            if padre == i:
                inf.e(f"ancla {i}: no puede ser su propio padre")
            elif padre not in ids:
                inf.e(f"ancla {i}: el padre {padre} no existe")
        if tipo in TIPOS_ENTIDAD:
            ent = a.get("entidad")
            if ent not in entidades:
                inf.e(f"ancla {i}: la entidad {ent} no está en la biblia")
            elif entidades[ent][0] != tipo:
                inf.e(f"ancla {i}: tipo {tipo} no coincide con la biblia ({entidades[ent][0]})")
            nivel = a.get("nivel")
            if nivel == 0 and a.get("padres"):
                inf.a(f"ancla {i}: una maestra (nivel 0) no debería tener padres")
            if nivel == 1:
                if not a.get("padres"):
                    inf.e(f"ancla {i}: una derivada necesita su maestra en 'padres'")
                if not a.get("cambio_en"):
                    inf.e(f"ancla {i}: una derivada necesita 'cambio_en' (una sola variación)")
                inf.texto(f"ancla {i}.cambio_en", a.get("cambio_en"))
                for padre in a.get("padres") or []:
                    if padre in ids and ids[padre].get("nivel") != 0:
                        inf.a(f"ancla {i}: deriva de {padre}, que no es maestra; deriva siempre desde la maestra")
            if nivel not in (0, 1):
                inf.e(f"ancla {i}: personajes, lugares y productos son nivel 0 (maestra) o 1 (derivada)")
            if tipo == "personaje" and a.get("vestuario") and ent in entidades:
                if a["vestuario"] not in (entidades[ent][1].get("vestuario") or {}):
                    inf.e(f"ancla {i}: vestuario {a['vestuario']} no existe para {ent}")
        elif tipo == "fotograma":
            if a.get("plano") not in planos_ids:
                inf.e(f"ancla {i}: el plano {a.get('plano')} no existe en el plan")
            if not a.get("padres"):
                inf.e(f"ancla {i}: un fotograma clave se compone desde anclas aprobadas ('padres')")
            for padre in a.get("padres") or []:
                if padre in ids and ids[padre].get("tipo") in ("fotograma", "relevo"):
                    inf.a(f"ancla {i}: se compone desde {padre}; compón desde maestras o derivadas")
        elif tipo == "relevo":
            if a.get("desde") not in planos_ids:
                inf.e(f"ancla {i}: 'desde' debe ser el plano del que sale el último fotograma")
        else:
            inf.e(f"ancla {i}: tipo «{tipo}» no válido")
        if estado == "aprobada" and a.get("archivo") and not (p.raiz / a["archivo"]).exists():
            inf.a(f"ancla {i}: aprobada pero falta el archivo {a['archivo']}")

    # --- plan
    formato = plan.get("formato") or {}
    if formato.get("aspecto") not in ("9:16", "16:9"):
        inf.e("plan.formato.aspecto debe ser 9:16 o 16:9 (los que admite Flow)")
    planos = plan.get("planos") or []
    if not planos:
        inf.a("plan: no hay planos todavía")
    vistos = set()
    relevos_seguidos = 0
    for pl in planos:
        pid = pl.get("id", "?")
        donde = f"plano {pid}"
        if pid in vistos:
            inf.e(f"{donde}: id duplicado")
        vistos.add(pid)
        modelo, modo = pl.get("modelo"), pl.get("modo")
        mcap = (cap.get("video") or {}).get(modelo)
        if not mcap:
            inf.e(f"{donde}: modelo «{modelo}» desconocido ({', '.join(cap.get('video', {}))})")
            continue
        if mcap.get("retiro"):
            retiro = dt.date.fromisoformat(mcap["retiro"])
            if retiro <= hoy:
                inf.e(f"{donde}: {mcap['nombre_ui']} se retiró el {retiro}")
            elif (retiro - hoy).days <= 45:
                inf.a(f"{donde}: {mcap['nombre_ui']} se retira el {retiro}; prefiere omni-1.2 o veo-3.1-lite")
        if modo not in MODO_UI:
            inf.e(f"{donde}: modo «{modo}» no válido ({', '.join(MODO_UI)})")
            continue
        if modo not in mcap.get("modos", []):
            inf.e(f"{donde}: {mcap['nombre_ui']} no admite el modo {modo}")
        dur = pl.get("duracion")
        if not isinstance(dur, (int, float)) or dur <= 0:
            inf.e(f"{donde}: falta 'duracion'")
            dur = 0
        else:
            if "duraciones" in mcap:
                validas = mcap.get("duraciones_ingredientes") if modo == "ingredientes" and mcap.get("duraciones_ingredientes") else mcap["duraciones"]
                if dur not in validas:
                    inf.e(f"{donde}: {dur} s no es válido para {mcap['nombre_ui']} en {modo} ({validas})")
            else:
                lo, hi, hi_pago = mcap.get("duracion_min", 1), mcap.get("duracion_max", 10), mcap.get("duracion_max_pago", mcap.get("duracion_max", 10))
                if modo == "extender":
                    lo, hi, hi_pago = mcap["extender"]["min"], mcap["extender"]["max"], mcap["extender"]["max"]
                if not lo <= dur <= hi_pago:
                    inf.e(f"{donde}: {dur} s fuera de rango para {mcap['nombre_ui']} ({lo}–{hi_pago} s)")
                elif dur > hi:
                    inf.a(f"{donde}: {dur} s requiere plan de pago (gratis hasta {hi} s)")
                if modo == "frames_ultimo" and dur > mcap.get("duracion_max_frames_ultimo", 10):
                    inf.e(f"{donde}: inicio y fin admiten como máximo {mcap.get('duracion_max_frames_ultimo', 10)} s")
            if modo == "extender" and (mcap.get("extender") or {}).get("requiere_pago"):
                inf.a(f"{donde}: Extend requiere Google AI Plus, Pro o Ultra")
        salidas = pl.get("salidas", 1)
        if not (isinstance(salidas, int) and 1 <= salidas <= 4):
            inf.e(f"{donde}: 'salidas' debe ser 1–4")
        uso = pl.get("uso")
        if uso is not None:
            if not (isinstance(uso, list) and len(uso) == 2 and 0 <= uso[0] < uso[1] <= (dur or 1e9) + 1e-6):
                inf.e(f"{donde}: 'uso' debe ser [entrada, salida] dentro de 0–{dur} s")

        # anclas del plano
        refs = pl.get("anclas") or []
        for r in refs:
            if r not in ids:
                inf.e(f"{donde}: el ancla {r} no existe en anclas.json")
            elif ids[r].get("estado") != "aprobada":
                (inf.e if para_video else inf.a)(f"{donde}: el ancla {r} no está aprobada ({ids[r].get('estado')})")
        for campo in ("fotograma_inicial", "fotograma_final"):
            k = pl.get(campo)
            if k:
                if k not in ids:
                    inf.e(f"{donde}: {campo} {k} no existe en anclas.json")
                else:
                    if ids[k].get("tipo") not in ("fotograma", "relevo"):
                        inf.e(f"{donde}: {campo} {k} debe ser un fotograma clave o un relevo")
                    if ids[k].get("estado") != "aprobada":
                        (inf.e if para_video else inf.a)(f"{donde}: {campo} {k} no está aprobado")
                    if ids[k].get("tipo") == "fotograma" and ids[k].get("plano") not in (pid, None):
                        inf.a(f"{donde}: {campo} {k} pertenece al plano {ids[k].get('plano')}")
        if modo in ("frames", "frames_ultimo") and not pl.get("fotograma_inicial"):
            inf.e(f"{donde}: el modo {modo} necesita fotograma_inicial")
        if modo == "frames_ultimo" and not pl.get("fotograma_final"):
            inf.e(f"{donde}: el modo frames_ultimo necesita fotograma_final")
        ini = ids.get(pl.get("fotograma_inicial") or "")
        relevos_seguidos = relevos_seguidos + 1 if ini and ini.get("tipo") == "relevo" else 0
        if relevos_seguidos > 2:
            inf.a(f"{donde}: tercer relevo seguido; re-ancla con un fotograma clave nuevo desde las anclas")

        tipos_ref = [ids[r].get("tipo") for r in refs if r in ids]
        if modo == "texto" and any(t in TIPOS_ENTIDAD for t in tipos_ref):
            inf.e(f"{donde}: texto a video con anclas de personaje/lugar/producto; nada recurrente sale solo de texto (usa frames o ingredientes)")
        if modo == "ingredientes":
            refs_max = mcap.get("refs_max", 0)
            if refs_max == 0:
                inf.e(f"{donde}: {mcap['nombre_ui']} no admite ingredientes")
            elif len(refs) > refs_max:
                inf.e(f"{donde}: {len(refs)} referencias; {mcap['nombre_ui']} admite {refs_max}. Compón un fotograma clave y usa frames")
            por_personaje: dict[str, int] = {}
            for r in refs:
                if r in ids and ids[r].get("tipo") == "personaje":
                    por_personaje[ids[r]["entidad"]] = por_personaje.get(ids[r]["entidad"], 0) + 1
            if mcap.get("refs_por_personaje"):
                for ent, n in por_personaje.items():
                    if n > mcap["refs_por_personaje"]:
                        inf.e(f"{donde}: {n} imágenes de {ent}; máximo {mcap['refs_por_personaje']} por personaje")
            if mcap.get("personajes_max") and len(por_personaje) > mcap["personajes_max"]:
                inf.e(f"{donde}: {len(por_personaje)} personajes; máximo {mcap['personajes_max']}. Compón un fotograma clave")
            if not refs:
                inf.e(f"{donde}: ingredientes sin anclas")
        if modo == "extender":
            if pl.get("clip_base") not in planos_ids:
                inf.e(f"{donde}: Extend necesita 'clip_base' (el plano que se alarga)")
            ext = mcap.get("extender") or {}
            if len(refs) > ext.get("refs_max", 3):
                inf.e(f"{donde}: Extend admite {ext.get('refs_max', 3)} imágenes de referencia")
        if modo == "editar":
            if not pl.get("correccion_en"):
                inf.e(f"{donde}: editar necesita 'correccion_en' (una corrección)")
            if pl.get("clip_base") not in planos_ids:
                inf.e(f"{donde}: editar necesita 'clip_base'")

        # contenido del plano
        lugar = pl.get("lugar")
        if lugar and (lugar not in entidades or entidades[lugar][0] != "lugar"):
            inf.e(f"{donde}: lugar {lugar} no está en la biblia")
        luz = pl.get("iluminacion")
        if isinstance(luz, str) and re.fullmatch(r"L\d+", luz) and luz not in luces:
            inf.e(f"{donde}: iluminación {luz} no existe en la biblia")
        for h, v in (pl.get("vestuario") or {}).items():
            if h not in entidades or entidades[h][0] != "personaje":
                inf.e(f"{donde}: vestuario para {h}, que no es un personaje de la biblia")
            elif v not in (entidades[h][1].get("vestuario") or {}):
                inf.e(f"{donde}: vestuario {v} no existe para {h}")
        if modo not in ("editar",):
            for campo in ("encuadre", "camara"):
                if not pl.get(campo):
                    inf.e(f"{donde}: falta '{campo}'")
            if not pl.get("accion"):
                inf.e(f"{donde}: falta 'accion'")
        accion = pl.get("accion") or []
        if isinstance(accion, list):
            fin_ant = 0.0
            for j, paso in enumerate(accion):
                t = intervalo(paso.get("t", "")) if isinstance(paso, dict) else None
                if not t:
                    inf.e(f"{donde}: accion[{j}] necesita 't' como «0-3s»")
                    continue
                a0, a1 = t
                if a1 <= a0:
                    inf.e(f"{donde}: accion[{j}] intervalo vacío {paso['t']}")
                if a1 > (dur or 0) + 1e-6:
                    inf.e(f"{donde}: accion[{j}] termina en {a1} s y el clip dura {dur} s")
                if a0 < fin_ant - 1e-6:
                    inf.e(f"{donde}: accion[{j}] se solapa con el paso anterior")
                elif a0 > fin_ant + 1e-6:
                    inf.a(f"{donde}: hueco entre {fin_ant} y {a0} s en la acción")
                fin_ant = a1
                inf.texto(f"{donde}.accion[{j}]", paso.get("en"))
            if accion and dur and fin_ant < dur - 0.5:
                inf.a(f"{donde}: la acción termina en {fin_ant} s y el clip dura {dur} s")
            if len(accion) > 3:
                inf.a(f"{donde}: {len(accion)} pasos de acción; una acción principal por plano")
        for campo in ("encuadre", "lente", "camara", "estado_inicial", "estado_final", "correccion_en"):
            inf.texto(f"{donde}.{campo}", pl.get(campo))
        inf.texto(f"{donde}.excluir", pl.get("excluir"))
        audio = pl.get("audio")
        if modo != "editar":
            if not isinstance(audio, dict):
                inf.e(f"{donde}: falta 'audio' (diálogo, efectos, ambiente, música)")
            else:
                if audio.get("musica") is None:
                    inf.a(f"{donde}: declara la música ('none' si no hay); si no, Flow la inventa")
                elif politica == "post" and str(audio.get("musica")).lower() not in ("none", "no music"):
                    inf.a(f"{donde}: política de audio 'post' pero el plano pide música en el clip")
                for k in ("sfx", "ambiente", "no_oir"):
                    inf.texto(f"{donde}.audio.{k}", audio.get(k))
                dlg = audio.get("dialogo")
                for d in (dlg if isinstance(dlg, list) else [dlg] if dlg else []):
                    dice = d.get("dice") if isinstance(d, dict) else str(d)
                    if dice and re.search(r"[\"“”«»]", dice):
                        inf.a(f"{donde}: diálogo con comillas; las comillas invitan a subtítulos")
                    if dice and dur and len(dice.split()) > dur * 2.8:
                        inf.a(f"{donde}: {len(dice.split())} palabras de diálogo en {dur} s; la voz saldrá acelerada")
        if mcap.get("multiplano_por_defecto") and pl.get("toma_unica") is None:
            inf.a(f"{donde}: {mcap['nombre_ui']} corta en varios planos por defecto; declara 'toma_unica'")
        enlace = pl.get("enlace") or {}
        if enlace.get("a") and enlace["a"] not in planos_ids:
            inf.e(f"{donde}: enlace a {enlace['a']}, que no existe")

    # duración total
    tl = linea_de_tiempo(plan)
    if tl:
        total = tl[-1]["inicio"] + tl[-1]["duracion"]
        objetivo = formato.get("duracion_objetivo")
        if objetivo and abs(total - objetivo) > max(1.0, 0.1 * objetivo):
            inf.a(f"plan: el montaje suma {total:.1f} s y el objetivo es {objetivo} s")
    return inf


# ----------------------------------------------------------------------------- prompts

def _ficha(p: Proyecto, handle: str):
    return p.entidades().get(handle, (None, {}))


def _vestuario(ficha: dict, clave: str | None) -> str:
    vest = ficha.get("vestuario") or {}
    if clave and clave in vest:
        return vest[clave]
    return next(iter(vest.values()), "")


def _luz(b: dict, ref) -> str:
    if not ref:
        return ""
    luces = b.get("iluminaciones") or {}
    return luces[ref]["en"] if ref in luces else str(ref)


def _orientacion(aspecto: str) -> str:
    return {"9:16": "Vertical 9:16 composition", "16:9": "Horizontal 16:9 composition"}.get(aspecto, f"{aspecto} composition")


def prompt_ancla(p: Proyecto, a: dict) -> dict:
    b = p.biblia
    pref = sin_punto(b["estilo"]["prefijo_en"])
    tipo, nivel = a.get("tipo"), a.get("nivel")
    if tipo in ("personaje", "producto") and (b.get("estilo") or {}).get("prefijo_referencias_en"):
        # Las referencias de identidad van sobre fondo neutro: sin el cielo ni la luz de las escenas.
        pref = sin_punto(b["estilo"]["prefijo_referencias_en"])
    modelo = a.get("modelo", "nano-banana-2.1")
    aspecto = a.get("aspecto", "1:1")
    salidas = a.get("salidas", 4 if nivel == 0 else 2)
    ajustes = f"Google Flow · Imagen · {NOMBRE_IMAGEN.get(modelo, modelo)} · {aspecto} · x{salidas}"
    adjuntar: list[str] = []
    es = a.get("es", "")

    if tipo == "relevo":
        return {"tipo": "relevo", "ajustes": "Sin prompt: es el último fotograma aprobado de " + a.get("desde", "?"),
                "texto": "", "es": "Usa ultimo.png de qc_clips.py o Save frame en Flow.", "adjuntar": [], "guardar": a.get("archivo")}

    if tipo in TIPOS_ENTIDAD:
        _, ficha = _ficha(p, a.get("entidad"))
        if tipo == "producto" and ficha.get("foto_real") and nivel == 0:
            return {"tipo": "imagen", "ajustes": "Foto real del producto: no se genera",
                    "texto": "", "es": f"Usa {ficha['foto_real']} como ancla maestra.", "adjuntar": [], "guardar": a.get("archivo")}
        if nivel == 0:
            if tipo == "personaje":
                vest = _vestuario(ficha, a.get("vestuario"))
                ropa = f", wearing {sin_punto(vest)}" if vest else ""
                if es_animado(ficha):
                    texto = (f"{pref}. Character design reference of {sin_punto(ficha['identidad_en'])}{ropa}. "
                             "The whole body visible from head to feet in a three-quarter front view with margin around it, "
                             "calm gentle expression, eyes looking into the lens. Faithful to the original cartoon design and proportions, "
                             "not turned into a realistic animal. Soft even studio lighting, plain light grey seamless background, sharp focus. "
                             "No text, no watermark.")
                elif es_criatura(ficha):
                    texto = (f"{pref}. Character identity reference of {sin_punto(ficha['identidad_en'])}{ropa}. "
                             "The whole body visible from the front with margin around it, calm neutral expression, eyes looking into the lens. "
                             "Soft even studio lighting, plain light grey seamless background, sharp focus, realistic surface texture. "
                             "No text, no watermark.")
                elif a.get("variante") == "cuerpo":
                    texto = (f"{pref}. Full-body character reference of {sin_punto(ficha['identidad_en'])}{ropa}. "
                             "Standing in a relaxed neutral pose, the whole body visible from head to shoes with margin around it, facing the camera. "
                             "Soft even studio lighting, plain light grey seamless background. Realistic proportions, natural hands with five fingers. "
                             "No text, no watermark.")
                else:
                    texto = (f"{pref}. Character identity reference portrait of {sin_punto(ficha['identidad_en'])}{ropa}. "
                             "Chest-up, facing the camera, neutral relaxed expression, eyes looking into the lens. "
                             "Soft even studio lighting, plain light grey seamless background, sharp focus on the face, natural skin texture. "
                             "No text, no watermark.")
                es = es or (f"Ancla maestra de {a['entidad']}: cuerpo completo de frente, luz neutra y fondo gris liso." if es_criatura(ficha) or es_animado(ficha) else
                            f"Ancla maestra de {a['entidad']}: {'cuerpo entero' if a.get('variante') == 'cuerpo' else 'retrato de identidad'}, luz neutra y fondo gris liso.")
            elif tipo == "producto":
                texto = (f"{pref}. Product reference photo of {sin_punto(ficha['descripcion_en'])}. "
                         "Three-quarter view, the whole product visible with margin around it, exact proportions, clean sharp edges. "
                         "Soft diffused studio lighting, plain white seamless background. The label area is plain with no readable text. "
                         "No text, no letters, no logo, no watermark.")
                es = es or f"Ancla maestra de {a['entidad']}: packshot en tres cuartos, fondo blanco liso, etiqueta sin texto."
            else:
                encuadre_lugar = f"{sin_punto(a['encuadre_en'])}: " if a.get("encuadre_en") else "Wide establishing shot of "
                texto = (f"{pref}. {encuadre_lugar}{sin_punto(ficha['disposicion_en'])}. "
                         f"Lighting: {sin_punto(_luz(b, ficha.get('luz_base')))}. Empty space, no people. "
                         f"{_orientacion(aspecto)}. No text, no signs, no letters, no watermark.")
                es = es or f"Ancla maestra de {a['entidad']}: plano general vacío con la luz base."
        else:
            conservar = {
                "personaje": "face, facial proportions, hairstyle, skin tone, age and clothing",
                "producto": "shape, proportions, materials, colors and label layout",
                "lugar": "layout of the place, architecture, object positions, materials and colors",
            }[tipo]
            fondo = {"personaje": " Plain light grey seamless background, soft even lighting.",
                     "producto": " Plain white seamless background, soft diffused studio lighting.",
                     "lugar": ""}[tipo]
            if tipo == "personaje" and es_criatura(ficha):
                conservar = "shape, proportions, colors, fur or surface texture and eyes"
            elif tipo == "personaje" and es_animado(ficha):
                conservar = "cartoon design, proportions, colors, surface look, eyes and outfit"
            if tipo == "personaje" and a.get("vestuario"):
                padre = p.ancla((a.get("padres") or [None])[0]) or {}
                if padre.get("vestuario") and padre.get("vestuario") != a.get("vestuario"):
                    conservar = "face, facial proportions, hairstyle, skin tone and age"
                    fondo = f" Wearing {sin_punto(_vestuario(ficha, a['vestuario']))}." + fondo
            texto = (f"Using the attached image of {a['entidad']} as the identity reference, keep exactly the same {conservar}. "
                     f"Change only: {sin_punto(a.get('cambio_en', ''))}. {pref}.{fondo} No text, no watermark.")
            adjuntar = [p.ancla(x).get("archivo", x) if p.ancla(x) else x for x in a.get("padres") or []]
            es = es or f"Derivada de {a['entidad']} ({a.get('variante', '')}) editando su maestra; solo cambia lo indicado en el prompt."
        return {"tipo": "imagen", "ajustes": ajustes, "texto": texto, "es": es, "adjuntar": adjuntar, "guardar": a.get("archivo")}

    # fotograma clave derivado de otro fotograma del mismo clip: misma luz y fondo, solo cambia lo indicado.
    # Evita los saltos de escena de Frames cuando inicio y fin se generan por separado (la-piscina-azul, P04).
    if a.get("derivada_de"):
        base = p.ancla(a["derivada_de"]) or {}
        aspecto = a.get("aspecto") or (p.plan.get("formato") or {}).get("aspecto", "9:16")
        texto = (f"Using the attached image as the same shot a moment earlier or later, keep exactly the same light, colors, "
                 f"background, set, character designs and camera style. Change only: {sin_punto(a.get('cambio_en', ''))}. "
                 f"{pref}. {_orientacion(aspecto)}. No text, no watermark.")
        es = es or f"Fotograma derivado de {a['derivada_de']}: misma luz y fondo; solo cambia lo indicado."
        ajustes = f"Google Flow · Imagen · {NOMBRE_IMAGEN.get(modelo, modelo)} · {aspecto} · x{a.get('salidas', 4)}"
        return {"tipo": "imagen", "ajustes": ajustes, "texto": texto, "es": es,
                "adjuntar": [base.get("archivo", a["derivada_de"])], "guardar": a.get("archivo")}

    # fotograma clave
    pl = p.plano(a.get("plano")) or {}
    final = bool(a.get("final"))
    roles, conservar, vest_frases = [], [], []
    solo_estilo = set(a.get("solo_estilo") or [])
    for n, pid in enumerate(a.get("padres") or [], start=1):
        pa = p.ancla(pid) or {}
        ent = pa.get("entidad", pid)
        t = pa.get("tipo")
        adjuntar.append(pa.get("archivo", pid))
        if pid in solo_estilo:
            # Referencia solo de color, luz y texturas: su composición no debe imponerse al encuadre.
            roles.append(f"{ent} (style reference, image {n})")
            conservar.append(f"only the colors, light and textures of {ent}, not its layout or framing")
            continue
        roles.append(f"{ent} ({TIPO_EN.get(t, 'reference')}, image {n})")
        if t == "personaje":
            conservar.append(f"{ent}'s {rasgos(_ficha(p, ent)[1])} identical to the character reference")
            clave = (pl.get("vestuario") or {}).get(ent) or pa.get("vestuario")
            vest = _vestuario(_ficha(p, ent)[1], clave)
            if vest:
                vest_frases.append(f"{ent} wears {sin_punto(vest)}.")
        elif t == "producto":
            conservar.append(f"{ent} identical to the product reference")
        elif t == "lugar":
            conservar.append(f"the layout of {ent} identical to its location reference")
    estado = pl.get("estado_final") if final else pl.get("estado_inicial")
    momento = "last" if final else "first"
    aspecto = a.get("aspecto") or (p.plan.get("formato") or {}).get("aspecto", "9:16")
    partes = [
        f"{pref}.",
        f"Using the attached references: {lista_en(roles)}.",
        f"Compose the {momento} frame of the shot: {sin_punto(pl.get('encuadre', ''))}, {sin_punto(pl.get('lente', ''))}.",
        frase(mayus(estado or "")),
        " ".join(vest_frases),
        f"Lighting: {sin_punto(_luz(p.biblia, pl.get('iluminacion')))}." if pl.get("iluminacion") else "",
        f"Keep {lista_en(conservar)}." if conservar else "",
        f"Avoid: {', '.join(pl['excluir'])}." if pl.get("excluir") else "",
        f"{_orientacion(aspecto)}. No text, no watermark.",
    ]
    texto = " ".join(x for x in partes if x).replace("  ", " ")
    ajustes = f"Google Flow · Imagen · {NOMBRE_IMAGEN.get(modelo, modelo)} · {aspecto} · x{a.get('salidas', 4)}"
    es = es or f"Fotograma {'final' if final else 'inicial'} de {pl.get('id', '?')}: {pl.get('es', '')}"
    return {"tipo": "imagen", "ajustes": ajustes, "texto": texto, "es": es, "adjuntar": adjuntar, "guardar": a.get("archivo")}


def _linea_audio(b: dict, pl: dict) -> str:
    au = pl.get("audio") or {}
    dlg = au.get("dialogo")
    frases = []
    for d in (dlg if isinstance(dlg, list) else [dlg] if dlg else []):
        if isinstance(d, dict):
            como = f" {sin_punto(d['como'])}" if d.get("como") else ""
            frases.append(f"{d.get('quien', 'The speaker')} says{como}: {sin_punto(d.get('dice', ''))} (no subtitles)")
        else:
            frases.append(f"{sin_punto(str(d))} (no subtitles)")
    dialogo = "; ".join(frases) if frases else "none"
    amb = au.get("ambiente") or ((b.get("audio") or {}).get("ambiente_por_lugar") or {}).get(pl.get("lugar") or "") or "natural room tone"
    s = (f"Audio: Dialogue: {dialogo}. SFX: {sin_punto(au.get('sfx') or 'none')}. "
         f"Ambient: {sin_punto(amb)}. Music: {sin_punto(au.get('musica') or 'none')}.")
    if au.get("no_oir"):
        s += f" Not heard: {sin_punto(au['no_oir'])}."
    return s


def prompt_video(p: Proyecto, pl: dict, cap: dict) -> dict:
    b = p.biblia
    mcap = cap["video"][pl["modelo"]]
    modo = pl["modo"]
    aspecto = (p.plan.get("formato") or {}).get("aspecto", "9:16")
    pref = sin_punto(b["estilo"]["prefijo_en"])
    refs = [p.ancla(r) or {"id": r} for r in pl.get("anclas") or []]
    ents_orden: list[str] = []
    for r in refs:
        if r.get("entidad") and r["entidad"] not in ents_orden:
            ents_orden.append(r["entidad"])
    if pl.get("lugar") and pl["lugar"] not in ents_orden:
        ents_orden.append(pl["lugar"])
    entidades = p.entidades()

    def vest_de(h):
        clave = (pl.get("vestuario") or {}).get(h)
        if not clave:
            clave = next((r.get("vestuario") for r in refs if r.get("entidad") == h and r.get("vestuario")), None)
        return _vestuario(entidades[h][1], clave)

    lineas: list[str] = []
    if modo == "editar":
        texto = f"{frase(mayus(pl.get('correccion_en', '')))} Keep everything else the same."
        adj = [f"clip de {pl.get('clip_base')}"] + [r.get("archivo", r.get("id")) for r in refs]
    else:
        toma_unica = pl.get("toma_unica")
        if toma_unica is None:
            toma_unica = bool(mcap.get("multiplano_por_defecto"))
        lineas.append("No on-screen text, no subtitles." + (" Single continuous shot, no scene cuts." if toma_unica else ""))
        adj: list[str] = []
        if modo in ("frames", "frames_ultimo"):
            s = "The video starts exactly on the provided start frame"
            if modo == "frames_ultimo":
                s += " and ends exactly on the provided end frame"
            lineas.append(s + ".")
            conservar = []
            for h in ents_orden:
                t, ficha = entidades.get(h, (None, {}))
                if t == "personaje":
                    conservar.append(f"the {rasgos(ficha)} of {h}")
                elif t == "producto":
                    conservar.append(ficha.get("nombre_en") or f"the {h} product")
                elif t == "lugar":
                    conservar.append(ficha.get("nombre_en") or "the layout of the place")
            conservar = list(dict.fromkeys(conservar))
            if conservar:
                lineas.append(f"Keep {lista_en(conservar)} exactly as they appear in the start frame.")
            for campo in ("fotograma_inicial", "fotograma_final"):
                k = p.ancla(pl.get(campo) or "")
                if k:
                    adj.append(k.get("archivo", k["id"]))
        elif modo in ("ingredientes", "extender"):
            if modo == "extender":
                lineas.append("Continue the scene in the same single continuous shot.")
                adj.append(f"clip de {pl.get('clip_base')}")
            for h in ents_orden:
                t, ficha = entidades.get(h, (None, {}))
                if t == "personaje":
                    vest = vest_de(h)
                    quien = "creature" if es_criatura(ficha) else "animated character" if es_animado(ficha) else "person"
                    lineas.append(f"{h} is the {quien} from the character reference: {sin_punto(ficha['identidad_en'])}"
                                  + (f", wearing {sin_punto(vest)}." if vest else "."))
                elif t == "producto":
                    lineas.append(f"{h} is the product from the product reference: {sin_punto(ficha['descripcion_en'])}.")
                elif t == "lugar":
                    lineas.append(f"The location is {h} from the location reference: {sin_punto(ficha['disposicion_en'])}.")
            adj += [r.get("archivo", r.get("id")) for r in refs]
        if modo in ("ingredientes", "texto", "extender"):
            if pl.get("encuadre"):
                lineas.append(f"{mayus(sin_punto(pl['encuadre']))}" + (f", {sin_punto(pl['lente'])}." if pl.get("lente") else "."))
            if pl.get("estado_inicial") and modo != "extender":
                lineas.append(f"Opening: {frase(pl['estado_inicial'])}")
        for h in ents_orden:
            t, ficha = entidades.get(h, (None, {}))
            if t == "personaje" and es_criatura(ficha) and h in (pl.get("quietos") or []):
                lineas.append(f"{h} stays completely still in this shot, only blinking, and never shows legs, feet, arms or hands.")
            elif t == "personaje" and es_animado(ficha) and h in (pl.get("quietos") or []):
                lineas.append(f"{h} stays still in this shot, keeping the same pose, only blinking and breathing softly.")
            elif t == "personaje" and (es_criatura(ficha) or es_animado(ficha)) and ficha.get("movimiento_en"):
                lineas.append(f"{h} {frase(ficha['movimiento_en'])}")
        accion = pl.get("accion") or []
        if isinstance(accion, str):
            lineas.append(frase(accion))
        else:
            for paso in accion:
                lineas.append(f"[{paso.get('t')}] {frase(paso.get('en', ''))}")
        if pl.get("camara"):
            lineas.append(f"Camera: {frase(pl['camara'])}")
        if modo not in ("frames", "frames_ultimo"):
            if pl.get("iluminacion"):
                lineas.append(f"Lighting: {frase(_luz(b, pl['iluminacion']))}")
            lineas.append(f"Style: {pref}.")
        if pl.get("estado_final"):
            lineas.append(f"Final moment: {frase(pl['estado_final'])}")
        lineas.append(_linea_audio(b, pl))
        excl = pl.get("excluir") or []
        if excl:
            if pl["modelo"].startswith("omni"):
                lineas.append(f"Do not include {lista_en(excl, 'or')}.")
            else:
                lineas.append(f"Avoid: {', '.join(excl)}.")
        texto = "\n".join(lineas)
        if modo in ("frames", "frames_ultimo"):
            # En Frames no hay personajes adjuntos: @Nombre podría abrir la búsqueda de recursos de Flow.
            texto = nombres_en_frames(texto, entidades)
    ajustes = (f"Google Flow · Video · {MODO_UI[modo]} · {mcap['nombre_ui']} · {aspecto} · {pl.get('duracion')} s · "
               f"x{pl.get('salidas', 1)} · {pl.get('resolucion', '720p')}")
    return {"tipo": "video", "ajustes": ajustes, "texto": texto, "es": pl.get("es", ""), "adjuntar": adj,
            "guardar": f"05-clips/raw/{pl['id']}_v#.mp4"}


def construir_prompts(p: Proyecto, cap: dict, solo: set[str] | None) -> dict:
    out = {}
    for a in p.anclas:
        if solo and a["id"] not in solo:
            continue
        out[a["id"]] = prompt_ancla(p, a)
    for pl in p.plan.get("planos", []):
        if solo and pl["id"] not in solo:
            continue
        if pl.get("modelo") in cap.get("video", {}) and pl.get("modo") in MODO_UI:
            out[pl["id"]] = prompt_video(p, pl, cap)
    for k, v in out.items():
        v["huella"] = huella(v["texto"]) if v["texto"] else None
        v["palabras"] = palabras(v["texto"])
    return out


def avisos_longitud(p: Proyecto, prompts: dict) -> list[str]:
    avisos = []
    for pid, v in prompts.items():
        if v["tipo"] != "video":
            continue
        pl = p.plano(pid) or {}
        lim = 180 if pl.get("modelo", "").startswith("omni") and pl.get("modo", "").startswith("frames") else 250
        if v["palabras"] > lim:
            avisos.append(f"prompt {pid}: {v['palabras']} palabras (orientativo ≤ {lim}); recorta lo que la imagen ya muestra")
    return avisos


def escribir_prompts_md(p: Proyecto, prompts: dict) -> Path:
    hoy = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    plan = p.plan
    lineas = [f"# Prompts · {plan.get('proyecto')} · plan v{plan.get('version')} · biblia v{p.biblia.get('version')}",
              "", f"Generado: {hoy} con `flowprompt.py prompts`. No edites este archivo: cambia los JSON y vuelve a generarlo.",
              "", "Cada bloque: la línea de ajustes de Flow, el prompt en inglés para copiar, el resumen en español, qué adjuntar y dónde guardar el resultado.",
              "En Flow, nombra cada ancla subida igual que su handle sin @ (`Valeria`, `BolsaOrigen`): así `@` la encuentra en el cuadro del prompt.", ""]
    secciones = [
        ("1. Anclas maestras (nivel 0)", lambda a: a.get("tipo") in TIPOS_ENTIDAD and a.get("nivel") == 0),
        ("2. Anclas derivadas (nivel 1)", lambda a: a.get("tipo") in TIPOS_ENTIDAD and a.get("nivel") == 1),
        ("3. Fotogramas clave (nivel 2)", lambda a: a.get("tipo") == "fotograma"),
    ]
    for titulo, filtro in secciones:
        grupo = [a for a in p.anclas if filtro(a) and a["id"] in prompts]
        if not grupo:
            continue
        lineas += [f"## {titulo}", ""]
        for a in grupo:
            v = prompts[a["id"]]
            lineas += [f"### {a['id']} · {a.get('entidad') or a.get('plano')} · {a.get('variante', 'fotograma final' if a.get('final') else 'fotograma inicial' if a.get('tipo') == 'fotograma' else '')} · estado: {a.get('estado', 'pendiente')}", "",
                       f"`{v['ajustes']}`", ""]
            if v["texto"]:
                lineas += ["```text", v["texto"], "```", ""]
            lineas.append(f"En español: {v['es']}")
            if v["adjuntar"]:
                lineas.append(f"Adjuntar: {', '.join(v['adjuntar'])}")
            lineas += [f"Guardar como: `{v['guardar']}`", ""]
    videos = [pl for pl in plan.get("planos", []) if pl["id"] in prompts]
    if videos:
        lineas += ["## 4. Video por plano", ""]
        for pl in videos:
            v = prompts[pl["id"]]
            lineas += [f"### {pl['id']} · {pl.get('papel', '')} · {pl.get('duracion')} s · uso {pl.get('uso')}", "",
                       f"`{v['ajustes']}`", "", "```text", v["texto"], "```", "",
                       f"En español: {v['es']}"]
            if v["adjuntar"]:
                lineas.append(f"Adjuntar: {', '.join(v['adjuntar'])}")
            lineas += [f"Guardar como: `{v['guardar']}` (y revisar con `qc_clips.py {pl['id']}`)", ""]
    ruta = p.raiz / "04-prompts" / "PROMPTS.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta


# ----------------------------------------------------------------------------- documentos legibles

def escribir_biblia_md(p: Proyecto) -> Path:
    b = p.biblia
    L = [f"# Biblia visual · {b.get('proyecto')} · v{b.get('version')}", "",
         "Generada desde `biblia.json`. Los textos en inglés se pegan literalmente en los prompts.", "",
         "## Estilo", "", f"**{(b.get('estilo') or {}).get('lenguaje', '')}.** {(b.get('estilo') or {}).get('es', '')}", "",
         f"Prefijo: `{(b.get('estilo') or {}).get('prefijo_en', '')}`", "", "## Paleta", "",
         "| Papel | Color | Nombre en los prompts |", "| --- | --- | --- |"]
    for c in b.get("paleta") or []:
        L.append(f"| {c.get('rol', '')} | `{c.get('hex', '')}` | {c.get('nombre_en', '')} |")
    L += ["", "## Iluminación", ""]
    for k, v in (b.get("iluminaciones") or {}).items():
        L.append(f"- **{k}:** {v.get('es', '')}  \n  `{v.get('en', '')}`")
    if b.get("texturas_en"):
        L += ["", "## Texturas", "", ", ".join(b["texturas_en"])]
    for titulo, clave, campo in (("Personajes", "personajes", "identidad_en"), ("Lugares", "lugares", "disposicion_en"),
                                 ("Productos", "productos", "descripcion_en")):
        fichas = b.get(clave) or []
        if not fichas:
            continue
        L += ["", f"## {titulo}", ""]
        for f in fichas:
            L += [f"### {f.get('handle')}", "", f.get("es", ""), "", f"`{f.get(campo, '')}`", ""]
            for vk, vv in (f.get("vestuario") or {}).items():
                L.append(f"- Vestuario {vk}: `{vv}`")
            if f.get("no_cambiar"):
                L.append(f"- No cambiar: {', '.join(f['no_cambiar'])}")
            if f.get("voz"):
                L.append(f"- Voz: {f['voz']}")
            if f.get("eje"):
                L.append(f"- Eje: {f['eje']}")
            if f.get("luz_base"):
                L.append(f"- Luz base: {f['luz_base']}")
            if f.get("texto_real"):
                L.append(f"- Texto real (en el montaje): {f['texto_real']}")
            anclas = [a for a in p.anclas if a.get("entidad") == f.get("handle")]
            if anclas:
                L.append("- Anclas: " + ", ".join(f"{a['id']} ({a.get('estado', 'pendiente')})" for a in anclas))
            L.append("")
    tx, au = b.get("texto") or {}, b.get("audio") or {}
    L += ["## Texto en imagen", "", f"Política: {tx.get('politica', '')}. {tx.get('nota', '')}", "",
          "## Audio", "", f"Política: **{au.get('politica', '')}**. Narración: {au.get('narracion', '')}. Música: {au.get('musica', '')}."]
    for h, amb in (au.get("ambiente_por_lugar") or {}).items():
        L.append(f"- Ambiente de {h}: `{amb}`")
    ruta = p.raiz / "01-biblia" / "BIBLIA.md"
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")
    return ruta


def escribir_storyboard_md(p: Proyecto) -> Path:
    plan = p.plan
    tl = {x["id"]: x for x in linea_de_tiempo(plan)}
    total = max((x["inicio"] + x["duracion"] for x in tl.values()), default=0)
    fmt = plan.get("formato") or {}
    L = [f"# Storyboard · {plan.get('proyecto')} · v{plan.get('version')} (brief v{plan.get('brief_version')})", "",
         f"Formato {fmt.get('aspecto')} · objetivo {fmt.get('duracion_objetivo')} s · montaje {total:.1f} s · {len(tl)} planos", "",
         "Generado desde `plan.json` con `flowprompt.py storyboard`.", ""]
    curva = plan.get("curva") or {}
    if curva:
        L += [f"Curva: re-ganchos en {curva.get('reganches', [])} s · pausas {curva.get('pausas', [])}", ""]
    L += ["| Plano | En el video | Papel | Qué pasa | Flow | Enlace |", "| --- | --- | --- | --- | --- | --- |"]
    for pl in plan.get("planos", []):
        t = tl.get(pl["id"], {})
        en = f"{t.get('inicio', 0):.1f}–{t.get('inicio', 0) + t.get('duracion', 0):.1f} s"
        enl = pl.get("enlace") or {}
        L.append(f"| {pl['id']} | {en} | {pl.get('papel', '')} | {pl.get('es', '')} | {pl.get('modo')} · {pl.get('modelo')} · {pl.get('duracion')} s | "
                 f"{enl.get('tipo', '')} → {enl.get('a') or 'fin'} |")
    for pl in plan.get("planos", []):
        t = tl.get(pl["id"], {})
        au = pl.get("audio") or {}
        enl = pl.get("enlace") or {}
        L += ["", f"### {pl['id']} · {pl.get('escena', '')} · {t.get('inicio', 0):.2f}–{t.get('inicio', 0) + t.get('duracion', 0):.2f} s · {pl.get('papel', '')}", "",
              f"- **Intención:** {pl.get('intencion', '')}",
              f"- **Cámara y composición:** {pl.get('encuadre', '')}; {pl.get('lente', '')}; {pl.get('camara', '')}.",
              f"- **Iluminación:** {pl.get('iluminacion', '')}.",
              f"- **Inicio:** {pl.get('estado_inicial', '')}",
              "- **Acción:**"]
        acc = pl.get("accion") or []
        for paso in (acc if isinstance(acc, list) else [{"t": "", "en": acc}]):
            L.append(f"  - {paso.get('t', '')}: {paso.get('en', '')}")
        L += [f"- **Final:** {pl.get('estado_final', '')}",
              f"- **Sonido:** diálogo {au.get('dialogo') or 'ninguno'}; efectos {au.get('sfx') or 'ninguno'}; música {au.get('musica') or 'sin declarar'}.",
              f"- **Enlace:** {enl.get('tipo', '')} → {enl.get('a') or 'fin'}. {enl.get('detalle', '')}",
              f"- **Flow:** {MODO_UI.get(pl.get('modo'), pl.get('modo'))} · {pl.get('modelo')} · {pl.get('duracion')} s · x{pl.get('salidas', 1)} · "
              f"inicio {pl.get('fotograma_inicial') or '—'} · fin {pl.get('fotograma_final') or '—'} · anclas {', '.join(pl.get('anclas') or [])} · uso {pl.get('uso')}"]
    ruta = p.raiz / "03-storyboard" / "STORYBOARD.md"
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")
    return ruta


# ----------------------------------------------------------------------------- CLI

def imprimir(inf: Informe, extra_avisos: list[str] | None = None) -> None:
    avisos = inf.avisos + (extra_avisos or [])
    for e in inf.errores:
        print(f"  ERROR  {e}")
    for a in avisos:
        print(f"  AVISO  {a}")
    print(f"\n{len(inf.errores)} errores · {len(avisos)} avisos")


def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validar", help="comprueba biblia, anclas y plan")
    v.add_argument("proyecto")
    v.add_argument("--para-video", action="store_true", help="exige anclas aprobadas (antes de gastar créditos)")
    pr = sub.add_parser("prompts", help="genera 04-prompts/PROMPTS.md y prompts.json")
    pr.add_argument("proyecto")
    pr.add_argument("--solo", help="ids separados por comas (anclas o planos)")
    pr.add_argument("--forzar", action="store_true", help="genera aunque haya errores")
    for nombre in ("biblia", "storyboard"):
        sp = sub.add_parser(nombre)
        sp.add_argument("proyecto")
    args = ap.parse_args(argv)

    p = Proyecto(args.proyecto)
    cap = capacidades()
    if args.cmd == "validar":
        inf = validar(p, cap, para_video=args.para_video)
        print(f"Validación de {p.raiz.name} (capacidades de Flow verificadas el {cap.get('verificado')})")
        imprimir(inf)
        return 1 if inf.errores else 0
    if args.cmd == "prompts":
        inf = validar(p, cap)
        if inf.errores and not args.forzar:
            imprimir(inf)
            print("Corrige los errores (o usa --forzar) antes de generar prompts.")
            return 1
        solo = set(args.solo.split(",")) if args.solo else None
        prompts = construir_prompts(p, cap, solo)
        anterior = {}
        ruta_json = p.ruta("prompts")
        if ruta_json.exists():
            anterior = json.loads(ruta_json.read_text(encoding="utf-8")).get("prompts", {})
        for k, val in prompts.items():
            prev = anterior.get(k) or {}
            val["version"] = prev.get("version", 0) + (1 if prev.get("huella") != val["huella"] else 0) or 1
        merged = {**anterior, **prompts}
        escribir_json(ruta_json, {"generado": dt.datetime.now().isoformat(timespec="seconds"),
                                  "plan_version": p.plan.get("version"), "biblia_version": p.biblia.get("version"),
                                  "prompts": merged})
        md = escribir_prompts_md(p, merged)
        imprimir(inf, avisos_longitud(p, prompts))
        print(f"Prompts: {md}\n         {ruta_json}")
        return 0
    if args.cmd == "biblia":
        print(escribir_biblia_md(p))
        return 0
    if args.cmd == "storyboard":
        print(escribir_storyboard_md(p))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
