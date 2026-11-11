# Reglas de producción

Cinco reglas fijadas por el usuario el 11 de noviembre de 2026, tras la primera iteración del video del puffle. Mandan sobre cualquier otra guía de la skill. Cada una dice qué hacer, con qué herramienta y qué evidencia deja.

## 1 · Análisis de referencia antes de generar nada

La primera iteración falló aquí. Se tomaron de la referencia el tema y el color, pero no su lenguaje: era **una toma continua en primera persona** y se planificaron planos cortados.

1. **Mira el video entero y mídelo.** Duración exacta, resolución y relación de aspecto.
2. **Recórrelo segundo a segundo.** En el navegador, con el video en pausa, salta a cada instante (`video.currentTime = t`, esperar `seeked`) y captura el fotograma. Con una copia local, usa `scripts/referencia.py` de motion-studio.
3. **Escribe `REFERENCIA.md` en el proyecto** con una tabla por tramo: tiempo, encuadre y punto de vista, movimiento de cámara, acción, **cuerpo del espectador** (manos, piernas), luz, sonido y transición.
4. **Extrae el lenguaje, no el tema:**
   - número de cortes (cero es una decisión de estilo);
   - si la cámara es un personaje (primera persona) y qué hace su cuerpo;
   - el arco en el tiempo (descubrir → acercarse → actuar → reacción → pausa o salida);
   - el ritmo (cuánto dura cada momento);
   - cómo suenan la música y los efectos;
   - la duración total.
5. **Declara lo que no comprobaste.** Si no pudiste escuchar el audio, dilo. La música y los efectos se describen al escucharlos, no se suponen.
6. **Contrasta el storyboard con `REFERENCIA.md` antes de la puerta 1.** Cada rasgo de la tabla «Lenguaje que se traslada» debe estar en el plan, o justificado si se cambia.

## 2 · Continuidad visual: cada clip continúa al anterior

Una escena se rueda como **una toma continua dividida en clips encadenados**. El espectador no debe notar dónde termina un clip y empieza el siguiente.

| Enlace | Cómo se genera | Cuándo |
| --- | --- | --- |
| **Relevo** | El clip N+1 en modo Frames, con el **último fotograma aprobado del clip N** como inicio (`R##`, de `qc_clips.py` → `ultimo.png` o *Save frame* en Flow) | Siempre que la acción continúa |
| **Relevo con re-anclaje** | Frames con inicio `R##` y **fin = fotograma clave aprobado** (`K##`) | Cuando el clip termina en una composición crítica (la cara o el personaje cerca): el propio clip vuelve a la identidad aprobada |
| **Extend** (Omni 1.2, de pago) | Alarga el clip anterior con hasta 3 imágenes de referencia | Cuando la cámara no para de moverse y un fotograma quieto cortaría la inercia |

Reglas:

- **El cuerpo del espectador es un personaje** (`@Viajero` en la biblia): mano, manga, pantalón y calzado se describen siempre igual.
- **Cada clip empieza moviéndose.** En los prompts de continuación: «continuing the same motion from the start frame without pausing».
- **En el montaje no se repite el fotograma de unión**: el `uso` del clip siguiente empieza un fotograma después (0,042 s a 24 fps).
- **Re-ancla cada dos relevos** con un fotograma clave aprobado (regla general de la skill).
- **Fluidez dentro de cada clip.** Sin congelados, sin saltos de velocidad ni acciones a medias. `qc_clips.py` marca los congelados y los cortes; la reproducción decide.

## 3 · Planificación temporal: escenas de ~15 segundos

- **La unidad es la escena de unos 15 s**, ajustable a la historia. Un reel tipo zuni es una escena; una pieza más larga son varias escenas enlazadas.
- **Cada escena se divide en clips de 4–6 s** que suman su duración. Omni 1.2 genera de 3 a 15 s; con clips cortos se controla mejor y se reintenta más barato.
- **Los tiempos se planifican por segundo** (intervalos `[0-2s]`) y la suma de los tramos `uso` debe dar la duración de la escena (`flowprompt.py validar` lo comprueba).
- **Coste:** con Omni 1.2 a 720p son 3 puntos por segundo y variante (×2 = 6 puntos/s). Una escena de 15 s en tres clips ×2 cuesta unos 90 puntos sin repeticiones.

## 4 · Producción de audio: ElevenLabs y montaje

| Capa | Herramienta | Cuándo |
| --- | --- | --- |
| **Voces** (narración o diálogo) | ElevenLabs, texto a voz | Antes de fijar los tiempos si hay narración: la voz manda el ritmo |
| **Efectos** (pasos, puerta, objetos) | ElevenLabs, efectos de sonido | Tras aprobar los clips, en los instantes reales de cada acción |
| **Música de fondo** | Pista del usuario o ElevenLabs Music | En el montaje y el render final |
| **Mezcla** | motion-studio | −14 LUFS, música con ducking bajo la voz y efectos sincronizados |

- **Efectos: primero los de Flow.** Los clips se piden con «Music: none» y los efectos de cada acción descritos en el prompt. Si al auditarlos el usuario aprueba su sonido, **se conservan en la mezcla** (`sonido.json` → `clips_audio`). ElevenLabs solo cubre lo que falte o suene mal (y las voces). Decidido por el usuario el 11 nov 2026: «Google Flow ya le agregó los sonidos».
- **Música de fondo:** la pista elegida entra **desde su segundo 0 al inicio del video** (no desde un fragmento), con fundido de salida al final y ducking bajo las voces.
- **Voces en primera persona: pocas y con emoción.** Por defecto, **una sola frase corta** en el momento de mayor carga emocional, con el tono cuidado (susurro, quebrado, cálido…). Más frases solo si la emoción lo pide, nunca una por clip. Deben acompañar la acción, no explicarla. Decidido por el usuario el 11 nov 2026, tras una v2 con cinco frases: «estas voces me desconcentran, deja solo 1 frase corta (el tono importa)».
- **Flujo obligatorio de voces:** 1) proponer la frase, el momento y el tono y **preguntar**; 2) generar **muestras solo de audio** (2–3 tomas o tonos) y entregarlas para auditar; 3) solo con su visto bueno, mezclar con el video y renderizar. Vale también para ecos o risas que suenen a voz.
- Herramienta: `scripts/elevenlabs.py` (efectos, voces y música desde `06-audio/sonido.json`). Lee la clave de la variable `ELEVENLABS_API_KEY` o de un archivo de credenciales, nunca la imprime, no vuelve a pagar lo que ya existe y anota los caracteres consumidos en `costos.json`.
- **La música de la referencia no se copia ni se recrea.** Para Instagram, el usuario puede elegir ese mismo audio de la biblioteca de la app al publicar.

## 5 · Auditoría obligatoria de cada clip

1. Cada clip pasa por `qc_clips.py` y por revisión visual de su hoja y su reproducción.
2. Al usuario se le presenta **cada clip por separado**: archivo, hoja, defectos encontrados y la variante recomendada.
3. **No se une nada sin su luz verde explícita, clip por clip** (puerta 4b). Una aprobación parcial («P01 y P03 sí») solo cubre esos clips.
4. **Un clip con defectos no se monta**: se corrige con la escalera de `07-control-calidad.md` y se vuelve a presentar.
5. Si el usuario rechaza un clip que ya sirvió de relevo para el siguiente, el siguiente también se regenera: su inicio dejó de existir.
