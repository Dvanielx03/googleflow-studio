# Etapa 1 · Skills investigadas y qué se integró

Investigación del 11 de noviembre de 2026. Se buscó en las skills instaladas, en el registro abierto (`npx skills find`, skills.sh) y en GitHub. Criterio para integrar: que aporte una técnica concreta para Flow, consistencia, dirección, audio o control de calidad que no esté ya en motion-studio, y que se pueda comprobar. No se instaló ninguna skill externa: se extrajeron sus técnicas, se reescribieron y se probaron dentro de esta skill. Así no hay dependencias de terceros ni instrucciones ajenas ejecutándose.

## Comparación

| Skill | Fuente y señales | Qué aporta | Decisión |
| --- | --- | --- | --- |
| **motion-studio** | Instalada (`~/.claude/skills/motion-studio`) | Fases preproducción/producción/postproducción, ficha por plano, curva de energía, avisos de aprobación, render determinista, `verificar.py`, `ritmo.py`, rúbricas, mezcla a −14 LUFS | **Base del flujo.** Esta skill la usa para el montaje y la exportación. Sus reglas de aprobación se conservan. |
| **director-de-collage** | Instalada | Entrega de prompts en inglés con «En español:», línea de ajustes de Flow, croma `#00B140` para recortes, prompt de «Locked-off static camera» para gestos pequeños | **Integrada** en el formato de entrega y en el modo «capas» (`05-prompts-flow.md`). |
| **google-flow-scripting-skill** (agbelemi) | GitHub, 15 estrellas, v1.6.0, docs revisadas jul 2026 | Identificadores `@PascalCase`, párrafo fijo del set, hoja de storyboard por segmento, libro de estado de continuidad, audio en cuatro líneas, comprobación de texto que se cuela, aritmética de segmentos | **Técnicas integradas** (anclas, plan, prompts y QC). Poca adopción: no se instala. |
| **prompt-videos** (replicate) | skills.sh, 2,7 K instalaciones, 148 estrellas, auditorías superadas | Prompt en 7 capas, cuatro capas de audio, cómo evitar subtítulos, ficha de personaje literal, 10 errores comunes, imagen a video = describir solo lo que cambia | **Integrada** en `05-prompts-flow.md` y `06-produccion-audio.md`. |
| **cinematography** (fal-ai-community) | skills.sh, 1,3 K instalaciones, 266 estrellas | Orden de prompt sujeto → contexto → lente → movimiento → atmósfera → color → salida; «arregla cámara, puesta en escena y luz antes de añadir adjetivos»; lista de comprobación física | **Integrada** en el orden de los prompts y en el QC. Su enrutado de modelos (fal) no aplica a Flow. |
| **short-drama-storyboard** (zenstory-ai) | skills.sh, 2,7 K instalaciones, 4,1 K estrellas | Una acción por plano, fotograma inicial congelado y final opcional, prompts de recursos en paralelo al storyboard | **Concepto integrado** (fotograma clave por plano, `04-planificacion-cinematografica.md`). Formato en chino: no se usa. |
| **ai-video-generation** («superpowers», muchos forks) | skills.sh, cientos de miles de instalaciones repartidas en copias | Depende de la CLI de inference.sh, no de Flow | **Descartada.** Cifras infladas por copias y no sirve para Flow. |
| **character-consistency** (varias) | skills.sh, menos de 50 instalaciones | Recetas ligadas a un proveedor (Runware, Magic Hour) | **Descartadas.** Lo útil ya está en el sistema de anclas. |
| **directorskills** (geegl) | 13–18 instalaciones | Reglas sueltas (180°, tres puntos de luz) | **Descartada** como skill; la regla de 180° y la dirección de luz se recogen en la biblia y el QC. |
| **hyperframes / Remotion / general-video** | Instaladas | Montaje por HTML/React | **No se usan**: regla fija del usuario. El montaje va por motion-studio. |
| **narrated-explainer** | Instalada | Voz clonada del usuario (Voice Studio) | **Opcional** para la narración; ver `06-produccion-audio.md`. |
| **yt-script / youtube-virality-gate** | Instaladas | Ganchos y verificación antes de publicar en YouTube | **Opcionales**: guion de YouTube (etapa 0) y puerta final si el destino es YouTube. |
| **Kling (MCP)** | Conectado | Otro generador de video | **Fuera de alcance** salvo que el usuario lo pida: esta skill es para Flow. |

## Documentación oficial consultada

- Flow · modelos y funciones: <https://support.google.com/flow/answer/16352836>
- Flow · crear videos (Frames, Ingredients, voces): <https://support.google.com/flow/answer/16353334>
- Flow · editar y Scenebuilder (Extend, Save frame): <https://support.google.com/flow/answer/16935718>
- Flow · personajes, recursos y colecciones: <https://support.google.com/flow/answer/16935308>
- Flow · imágenes y límites diarios: <https://support.google.com/flow/answer/16729550>
- Gemini Omni Flash (prompts, referencias, edición, extensión): <https://aistudio.google.com/docs/omni>
- Veo · guía de prompts: <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide>

Las cifras de modelos están en `assets/flow_capacidades.json` con su fecha. Si Flow cambia, se actualiza ese archivo, no el texto de las guías.

## Cómo repetir esta investigación

Hazlo cada 2–3 meses o cuando Flow anuncie un modelo:

1. `npx skills find storyboard`, `cinematography`, `video prompt`, `veo`, `character consistency`.
2. Prefiere más de 1 000 instalaciones, autor reconocible y auditorías superadas. Lee el `SKILL.md` antes de valorar nada.
3. Integra técnicas concretas que puedas probar en un plano, nunca dependencias. Anota aquí la fecha, la fuente y la decisión.
4. Prueba la técnica nueva en un proyecto y regístrala en la bitácora (`09-aprendizaje.md`). Solo pasa a `patrones-probados.md` si funciona.
