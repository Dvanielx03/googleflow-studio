# Postproducción · Montaje en motion-studio

Los clips de Flow se montan, se rotulan, se mezclan y se exportan con motion-studio, en su **modo animación**. No se usa Scenebuilder de Flow para la entrega (sirve como vista rápida), ni HyperFrames ni Remotion. Así la pieza final pasa por las mismas comprobaciones que cualquier video del usuario: determinismo, ritmo, `verificar.py` y −14 LUFS.

## Recorrido

1. **Proyecto de motion-studio.** Con el brief aprobado y la autorización de la puerta correspondiente, desde la carpeta de motion-studio:
   ```bash
   python scripts/nuevo.py <proyecto-flow>/08-montaje --nombre <nombre> --duracion <s> --fps 30 [--vertical]
   ```
   30 fps es la entrega natural para clips de Flow (generados a 24 fps); 60 fps duplica fotogramas sin ganar fluidez.

2. **Clips aprobados.** Cada plano aprobado se copia como `05-clips/aprobados/P##.mp4`. Si la entrega es 1080p o más, sube primero el clip en Flow (upscale de pago a 1080p o 4K) y descarga esa versión: escalar 720p en el montaje se nota.

3. **Pasar los clips al montaje.**
   ```bash
   python scripts/a_motion_studio.py <proyecto-flow> <proyecto-flow>/08-montaje
   ```
   Para cada plano del `plan.json`, en orden:
   - extrae el tramo `uso` del clip como secuencia PNG en `recursos/flow/P##/` (a sus fps nativos, ajustada al tamaño del video);
   - extrae su audio a `audio/flow/P##.wav` si lo tiene;
   - escribe `recursos/flow/clips.json` con la línea de tiempo (inicio, duración, fundidos) y copia `kit/flow_montaje.js`.

   Con `--animatic` usa los fotogramas clave `K##` quietos en lugar de los clips: el animatic de la etapa 4.

4. **Componer en `index.html`.** El ayudante resuelve qué fotograma de qué clip toca en cada `t` y dibuja los fundidos:
   ```html
   <script src="lib.js"></script>
   <script src="kit/secuencia.js"></script>
   <script src="kit/flow_montaje.js"></script>
   <script>
   (async () => {
     const cfg = await (await fetch('motion.config.json')).json();
     const W = cfg.video.ancho, H = cfg.video.alto;
     const cv = document.getElementById('c'); cv.width = W; cv.height = H;
     const ctx = cv.getContext('2d');
     const montaje = await crearMontajeFlow('recursos/flow/clips.json');
     const { texto } = crearTexto(ctx);
     window.seek = async t => {
       ctx.reset();
       await montaje.dibujar(ctx, t, W, H);
       // Rótulos, logo y textos del producto: aquí, con texto(), nunca generados por Flow.
     };
     await window.seek(0); window.ready = true;
   })().catch(e => { window.loadError = String(e && e.stack || e); });
   </script>
   ```
   El resto (rótulos, subtítulos, cámara sobre el clip, grano común, transiciones con motivo) se hace con el kit de motion-studio y sus reglas.

5. **Audio.** Con política `post`: voz, música y efectos con `audio/musica.py` (`--voz`, `--pista`) y los ambientes de `audio/flow/` como capa baja. Con política `nativo`: une las pistas `audio/flow/P##.wav` en la línea de tiempo de `clips.json` (cruces de 40–80 ms en los cortes) y añade la música debajo. Resultado: `audio/final.wav` a −14 LUFS.

6. **Revisión y exportación.** Las de motion-studio, sin atajos: `auditar.mjs`, `--determinismo`, `--prueba`, `--ritmo`, hoja de contacto, rúbricas (más las cuatro de `07-control-calidad.md`), `--final` con autorización y `verificar.py`.

## Unificar el aspecto de los clips

Aunque compartan anclas, los clips pueden variar un poco de color y contraste. En el montaje:
- Aplica el mismo grado a todos (curva suave y tono de la biblia) con un filtro de canvas o una capa de color común.
- Un grano común encima de todo disimula diferencias de textura entre generaciones; úsalo solo si la biblia lo pide.
- No corrijas en el montaje un cambio de identidad: eso se arregla en el plano (QC).

## Notas

- Los ambientes de Flow cambian de un clip a otro aunque el lugar sea el mismo: en la mezcla, un ambiente continuo por escena.
- Un clip con un texto o un defecto en sus extremos se arregla ajustando `uso` en `plan.json` y repitiendo `a_motion_studio.py`; no se edita la secuencia a mano.
- `a_motion_studio.py` solo reescribe los planos cuyo clip o `uso` cambiaron.
