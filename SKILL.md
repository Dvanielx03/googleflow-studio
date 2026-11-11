---
name: googleflow-studio
description: >-
  Producción audiovisual completa de videos generados con IA en Google Flow (Omni Flash, Veo 3.1, Nano Banana), realistas o animados, con personajes, productos y lugares idénticos de principio a fin gracias a un sistema de imágenes ancla. Úsala SIEMPRE que el usuario quiera convertir una idea en un video hecho en Google Flow, con Veo, Omni o Nano Banana, o hable de imagen ancla, biblia visual, consistencia de personaje, storyboard o prompts para Flow, fotogramas clave, o revisar clips generados por IA; aunque no nombre esta skill. Recorre preproducción (brief, biblia visual, anclas, planificación de planos y audio), producción en Flow con control de calidad por clip y postproducción con motion-studio, y aprende de cada proyecto con una bitácora. Tiene prioridad sobre motion-studio cuando las imágenes salen de Flow; motion-studio se usa dentro de ella para montar, mezclar y exportar.
---

# GoogleFlow Studio · Dirección de videos con Google Flow

Conviertes ideas en videos generados con Google Flow siguiendo las etapas de una producción audiovisual real. El agente dirige: traduce la idea en guion, identidad visual, planos, sonido y montaje; el usuario aprueba el propósito, la experiencia y el gasto. No preguntes técnicas que te toca resolver a ti.

**Principio central: se decide en imagen, se anima en video.** Las imágenes de Flow (Nano Banana) no gastan créditos; el video sí. Todo lo que define el video (quién es cada personaje, cómo es el lugar, cómo empieza cada plano) se resuelve y se aprueba como imagen ancla antes de generar un solo clip. El video solo anima decisiones aprobadas. Así todas las escenas salen de las mismas anclas, los escenarios son los del storyboard y el personaje es el mismo de principio a fin.

Esta skill se apoya en **motion-studio** (instalada en `~/.claude/skills/motion-studio`): usa su brief, su ficha de plano, sus avisos de aprobación y, para la postproducción, su montaje, mezcla, revisión y exportación. No uses HyperFrames, Remotion ni otro framework de video. Resuelve `scripts/`, `references/` y `assets/` desde la carpeta de este `SKILL.md`.

## Reglas de producción del usuario (mandan sobre todo lo demás)

Detalle en `references/10-reglas-de-produccion.md`.

1. **Análisis de referencia antes de generar:** recorre la referencia segundo a segundo (encuadres, primera persona, cámara, ritmo, música, efectos, duración, transiciones y cuerpo del espectador) y escribe `REFERENCIA.md`. Traslada su lenguaje, no solo su tema.
2. **Continuidad visual:** cada clip continúa al anterior. Su fotograma inicial es el último fotograma aprobado del anterior (relevo) o un fotograma clave, con un fotograma clave como final cuando hay que volver a la identidad aprobada. El inicio y el fin de un mismo clip comparten luz y fondo (se derivan uno del otro), y un clip no recorre mucha distancia y cambia la postura del personaje a la vez: se divide con un fotograma intermedio. La toma no debe notarse cortada.
3. **Escenas de ~15 s** divididas en clips de 4–6 s, con la duración ajustada a la historia.
4. **Audio:** los sonidos de Flow se conservan si el usuario los aprueba; ElevenLabs cubre lo que falte (`scripts/elevenlabs.py`); la música entra desde su inicio y suena hasta el final en la mezcla del render. **Voces: se pregunta antes**, por defecto una sola frase corta con el tono cuidado, y se entrega una muestra solo de audio para auditar antes de mezclarla.
5. **Auditoría obligatoria:** cada clip se revisa y se presenta al usuario. No se une nada sin su aprobación explícita, clip por clip.

## Antes de empezar

1. Lee `assets/patrones/patrones-probados.md`: lo aprendido en proyectos anteriores manda sobre las recomendaciones generales.
2. Comprueba la fecha de `assets/flow_capacidades.json`. Si tiene más de un mes, o el usuario menciona un modelo que no aparece, contrasta con el selector de Flow y la página de modelos (`references/09-aprendizaje.md`) y actualízala. Hoy (verificado el 2026-11-11): Omni Flash 1.2 es el modelo principal; Veo 3.1 Fast y Quality se retiran el 5 de diciembre de 2026.
3. Pregunta, si no lo sabes, qué plan de Google AI tiene el usuario (Extend, clips de 15 s y upscale son de pago) y quién operará Flow (abajo).

## Las etapas

| Fase | Etapa | Qué produce | Guía |
| --- | --- | --- | --- |
| Transversal | 1 · Investigación de skills | Qué técnicas externas se integraron y cómo repetir la búsqueda | `references/01-skills-investigadas.md` |
| Preproducción | 0 · Brief y guion | `BRIEF.md` y guion con acciones visibles (motion-studio: `references/preproduccion.md`) | motion-studio |
| | 2 · Biblia visual | `biblia.json` → `BIBLIA.md`: estilo, paleta, luces, texturas, personajes, lugares, productos, política de texto y audio | `references/02-biblia-visual.md` |
| | 3 · Imágenes ancla | `anclas.json` + imágenes: maestras → derivadas → fotogramas clave | `references/03-imagenes-ancla.md` |
| | 4 · Planificación cinematográfica | `plan.json` → `STORYBOARD.md`: encuadre, cámara, acción, duración, ritmo, enlaces, modo de Flow | `references/04-planificacion-cinematografica.md` |
| | 5 · Diseño de audio | Política de audio y las cuatro líneas de cada plano | `references/06-produccion-audio.md` |
| Producción | Prompts y generación en Flow | `PROMPTS.md`; clips en `05-clips/raw/` | `references/05-prompts-flow.md` |
| | 6 · Control de calidad por clip | `07-qc/<plano>/`: hoja, medidas, último fotograma; escalera de corrección | `references/07-control-calidad.md` |
| Postproducción | Montaje, audio y exportación | Video final con motion-studio | `references/08-montaje-motion-studio.md` |
| | 6 · Control de calidad global | Rúbricas con evidencia, `REVISION.md` | `references/07-control-calidad.md` |
| Transversal | 7 · Automatización y aprendizaje | `bitacora.jsonl`, estadísticas, patrones promovidos | `references/09-aprendizaje.md` |

Mantén la preparación proporcional: un clip de producto de 3 planos no necesita animatic ni derivadas de cada ángulo; un corto de 20 planos con dos personajes, sí.

## Puertas de aprobación

Usa los avisos con opciones de motion-studio (`references/avisos-creativos.md` de esa skill): una decisión por aviso, la opción recomendada primero, el efecto visible explicado en palabras sencillas. Registra en `BRIEF.md` cada aprobación con las palabras del usuario. Una aprobación cubre solo su alcance; el silencio o una corrección parcial no aprueban nada.

| Puerta | Se presenta | Autoriza |
| --- | --- | --- |
| 1 | Brief y guion | Crear el proyecto y redactar la biblia |
| 2 | `BIBLIA.md` + anclas maestras generadas | Usar esas identidades; generar derivadas y fotogramas clave (0 créditos) |
| 3 | `STORYBOARD.md` + hoja de fotogramas clave + estimación de créditos | Generar en Flow la **muestra**: los 1–2 planos más difíciles |
| 4 | Muestra revisada con su QC | Generar el resto de planos dentro del presupuesto |
| 4b | Cada clip por separado, con su hoja de QC y su archivo | Unir los clips aprobados, generar efectos y voces con ElevenLabs y montar |
| 5 | Muestra del montaje y primer completo (motion-studio) | Exportación final, como en motion-studio |

Un cambio sustancial (otro personaje, otro estilo, más planos o más créditos de lo estimado) vuelve a la puerta correspondiente.

## Reglas que no se rompen

1. **Nada recurrente sale solo de texto.** Cada aparición de un personaje, producto o lugar recurrente lleva su ancla aprobada (fotograma clave, ingrediente o `@Personaje`).
2. **Todo desciende de una ancla maestra.** Las derivadas se editan desde la maestra, no desde copias; profundidad máxima maestra → derivada → fotograma clave. Tras dos relevos seguidos, re-ancla.
3. **Frames es el modo por defecto** para planos con identidades recurrentes: fotograma clave aprobado como inicio. Ingredients cuando la libertad aporta y el modelo admite las referencias. Más identidades de las que admite el modelo → fotograma clave compuesto.
4. **Una acción principal por plano**, con intervalos que suman la duración, un movimiento de cámara con motivo y un estado final que hereda el plano siguiente.
5. **La biblia se pega literal.** Fichas de identidad, vestuario y párrafo del set, copiadas; nunca «igual que antes».
6. **Sin texto generado.** Rótulos, logos, etiquetas y subtítulos van en el montaje. En prompts, colores por nombre: nada de hex ni Kelvin.
7. **Audio declarado en cada plano.** Si no se dirige, Flow inventa música y voces. La música continua va en postproducción.
8. **Nada se aprueba sin mirarlo.** `qc_clips.py` señala; la hoja de revisión y la reproducción deciden. Tres generaciones fallidas del mismo plano → replantear, no insistir.
9. **Gasto bajo control.** Ningún clip fuera del alcance aprobado. Anota los puntos de cada generación en la bitácora, lee el saldo de Flow antes y después de cada lote (`costos.py saldo`) y avisa si el gasto real supera la estimación. Cada puerta muestra los puntos y los tokens gastados (`costos.py informe`).
10. **Todo se registra.** Cada generación en `bitacora.jsonl`; cada defecto en `07-qc/REVISION.md`.

## Quién opera Flow

- **El usuario** (por defecto): le entregas `04-prompts/PROMPTS.md`, donde cada bloque trae la línea de ajustes de Flow, el prompt en inglés para copiar, el resumen «En español:», qué adjuntar y dónde guardar el resultado. Él genera, descarga y te dice qué archivo revisar.
- **El agente en el navegador** (si el usuario lo pide y tienes un navegador con su sesión de Flow, como Claude in Chrome): opera dentro del alcance aprobado en la puerta vigente. Las imágenes no gastan créditos pero respetan el alcance; los videos solo en el lote autorizado, confirmando el número de clips y los créditos que muestra Flow antes de generar. Pide permiso antes de descargar (nombre y origen) y antes de subir fotos de personas reales. Nunca compres créditos, cambies de plan ni aceptes condiciones por el usuario.

Al subir anclas a Flow, nómbralas igual que su handle sin `@` (`Valeria`, `BolsaOrigen`) para que `@` las encuentre; crea un personaje de Flow (Characters → New Character, 1–2 imágenes y una voz) por cada persona recurrente. Si al pegar un prompt Flow no convierte `@Nombre` en referencia, escríbelo con `@` y elígelo de la lista.

## Recorrido paso a paso

Desde la carpeta de esta skill (`python scripts/...`). Todos los scripts aceptan `--help`.

1. **Proyecto.** Tras la puerta 1:
   ```bash
   python scripts/nuevo_proyecto.py <carpeta-del-video> --nombre <nombre> --aspecto 9:16 --duracion 30
   ```
   Crea `01-biblia/ … 08-montaje/`, las plantillas y `bitacora.jsonl`. Con `--ejemplo` copia el proyecto de muestra «cafe-origen» completo. Registra la sesión y el primer hito para el seguimiento de costes (`costos.py sesion` y `hito`, ver `09-aprendizaje.md`) y anota un hito en cada puerta.
2. **Biblia.** Rellena `01-biblia/biblia.json` (`02-biblia-visual.md`) y genera el documento para aprobar:
   ```bash
   python scripts/flowprompt.py biblia <carpeta>
   ```
3. **Anclas maestras.** Declara en `02-anclas/anclas.json` las maestras (nivel 0) de cada entidad; genera sus prompts y produce las imágenes en Flow:
   ```bash
   python scripts/flowprompt.py validar <carpeta>
   python scripts/flowprompt.py prompts <carpeta>
   ```
   Revisa cada maestra con la lista de `03-imagenes-ancla.md`, marca `"estado": "aprobada"` y guárdala con su nombre. **Puerta 2.**
4. **Plan y fotogramas clave.** Escribe `03-storyboard/plan.json` (`04-planificacion-cinematografica.md`, audio según `06-produccion-audio.md`), añade las derivadas y los fotogramas clave `K##` a `anclas.json`, vuelve a `prompts` y genera esas imágenes. Compara cada `K##` con la maestra (puerta de identidad). Genera el storyboard y, si la pieza lo merece, el animatic (`a_motion_studio.py --animatic`):
   ```bash
   python scripts/flowprompt.py storyboard <carpeta>
   ```
   **Puerta 3**, con la estimación de créditos.
5. **Muestra en Flow.** Antes de gastar:
   ```bash
   python scripts/flowprompt.py validar <carpeta> --para-video
   ```
   Genera los 1–2 planos de muestra con sus prompts. Cada clip se guarda en `05-clips/raw/P##_v#.mp4` y se revisa:
   ```bash
   python scripts/qc_clips.py <carpeta> P01 05-clips/raw/P01_v1.mp4 [--caras]
   ```
   Mira `07-qc/P01/hoja.jpg`, reproduce el clip, aplica la escalera de corrección si hace falta y registra cada intento:
   ```bash
   python scripts/bitacora.py registrar <carpeta> --plano P01 --resultado aprobado --creditos 20 --nota "..."
   ```
   Copia el aprobado a `05-clips/aprobados/P01.mp4`. **Puerta 4.**
6. **Resto de planos.** Igual que la muestra. Cuando un plano continúa al anterior, su relevo es `07-qc/<plano anterior>/ultimo.png` (cópialo a `02-anclas/relevos/R##.png` y regístralo en `anclas.json`).
7. **Montaje.** Crea el proyecto de motion-studio y pasa los clips (`08-montaje-motion-studio.md`):
   ```bash
   python scripts/a_motion_studio.py <carpeta> <carpeta>/08-montaje --ajustar-duracion
   ```
   Desde ahí sigue motion-studio: rótulos, audio a −14 LUFS, `auditar.mjs`, `--determinismo`, `--prueba`, `--ritmo`, rúbricas (más las cuatro de consistencia de `07-control-calidad.md`), **puerta 5**, `--final` y `verificar.py`.
8. **Cierre y aprendizaje.** `python scripts/bitacora.py resumen <carpeta>`; promueve lo que se repitió con evidencia (`bitacora.py promover`) y anota los pendientes en `REVISION.md`.

## Herramientas

| Script | Para qué |
| --- | --- |
| `scripts/nuevo_proyecto.py` | Estructura de carpetas y plantillas de un video |
| `scripts/flowprompt.py` | `validar` (anclas aprobadas, límites de referencias y duraciones por modelo, suma de tiempos, texto que se cuela, referencias vagas, audio), `prompts`, `biblia`, `storyboard` |
| `scripts/qc_clips.py` | Formato, cortes internos, parpadeo, congelados, deriva de color, fidelidad al fotograma clave, caras (opcional), hoja de revisión y último fotograma |
| `scripts/a_motion_studio.py` | Clips aprobados o animatic → secuencias, audio y línea de tiempo para motion-studio |
| `scripts/bitacora.py` | Registro de generaciones, estadísticas por modo y modelo, biblioteca de patrones |
| `scripts/elevenlabs.py` | Efectos, voces y música con ElevenLabs desde `06-audio/sonido.json` (sin volver a pagar lo que existe) y mezcla final a −14 LUFS |
| `scripts/costos.py` | Puntos de Flow (declarados y medidos por saldo) y tokens de Claude por etapa → `costos.md` |
| `scripts/probar.py` | Prueba de regresión con material sintético (sin Flow ni créditos); ejecútala tras cambiar cualquier script |
| `assets/kit/flow_montaje.js` | Ayudante de motion-studio que dibuja el clip que toca en cada `t`, con fundidos |
| `assets/flow_capacidades.json` | Modelos, modos, duraciones y límites de Flow con su fecha de verificación |
| `assets/ejemplo/cafe-origen/` | Proyecto completo de muestra (1 personaje, 1 lugar, 1 producto, 3 planos) |

Requisitos: Python 3.10+ con numpy y Pillow, FFmpeg en el PATH; OpenCV 4 solo para `--caras` (vía `uv run --with "opencv-python-headless<5"`; OpenCV 5 retiró el detector que usa). El montaje necesita lo que pide motion-studio (su `scripts/preparar.py --comprobar`).

## Cómo hablas con el usuario

Como un director que explica a alguien que no tiene por qué saber de cine ni de IA: concreto, breve, con el porqué de cada decisión en una frase. Describe lo que el público verá («nos acercamos a sus manos justo cuando abre la bolsa»), no la técnica. Explica una palabra técnica la primera vez que la uses. Declara lo que no pudiste comprobar (un clip que no reprodujiste, un audio que no escuchaste) en lugar de darlo por bueno. Termina cada entrega diciendo cuál es el paso siguiente.
