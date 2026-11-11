# Etapa 5 · Producción de audio

El audio se decide en la preproducción, no al final. Flow (Omni y Veo) genera sonido en cada clip aunque no lo pidas; si no lo diriges, inventa música, voces o risas. Por eso cada plano declara su audio, y el proyecto declara una política.

## Política de audio del proyecto (`biblia.json` → `audio.politica`)

| Política | Cuándo | Cómo se pide en Flow | Qué se hace en el montaje |
| --- | --- | --- | --- |
| **post** (recomendada para narrado, anuncio o pieza con música) | Hay narración en off, música continua o mezcla exigente | Cada clip: «Audio: Ambient: [ambiente]. SFX: [efectos]. Music: none. Dialogue: none.» Se conserva el ambiente nativo como capa opcional | Voz, música y efectos se montan y mezclan en motion-studio (`audio/musica.py --voz`), a −14 LUFS |
| **nativo** | Escenas con diálogo en cámara y sincronía labial | Diálogo y sonido completos en el prompt; voz del personaje con referencia de voz (Omni, Ingredients) | Se respetan las pistas de cada clip; se nivelan, se cruzan en los cortes y se añade música por debajo |
| **mixto** | Diálogo en algunos planos y narración en otros | Por plano | Diálogo nativo + narración y música en post |

La música casi nunca debe salir de Flow dentro de los clips: cada clip traería otra pieza y los cortes la romperían. Música continua = postproducción (Flow Music, `audio/musica.py` de motion-studio o una pista del usuario).

## Las cuatro líneas de audio de cada plano

```
Audio: Dialogue: [quién, qué dice y cómo]. SFX: [el sonido ligado a una acción visible]. Ambient: [el fondo del lugar]. Music: [none, o descripción]. Not heard: [lo que no debe sonar].
```

- **Densidad:** en un clip corto, una línea de diálogo, un efecto principal y un ambiente. Más capas suenan a ruido.
- **Silencio intencional:** «Audio: intentional silence, only faint room tone.»
- **Sin subtítulos:** el diálogo va tras dos puntos y sin comillas, y se añade «(no subtitles)». Las comillas invitan al modelo a escribir el texto en pantalla.
- **Atribución:** en planos con dos personas, «The woman in the apron says: …», no «she says».
- **Pronunciación:** nombres raros, escritos como suenan.
- **Longitud:** 2–3 frases cortas por cada 8 s. Más acelera la voz; menos deja silencios o balbuceo.

## Narración (voz en off)

Opciones, por orden de preferencia y según lo que el usuario tenga:

1. **Grabación del usuario.** Mejor naturalidad. Se edita con el modo edición de motion-studio si hace falta.
2. **Voz clonada o voz de servicio** (Voice Studio de la skill narrated-explainer, ElevenLabs con marcas de tiempo por palabra, como en el pipeline del canal). Una sola toma para todo el texto da mejor prosodia que frases sueltas.
3. **Voz de Flow** (Omni, Ingredients): solo para diálogo en cámara; no está pensada para una locución larga.

Si ninguna está disponible, dilo y propone texto en pantalla. No sustituyas una opción por otra en silencio.

**La voz manda el tiempo.** Con narración, primero se graba o genera la voz, se miden los tiempos reales de cada frase y después se fija `uso` de cada plano para que los cortes caigan con las frases. La duración generada de cada clip se elige para cubrir su frase con margen.

## Efectos y ambientes

- El ambiente nativo de Flow suele ser bueno y coherente con la imagen: consérvalo como capa baja (−24 a −18 dB bajo la voz) cuando la política es `post`.
- Los efectos clave (un golpe, un cierre de puerta, el clic del producto) se colocan en la mezcla en el fotograma exacto del impacto, no se confía en el del clip.
- Un mismo lugar suena igual en todos sus planos: elige un ambiente y repítelo, aunque cada clip traiga el suyo.

## Sincronización

- Cortes y acentos visuales en los pulsos de la música medida (`beats.json` de motion-studio), no en los supuestos.
- Las acciones que suenan (un golpe, un paso) coinciden en ±1 fotograma con su efecto. Se comprueba en reproducción, no en una hoja de contacto.
- Diálogo nativo: revisa la sincronía labial plano a plano; si falla, el clip se corrige (Editar) o se tapa con un plano de reacción o de detalle.

## Mezcla y entrega

La mezcla final la hace motion-studio: voz al frente, música con ducking de unos 8 dB bajo la voz, ambientes y efectos, −14 LUFS integrados y pico por debajo de −1 dBTP. `a_motion_studio.py` extrae el audio de cada clip aprobado a `audio/flow/P##.wav` para usarlo como capa.

## Comprobaciones de audio en el QC

- ¿Algún clip trae música, voces o risas que no se pidieron? → Se silencia ese clip o se regenera con «Music: none. Not heard: …».
- ¿El diálogo nativo dice exactamente el texto del plan? → Transcríbelo y compáralo.
- ¿Hay saltos de ambiente en los cortes dentro del mismo lugar? → Se unifica el ambiente en la mezcla.
- ¿La voz en off está a −14 LUFS en la mezcla final y sin picos por encima de −1 dBTP? → `verificar.py` de motion-studio.

## Voces de interacción en primera persona (la-piscina-azul, nov 2026)

- **Quién habla:** el espectador, en susurro (`[whispers]`, eleven_v4). **Una sola frase corta por defecto**, en el momento de más emoción (regla 4 de `10-reglas-de-produccion.md`). La v2 de la-piscina-azul llevaba cinco frases y el usuario la rechazó porque distraían. Los personajes de dibujo con la boca cerrada en los clips **no hablan**: sonarían doblados. Responden con gestos.
- **Antes de mezclar:** muestras solo de audio de la frase, con 2–3 tonos, para que el usuario las audite.
- **Cuándo:** se coloca la frase en el instante del gesto que acompaña y se comprueba que no pise un efecto clave de Flow, como el chapoteo o la gota. Se deja silencio antes del cierre.
- **Recuerdos:** voces lejanas como eco de memoria, con `"filtro": "highpass=f=280,lowpass=f=3200,aecho=0.8:0.55:190|340:0.45|0.3"` en la capa de `sonido.json`, más risas generadas como efecto con el mismo filtro. Sin voces infantiles en la cuenta, una voz joven y luminosa (Jessica) con eco funciona.
- **Comprobación:** se transcribe cada toma y la mezcla completa con faster-whisper. Los susurros muy suaves se escapan a la detección de voz (VAD), así que se comprueban también sin VAD. En cambio, sin VAD el transcriptor alucina frases sobre las risas y el silencio («Thank you», «I love you»): ante la duda, manda la detección de voz.
- **Mezcla:** `mezclar` compensa en una segunda pasada la sonoridad que le quita el limitador y limita con sobremuestreo ×4 para que el pico real quede ≤ −1 dBTP.
- **Naturalidad:** el susurro con etiquetas (`[whispers] [sad]`) y las respiraciones generadas sonaron artificiales. Lo que el usuario aprobó fue una voz baja con `previous_text` (contexto de la escena que no se lee) en `eleven_multilingual_v2`, con estabilidad 0,45 y estilo 0,15. Para la máxima naturalidad, se puede ofrecer que el usuario grabe la frase y pasarla por el cambiador de voz.
