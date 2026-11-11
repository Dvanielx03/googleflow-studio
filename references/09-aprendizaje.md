# Etapa 7 · Automatización y aprendizaje

La skill mejora con cada video. Lo que funcionó se convierte en patrón; lo que falló, en antipatrón. Para eso cada generación se registra con su prompt, sus ajustes y su resultado.

## La bitácora del proyecto

`<proyecto>/bitacora.jsonl`: una línea por generación (imagen o video). Se escribe con:

```bash
python scripts/bitacora.py registrar <proyecto> --plano P01 --tipo video --modo frames --modelo omni-1.2 \
  --prompt-id P01 --version 2 --resultado aprobado --nota "intervalos [0-3s] respetados" --creditos 20
python scripts/bitacora.py registrar <proyecto> --plano P03 --tipo video --modo ingredientes --modelo veo-3.1-lite \
  --prompt-id P03 --resultado rechazado --defectos identidad,manos --nota "cara más joven que la maestra"
```

Guarda automáticamente fecha, el texto del prompt (desde `04-prompts/prompts.json`) y su huella, las anclas usadas y los ajustes del plan. `--resultado`: `aprobado`, `corregido` (aprobado tras editar o recortar), `rechazado`.

Defectos normalizados (para poder contarlos): `identidad`, `manos`, `deformacion`, `producto`, `lugar`, `movimiento`, `continuidad`, `storyboard`, `texto`, `audio`, `cortes`, `tecnico`.

## Leer lo aprendido

```bash
python scripts/bitacora.py resumen <proyecto>
```

Muestra, por modo y modelo: generaciones, aprobadas a la primera, intentos medios por plano aprobado, defectos más frecuentes y créditos gastados. Con `--todos <carpeta>` agrega varios proyectos.

Preguntas que responde: ¿Frames da menos deriva de identidad que Ingredients con estos personajes? ¿Omni respeta los intervalos? ¿Qué defecto aparece más con manos en primer plano? ¿Cuánto cuesta de verdad un plano aprobado?

## Promover un patrón

Cuando una técnica funciona en al menos dos planos (o dos proyectos) y la bitácora lo muestra, pasa a la biblioteca de la skill:

```bash
python scripts/bitacora.py promover --tipo patron --titulo "Manos con objeto: plano medio, no primer plano" \
  --contexto "Omni 1.2, Frames, producto en mano" --tecnica "Encuadrar a medium shot y nombrar 'five natural fingers'" \
  --evidencia "proyecto cafe-origen: P02 y P05 aprobados a la primera; antes 3 rechazos por manos"
```

Escribe en `assets/patrones/patrones-probados.md` (patrones o antipatrones), con fecha y evidencia. Antes de planificar un proyecto nuevo, **lee ese archivo**: sus patrones tienen prioridad sobre las recomendaciones generales de las guías, porque están probados con las herramientas y el estilo del usuario.

Reglas para la biblioteca:
- Un patrón sin evidencia (proyecto, planos, resultado) no entra.
- Si un patrón deja de funcionar (Flow cambió el modelo), se marca «obsoleto» con la fecha, no se borra.
- Un fallo aislado no es un antipatrón: hacen falta dos.

## Costes: puntos de Flow y tokens de Claude

Cada proyecto lleva sus costes en `costos.json` y los resume en `costos.md`:

```bash
python scripts/costos.py sesion  <proyecto> --id <sessionId> --desde <ISO>   # al empezar (y en cada sesión nueva)
python scripts/costos.py hito    <proyecto> --nombre "2 · Biblia y anclas maestras"   # en cada puerta
python scripts/costos.py saldo   <proyecto> --puntos 194 --nota "antes de la muestra"  # antes y después de cada lote de video
python scripts/costos.py informe <proyecto> --previo "0 · Antes del proyecto"
```

- **Puntos declarados:** los que Flow anuncia antes de generar («La generación consumirá N puntos»), registrados con `bitacora.py registrar --puntos N`.
- **Puntos medidos:** la diferencia entre lecturas del saldo de la cuenta (menú del plan en Flow: «N puntos de Google Flow»). Si no coinciden con los declarados, algo se generó fuera de la bitácora o hubo un restablecimiento.
- **Tokens de Claude:** se leen de los registros de la sesión (`~/.claude/projects/**/<sessionId>.jsonl`), una vez por respuesta (requestId + message.id). Solo números, nunca el texto. La caché leída se muestra aparte porque es casi todo el volumen y cuenta mucho menos contra los límites.

Al presentar cada puerta, incluye la tabla de `costos.md`: lo gastado hasta ahí y la estimación de lo siguiente.

## Mantener la skill al día

| Qué | Cuándo | Cómo |
| --- | --- | --- |
| `assets/flow_capacidades.json` | Al empezar cada proyecto si tiene más de un mes, o cuando Flow anuncie un modelo | Compara con el selector de Flow y la página de modelos; actualiza cifras y la fecha |
| `references/01-skills-investigadas.md` | Cada 2–3 meses | Repite la búsqueda de skills descrita allí |
| `patrones-probados.md` | Al cerrar cada proyecto | `bitacora.py resumen` → promover lo que se repitió |
| Plantillas de prompt | Cuando un patrón cambie una plantilla | Edita `scripts/flowprompt.py`, documenta el cambio en `05-prompts-flow.md` y ejecuta `python scripts/probar.py` |

## Automatización disponible

| Paso | Herramienta | Automatiza |
| --- | --- | --- |
| Crear proyecto | `nuevo_proyecto.py` | Carpetas, plantillas, bitácora vacía |
| Biblia y storyboard legibles | `flowprompt.py biblia`, `storyboard` | Documentos para aprobar desde los JSON |
| Validar | `flowprompt.py validar` | Anclas aprobadas, límites de referencias, duraciones por modelo, suma de tiempos, texto que se cuela, referencias vagas, audio declarado |
| Prompts | `flowprompt.py prompts` | Prompts de anclas, fotogramas clave y video con su línea de ajustes |
| QC por clip | `qc_clips.py` | Formato, cortes, parpadeo, congelados, deriva de color, fidelidad al fotograma clave, hoja de revisión, último fotograma |
| Montaje | `a_motion_studio.py` | Secuencias, audio y línea de tiempo para motion-studio; animatic |
| Aprendizaje | `bitacora.py` | Registro, estadísticas y biblioteca de patrones |

La generación en Flow la hace el usuario con los prompts listos o, si lo autoriza, el agente en el navegador (ver «Quién opera Flow» en `SKILL.md`).
