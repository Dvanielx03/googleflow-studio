# Etapa 4 · Planificación cinematográfica

Cada plano se decide completo antes de generarlo: encuadre, cámara, acción, duración, ritmo, sonido y cómo enlaza con el siguiente. Un clip de Flow cuesta créditos y tiempo; un plano mal pensado no se arregla regenerándolo cinco veces.

Fuente de verdad: `03-storyboard/plan.json`. `python scripts/flowprompt.py storyboard` genera `03-storyboard/STORYBOARD.md` para revisar con el usuario. La ficha amplía la de motion-studio (`references/preproduccion.md` de esa skill): conserva sus seis campos y añade los de Flow.

## Ficha del plano

| Campo (`plan.json`) | Decisión |
| --- | --- |
| `id`, `escena`, `papel` | `P01`, `E01`; papel en la curva: gancho, desarrollo, re-gancho, pausa, clímax o cierre. |
| `intencion` | Qué debe entender o sentir el público y por qué el plano es necesario. |
| `encuadre` | Tamaño y ángulo: «medium close-up, eye-level». |
| `lente` | Focal y profundidad: «50mm lens, shallow depth of field». |
| `camara` | Un movimiento con motivo, o cámara fija con motivo: «slow dolly in toward her hands». |
| `iluminacion` | `L#` de la biblia y la variación si la hay. |
| `accion` | Estado inicial → acción → consecuencia, con intervalos: `[{"t": "0-3s", "en": "..."}]`. **Una acción principal por plano.** |
| `estado_final` | Cómo acaba el plano (posición, mirada, objeto). Es la entrada del libro de continuidad. |
| `audio` | Diálogo, efectos, ambiente, música y lo que no debe oírse (ver `06-produccion-audio.md`). |
| `enlace` | Plano destino, tipo (`corte`, `continuacion`, `match`, `fundido`) y qué los une. |
| `modo`, `modelo` | Modo de Flow (`frames`, `frames_ultimo`, `ingredientes`, `extender`, `editar`, `texto`) y modelo (`omni-1.2`, `veo-3.1-lite`…). Ver la tabla de modos en `03-imagenes-ancla.md`. |
| `duracion` | Segundos que se generan: un valor admitido por el modelo. |
| `uso` | `[entrada, salida]` en segundos dentro del clip: lo que se monta. |
| `anclas`, `fotograma_inicial`, `fotograma_final` | Ids de `anclas.json`. |
| `quietos` | Criaturas que no deben moverse en este plano (`["@PuffleRosa"]`): su regla de movimiento se cambia por «se queda completamente quieta». Si no, la regla de movimiento invita a moverse, y al moverse aparecen patas. |
| `toma_unica` | `true` si el plano no debe tener cortes internos (Omni corta por defecto). |
| `salidas` | Variantes por generación (x1–x4). Más variantes, más créditos. |

## Aritmética de duración

- Una generación es un plano. Su duración debe ser un valor admitido: Veo 3.1 → 4, 6 u 8 s (Ingredients solo 8 s); Omni Flash 1.2 → 3–10 s (hasta 15 s con plan de pago; Frames con inicio y fin, máximo 10 s). `flowprompt.py validar` lo comprueba con `assets/flow_capacidades.json`.
- **Genera más de lo que montas.** El final de un clip es lo que más se desvía; el principio de un clip de Frames es el fotograma clave quieto. Planifica `uso` dentro del clip (por ejemplo, 0,4–6,5 s de un clip de 8 s) y deja aire para cortar en la acción.
- La duración en pantalla la decide el ritmo, no el modelo. En piezas dinámicas los planos montados duran 1,5–4 s aunque se generen de 6–8 s.
- Suma: `duración del video = suma de (uso.salida − uso.entrada)` menos los solapes de las transiciones. `validar` avisa si no cuadra con el brief.
- Con voz: unas 2,5 palabras por segundo en español. Un diálogo nativo cabe en 2–3 frases cortas por cada 8 s; más texto acelera la voz, menos deja silencios o balbuceos.

## Una acción por plano

Un clip de 8 s sostiene una acción con su preparación y su consecuencia. Dos acciones independientes en un clip suelen salir mezcladas o a medias. Si el guion pide más, son dos planos. Escribe la acción como algo que se ve: no «recuerda a su abuelo», sino «toma la foto del mostrador, la mira y sonríe de lado».

En Omni Flash, los intervalos fijan el ritmo dentro del clip:

```
[0-3s] She lifts the bag from the counter and turns it toward the window light.
[3-8s] She breathes in the aroma, closes her eyes and smiles slightly.
```

## Cámara: vocabulario que los modelos entienden

| Término | Qué hace | Úsalo para |
| --- | --- | --- |
| `static shot`, `locked-off camera` | Cámara fija | Leer un gesto, diálogo, producto |
| `slow dolly in` / `dolly out` | Se acerca / aleja físicamente | Revelar emoción / revelar contexto |
| `pan left/right`, `tilt up/down` | Gira sobre su eje | Seguir una mirada, descubrir algo al lado |
| `tracking shot`, `truck left/right` | Acompaña lateralmente | Personaje que camina |
| `crane shot`, `pedestal up` | Sube o baja | Apertura o cierre de escena |
| `arc shot` | Rodea al sujeto | Momento de revelación de producto o personaje |
| `handheld` | Cámara en mano | Tensión, documental |
| `whip pan` | Barrido rápido | Transición enérgica entre planos |
| `aerial shot`, `drone shot` | Desde el aire | Establecer lugar |
| `rack focus` | Cambia el foco | Pasar la atención de un objeto a otro |

Encuadres: `extreme close-up`, `close-up`, `medium close-up`, `medium shot`, `full shot`, `wide shot`, `over-the-shoulder shot`, `POV shot`. Ángulos: `eye-level`, `low-angle`, `high-angle`, `bird's-eye view`, `dutch angle`.

Reglas:
- Lente, tamaño de plano y ángulo deben encajar entre sí («extreme close-up» con «wide-angle lens» deforma la cara).
- Un movimiento por plano. Dolly + pan + zoom en 8 s produce cámaras imposibles.
- Movimiento físicamente posible: una cámara no atraviesa paredes ni gira 360° en una habitación pequeña.
- Si el resultado parece genérico, corrige cámara, puesta en escena y luz antes de añadir adjetivos.

## Continuidad: el libro de estado

Los modelos no recuerdan nada entre generaciones. Lo que debe persistir se escribe. Para cada plano, `estado_final` registra lo que el siguiente debe heredar:

- Posición en cuadro (izquierda/derecha) y dirección de la mirada y del movimiento.
- Vestuario y su estado (manchado, mojado, remangado).
- Objetos: dónde están, abiertos o cerrados, llenos o vacíos.
- Luz y hora: `L#`, encendida o apagada.
- Eje de acción (regla de 180°): de qué lado está la cámara respecto a la línea que une a los personajes o al personaje y su objetivo.

En el prompt del plano siguiente se describe ese estado completo. Prohibido «igual que antes», «la misma mujer», «sigue mojado»: el modelo no sabe qué era antes. `flowprompt.py validar` busca esas expresiones.

Dos tipos de enlace:
- **Continuación:** la cámara no cambia. El plano empieza con el último fotograma del anterior (`R##`) o con Extend, y su composición inicial coincide.
- **Corte:** cambia la cámara. El estado de la historia continúa, pero el encuadre es el nuevo; se compone un fotograma clave nuevo desde las anclas.

## Transiciones

La mayoría se hacen en el montaje (motion-studio): corte en la acción, corte por mirada, match cut por forma o color, fundido con motivo. Para una transición generada:
- **Morph o transformación:** Frames con inicio y fin (`K##` → `K##f`).
- **Whip pan:** se pide al final de un plano y al inicio del siguiente, en la misma dirección.
- No pidas «transition to the next scene» dentro de un clip: el modelo inventa la escena siguiente.

## Ritmo y curva de energía

Aplica la curva de motion-studio (gancho, re-ganchos, pausas, clímax, cierre). El gancho son los 2–3 primeros segundos montados: acción en curso, contraste o pregunta visual, nunca un logo. Reparte los planos más fuertes (cámara activa, primeros planos, revelaciones) también en el centro y en el clímax. Copia los tiempos de la curva al `motion.config.json` del montaje.

## Animatic antes de gastar créditos

Con los fotogramas clave aprobados (0 créditos), monta un animatic: cada `K##` quieto el tiempo de su plano, con la narración o una pista guía. `python scripts/a_motion_studio.py --animatic` lo prepara para motion-studio. Revela problemas de ritmo, de orden y de continuidad antes de generar video. Es opcional en piezas de 3–4 planos; recomendable desde 6.

## Aprobación (puerta 3)

Presenta el storyboard (`STORYBOARD.md`), la hoja de fotogramas clave y una estimación de gasto: planos × salidas × intentos esperados (1,5–2 de media) × créditos por segundo que muestra Flow. Pregunta con el aviso de motion-studio:

> ¿Apruebas este storyboard y sus fotogramas clave, y autorizas generar en Flow la muestra de los planos P0X y P0Y (unos N créditos)? El resto se generará después de revisarla.

La muestra son los 1–2 planos más difíciles (actuación, manos, producto en movimiento), no el más fácil.
