# Ingeniería de prompts para Google Flow

`python scripts/flowprompt.py prompts` arma todos los prompts desde la biblia, las anclas y el plan, y los deja en `04-prompts/PROMPTS.md` (para copiar) y `04-prompts/prompts.json` (para la bitácora). Esta guía explica qué hace ese ensamblado y cómo retocar un prompt a mano sin romper la consistencia.

## Reglas comunes

1. **En inglés.** Omni Flash solo garantiza inglés. Debajo de cada prompt va una línea «En español:» para el usuario.
2. **Cada prompt se sostiene solo.** Nada de «como en el plano anterior». Lo que debe verse se nombra.
3. **Lo importante, primero.** Los modelos atienden más al principio. Orden: política de texto y de plano → referencias y su papel → sujeto → acción → encuadre, lente y cámara → lugar y luz → estilo → audio → exclusiones.
4. **Texto que no se cuela.** Sin códigos hex, sin temperaturas en Kelvin, sin etiquetas entre corchetes (salvo los intervalos `[0-3s]`), sin rayas largas (—). Los colores van con nombre.
5. **Sujetos con nombre o descripción**, nunca con pronombres ambiguos cuando hay más de uno: `@Valeria`, «the old man in the grey cardigan».
6. **Adjetivos concretos.** «Shot on 35mm film, soft grain» y no «cinematic masterpiece, stunning, 8K».
7. **Las fichas de la biblia se pegan literal.** Identidad, vestuario, disposición del set: copiar, no parafrasear.

## Línea de ajustes

Encima de cada prompt, la configuración exacta de Flow:

```
Google Flow · Video · Frames · Omni Flash 1.2 · 9:16 · 8 s · x2 · 720p · inicio: K01
Google Flow · Imagen · Nano Banana Pro · 9:16 · x4 · refs: Valeria.A0, TostaduriaSantaRita.A0
```

## Prompts de video según el modo

### Frames (inicio, o inicio y fin)

La imagen ya muestra el sujeto, el lugar, la luz y el estilo. **Describe solo lo que cambia**: acción, cámara, audio y el estado final. Repetir la descripción completa empuja al modelo a «redibujar» la escena y se pierde la fidelidad al fotograma.

```
No on-screen text, no subtitles. Single continuous shot, no scene cuts.
The video starts exactly on the provided start frame. Keep the character's face, hair and clothing, the product and the room exactly as they appear in it.
[0-3s] Valeria lifts the coffee bag from the counter and turns it toward the window light.
[3-8s] She breathes in the aroma, closes her eyes and smiles slightly.
Camera: slow dolly in from medium shot to medium close-up.
Ends with Valeria holding the bag near her face, eyes closed, smiling.
Audio: Ambient: soft hum of a coffee roaster and distant street noise. SFX: paper bag crinkle when she lifts it. Music: none. Dialogue: none.
Do not add other people. Do not change her clothing.
```

Con inicio y fin, añade: «The video ends exactly on the provided end frame.» y describe la transición entre ambos.

### Ingredients

Aquí el modelo construye la escena desde las referencias. Prompt completo: papel de cada referencia, ficha de identidad literal, párrafo del set, encuadre, acción, luz, estilo y audio. Omni Flash 1.2 admite hasta 6 imágenes (3 por personaje, 2 personajes); Veo 3.1 Lite/Fast, 3 ingredientes y solo 8 s.

```
No on-screen text, no subtitles. Single continuous shot, no scene cuts.
@Valeria is the woman from the character reference: [ficha de identidad literal], wearing [vestuario V1 literal]. The location is the coffee roastery from the location reference: [párrafo fijo del set].
[Acción con intervalos]
[Encuadre], [lente]. Camera: [movimiento].
Lighting: [L#]. Style: [prefijo de estilo].
Audio: [cuatro líneas].
Do not ...
```

### Extend (Omni Flash 1.2, de pago)

```
Continue the scene in the same single continuous shot: [lo que sigue pasando]. @Valeria [estado visible actual]. Camera: [continúa o cambia con motivo]. Audio: [...]
```

Omni usa los últimos 10 s como contexto. Si alguien apareció antes de esos 10 s, vuelve a nombrarlo y adjunta su referencia (hasta 3 imágenes). Solo alarga por el final; máximo 30 s en total.

### Editar (Omni Flash 1.2)

Prompts cortos. Una corrección por turno y la frase de cierre siempre:

```
Make her left hand have five natural fingers holding the bag. Keep everything else the same.
```

Hasta 3 turnos conservando el contexto. Las ediciones cuestan lo mismo por segundo que una generación. Si al tercer turno no está, regenera el plano.

### Texto a video

Solo para recursos sin identidad recurrente. Prompt completo en el orden de las reglas comunes.

## Particularidades de los modelos

| | Omni Flash 1.2 | Veo 3.1 (Lite/Fast/Quality) |
| --- | --- | --- |
| Planos por clip | **Varios por defecto**: pide «Single continuous shot, no scene cuts» si el plano es único | Uno |
| Intervalos `[0-3s]` | Sí | Funcionan como guía; menos precisos |
| Longitud del prompt | Concreto y enfocado: 60–150 palabras en Frames, hasta ~250 en Ingredients | Admite más detalle; menos de ~250 palabras |
| Exclusiones | No hay campo negativo: frases cortas «Do not add …» | Flow no tiene campo negativo: lista corta «Avoid: …» al final (pendiente de validar en la bitácora) |
| Audio | Lo genera siempre: descríbelo o niégalo («No dialogue», «No music») | Nativo; descríbelo igual |
| Voz de personaje | Referencia de voz en Ingredients (`@Voice: Nombre` o la del personaje) | No |
| Retiro | — | Fast y Quality se retiran el 5 dic 2026: usa Omni 1.2 o Veo 3.1 Lite |

## Prompts de imagen (Nano Banana)

Lenguaje natural, describiendo la foto que quieres como lo haría un director de fotografía. Para anclas y fotogramas clave, las plantillas están en `03-imagenes-ancla.md`. Además:

- Al editar una imagen: «Using the attached image…», una sola variación, y lo que se conserva dicho explícitamente.
- Varias referencias: di el papel de cada una («the woman from the first image, the room from the second image»). En Flow, los personajes se nombran con `@` y las imágenes se añaden con *Add to Prompt*.
- Relación de aspecto de los fotogramas clave = la del video.
- Termina con «No text, no watermark.» salvo que el plano necesite texto (y entonces mejor en el montaje).
- Nano Banana Pro para maestras difíciles (manos, producto, varias referencias); 2.1 para derivadas y variantes. Ninguno gasta créditos de Flow, pero tienen límite diario.

## Modo capas (collage o composición en el montaje)

Si un elemento se va a recortar y animar en el montaje (estilo de director-de-collage), se genera sobre croma: «isolated on a plain flat chroma key green background (pure green, evenly lit, no shadows on the background), clean sharp edges for cutout». Si lleva algo verde, fondo azul. Para que una persona recortada haga solo un gesto pequeño en Flow:

```
Locked-off static camera, no camera movement, no zoom, same framing and same lighting for the whole shot. The woman stays in exactly the same position. She breathes slowly, blinks and lifts her eyes toward the left. Only small, natural, subtle movements. The plain flat green background stays perfectly flat and unchanged. No particles, no text, no music, no voice.
```

## Lista de comprobación antes de generar

- [ ] Modelo, modo, duración y relación de aspecto coinciden con el plan y con `flow_capacidades.json`.
- [ ] Las referencias adjuntas son las aprobadas y caben en el límite del modelo.
- [ ] El prompt nombra el papel de cada referencia.
- [ ] Una acción principal; intervalos que suman la duración.
- [ ] Un movimiento de cámara con motivo.
- [ ] Audio en sus líneas o «Music: none / Dialogue: none».
- [ ] Política de texto y de plano único arriba.
- [ ] Sin hex, Kelvin, rayas largas ni referencias vagas.

`flowprompt.py validar` comprueba automáticamente lo que se puede comprobar; el resto es lectura.
