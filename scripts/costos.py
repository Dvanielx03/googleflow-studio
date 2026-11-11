#!/usr/bin/env python3
"""costos · seguimiento de puntos de Google Flow y tokens de Claude de un video, por etapa.

Uso:
  python costos.py sesion  <proyecto> --id <sessionId> [--desde ISO] [--hasta ISO]
  python costos.py hito    <proyecto> --nombre "Puerta 2" [--fecha ISO]
  python costos.py saldo   <proyecto> --puntos 194 [--nota "..."] [--fecha ISO]
  python costos.py informe <proyecto> [--previo "Desarrollo de la skill"]

Fuentes:
  · Puntos de Flow declarados: campo `creditos` de cada generación en bitacora.jsonl
    (el que muestra Flow: «La generación consumirá N puntos»).
  · Puntos medidos: lecturas del saldo de la cuenta («N puntos de Google Flow»), con `saldo`.
  · Tokens de Claude: registros de las sesiones (~/.claude/projects/**/*.jsonl). Cada respuesta se cuenta una vez
    (requestId + message.id, máximo por tipo). Solo se leen números,
    nunca el texto de los mensajes.
Las etapas son los tramos entre hitos. Escribe costos.json (datos) y costos.md (informe) en el proyecto.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import RUTAS, escribir_json, leer_json, utf8_stdout  # noqa: E402

TIPOS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
CORTOS = ("entrada", "salida", "caché escrita", "caché leída")
import os  # noqa: E402
PROYECTOS_CLAUDE = Path(os.environ.get("CLAUDE_PROJECTS_DIR") or Path.home() / ".claude" / "projects")


def ahora_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def a_fecha(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def local(iso: str) -> str:
    return a_fecha(iso).astimezone().strftime("%d %b %H:%M")


def cargar(raiz: Path) -> dict:
    ruta = raiz / "costos.json"
    datos = leer_json(ruta) if ruta.exists() else {}
    for k in ("sesiones", "hitos", "saldos"):
        datos.setdefault(k, [])
    return datos


def guardar(raiz: Path, datos: dict) -> None:
    datos["hitos"].sort(key=lambda h: h["fecha"])
    datos["saldos"].sort(key=lambda s: s["fecha"])
    escribir_json(raiz / "costos.json", datos)


# ----------------------------------------------------------------------------- tokens

def archivos_de(sesiones: set[str]) -> list[Path]:
    """Registros de las sesiones (y de sus subagentes) en ~/.claude/projects."""
    out = []
    for s in sesiones:
        out += list(PROYECTOS_CLAUDE.glob(f"*/{s}.jsonl"))
        out += list(PROYECTOS_CLAUDE.glob(f"*/{s}/**/*.jsonl"))
    return sorted(set(out))


def mensajes(sesiones: list[dict]) -> list[dict]:
    """Respuestas únicas de Claude dentro de las ventanas registradas: [{ts, uso, modelo}]."""
    ventanas = {s["id"]: (a_fecha(s["desde"]) if s.get("desde") else None, a_fecha(s["hasta"]) if s.get("hasta") else None)
                for s in sesiones}
    vistos: dict[tuple, dict] = {}
    for ruta in archivos_de(set(ventanas)):
        with ruta.open(encoding="utf-8", errors="replace") as f:
            for linea in f:
                if '"usage"' not in linea:
                    continue
                try:
                    d = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                sid, ts = d.get("sessionId"), d.get("timestamp")
                if sid not in ventanas or not ts:
                    continue
                desde, hasta = ventanas[sid]
                t = a_fecha(ts)
                if (desde and t < desde) or (hasta and t > hasta):
                    continue
                m = d.get("message") or {}
                uso = m.get("usage") or {}
                if not uso:
                    continue
                clave = (d.get("requestId"), m.get("id"), None if d.get("requestId") or m.get("id") else d.get("uuid"))
                rec = vistos.setdefault(clave, {"ts": ts, "modelo": m.get("model"), "uso": dict.fromkeys(TIPOS, 0)})
                for k in TIPOS:  # líneas repetidas del mismo mensaje: se toma el máximo
                    rec["uso"][k] = max(rec["uso"][k], int(uso.get(k) or 0))
    return sorted(vistos.values(), key=lambda r: r["ts"])


def etapa_de(ts: str, hitos: list[dict], previo: str) -> str:
    nombre = previo
    for h in hitos:
        if a_fecha(h["fecha"]) <= a_fecha(ts):
            nombre = h["nombre"]
    return nombre


# ----------------------------------------------------------------------------- informe

def fmt(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def informe(raiz: Path, previo: str) -> str:
    datos = cargar(raiz)
    hitos = sorted(datos["hitos"], key=lambda h: h["fecha"])
    orden = [previo] + [h["nombre"] for h in hitos]

    # tokens
    tok = defaultdict(lambda: dict.fromkeys(TIPOS, 0))
    resp = defaultdict(int)
    modelos = defaultdict(int)
    for m in mensajes(datos["sesiones"]):
        e = etapa_de(m["ts"], hitos, previo)
        for k in TIPOS:
            tok[e][k] += m["uso"][k]
        resp[e] += 1
        modelos[m["modelo"]] += 1

    # puntos declarados (bitácora)
    pts = defaultdict(float)
    gens = defaultdict(lambda: defaultdict(int))
    ruta_b = raiz / RUTAS["bitacora"]
    if ruta_b.exists():
        for linea in ruta_b.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            g = json.loads(linea)
            e = etapa_de(g["fecha_utc"] if g.get("fecha_utc") else
                         dt.datetime.fromisoformat(g["fecha"]).astimezone(dt.timezone.utc).isoformat(), hitos, previo)
            pts[e] += float(g.get("creditos") or 0)
            gens[e][g.get("tipo") or "?"] += 1

    L = [f"# Costes · {raiz.name}", "", f"Actualizado: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} con `costos.py informe`.", "",
         "## Por etapa", "",
         "| Etapa | Desde | Respuestas de Claude | Tokens (sin caché leída) | Caché leída | Generaciones en Flow | Puntos de Flow |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    inicios = {previo: datos["sesiones"][0].get("desde") if datos["sesiones"] else None}
    inicios.update({h["nombre"]: h["fecha"] for h in hitos})
    tot = dict.fromkeys(TIPOS, 0)
    tot_pts, tot_resp = 0.0, 0
    for e in orden:
        if e not in tok and e not in pts and e not in gens:
            continue
        t = tok[e]
        sin_cache = t["input_tokens"] + t["output_tokens"] + t["cache_creation_input_tokens"]
        g = ", ".join(f"{n} {k}" for k, n in gens[e].items()) or "—"
        L.append(f"| {e} | {local(inicios[e]) if inicios.get(e) else '—'} | {resp[e]} | {fmt(sin_cache)} | {fmt(t['cache_read_input_tokens'])} | {g} | {pts[e]:g} |")
        for k in TIPOS:
            tot[k] += t[k]
        tot_pts += pts[e]
        tot_resp += resp[e]
    sin_cache = tot["input_tokens"] + tot["output_tokens"] + tot["cache_creation_input_tokens"]
    L.append(f"| **Total** | | {tot_resp} | {fmt(sin_cache)} | {fmt(tot['cache_read_input_tokens'])} | | {tot_pts:g} |")
    L += ["", "## Tokens de Claude por tipo", "", "| Tipo | Tokens |", "| --- | --- |"]
    for k, c in zip(TIPOS, CORTOS):
        L.append(f"| {c} | {fmt(tot[k])} |")
    L.append(f"| total | {fmt(sum(tot.values()))} |")
    if modelos:
        L += ["", "Modelos: " + ", ".join(f"{m} ({n} respuestas)" for m, n in modelos.items() if m)]
    L += ["", "La caché leída es casi todo el volumen y cuenta mucho menos contra los límites que la entrada, la salida o la caché escrita.",
          "Por eso se muestra aparte.", "", "## Saldo de Google Flow", ""]
    if datos["saldos"]:
        L += ["| Lectura | Puntos | Nota |", "| --- | --- | --- |"]
        for s in datos["saldos"]:
            L.append(f"| {local(s['fecha'])} | {s['puntos']:g} | {s.get('nota', '')} |")
        if len(datos["saldos"]) >= 2:
            medido = datos["saldos"][0]["puntos"] - datos["saldos"][-1]["puntos"]
            L += ["", f"Consumo medido entre la primera y la última lectura: **{medido:g} puntos**. "
                      f"Declarado en la bitácora en ese tramo: {sum(pts.values()):g} puntos."]
            if medido < 0:
                L.append("El saldo subió: hubo una recarga o un restablecimiento entre lecturas.")
    else:
        L.append("Sin lecturas del saldo todavía (`costos.py saldo`).")
    L += ["", "## ElevenLabs", ""]
    if datos.get("elevenlabs"):
        L += ["| Fecha | Generado | Consumo (caracteres/créditos) |", "| --- | --- | --- |"]
        total_el = 0
        for e in datos["elevenlabs"]:
            L.append(f"| {local(e['fecha'])} | {', '.join(e.get('generado', []))} | {e.get('consumo') if e.get('consumo') is not None else 'sin medir'} |")
            total_el += e.get("consumo") or 0
        L += ["", f"Total ElevenLabs: **{total_el}**."]
    else:
        L.append("Sin generaciones todavía (`elevenlabs.py generar`).")
    texto = "\n".join(L) + "\n"
    (raiz / "costos.md").write_text(texto, encoding="utf-8")
    return texto


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sesion")
    s.add_argument("proyecto")
    s.add_argument("--id", required=True)
    s.add_argument("--desde")
    s.add_argument("--hasta")
    h = sub.add_parser("hito")
    h.add_argument("proyecto")
    h.add_argument("--nombre", required=True)
    h.add_argument("--fecha")
    sa = sub.add_parser("saldo")
    sa.add_argument("proyecto")
    sa.add_argument("--puntos", type=float, required=True)
    sa.add_argument("--nota", default="")
    sa.add_argument("--fecha")
    i = sub.add_parser("informe")
    i.add_argument("proyecto")
    i.add_argument("--previo", default="Antes del primer hito")
    args = ap.parse_args(argv)

    raiz = Path(args.proyecto).resolve()
    datos = cargar(raiz)
    if args.cmd == "sesion":
        if not archivos_de({args.id}):
            print(f"Aviso: no encuentro el registro de la sesión {args.id} en {PROYECTOS_CLAUDE}")
        datos["sesiones"] = [x for x in datos["sesiones"] if x["id"] != args.id]
        datos["sesiones"].append({k: v for k, v in {"id": args.id, "desde": args.desde, "hasta": args.hasta}.items() if v})
        guardar(raiz, datos)
        print(f"Sesión {args.id} registrada" + (f" desde {args.desde}" if args.desde else ""))
    elif args.cmd == "hito":
        datos["hitos"] = [x for x in datos["hitos"] if x["nombre"] != args.nombre]
        datos["hitos"].append({"nombre": args.nombre, "fecha": args.fecha or ahora_iso()})
        guardar(raiz, datos)
        print(f"Hito «{args.nombre}» registrado")
    elif args.cmd == "saldo":
        datos["saldos"].append({"fecha": args.fecha or ahora_iso(), "puntos": args.puntos, "nota": args.nota})
        guardar(raiz, datos)
        print(f"Saldo de Flow: {args.puntos:g} puntos")
    else:
        print(informe(raiz, args.previo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
