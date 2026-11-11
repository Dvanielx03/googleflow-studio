# Etapa 3 · Sistema de imágenes ancla

Una imagen ancla es la referencia visual aprobada de algo que se repite en el video: un personaje, un producto o un lugar. El video no se genera desde la imaginación del modelo, sino desde estas imágenes. Así el personaje es el mismo de principio a fin y los escenarios son los del storyboard, no otros parecidos.

No significa usar la misma foto en todos los planos. Significa que **todas las imágenes de un personaje, producto o lugar descienden de una misma ancla maestra** y conservan su identidad: cada plano tiene su ángulo, su luz y su pose, pero es la misma cara, el mismo envase y la misma habitación.

Registro: `02-anclas/anclas.json`. Solo las anclas con `"estado": "aprobada"` entran a un video.

## La jerarquía

```
Nivel 0 · Ancla maestra (A0)      una por entidad; define la identidad
   │  se edita con Nano Banana a partir de la maestra
Nivel 1 · Anclas derivadas (A1-…) ángulos, expresiones, vestuario, luz, zonas del lugar
   │  se combinan varias en una composición
Nivel 2 · Fotograma clave (K##)   el primer fotograma de un plano concreto (y K##f, el último, si hace falta)
   │  Flow lo anima
Clip del plano (P##)
   │  su último fotograma aprobado
Relevo (R##)                      inicio del plano siguiente cuando la acción continúa
```

### Nivel 0 · Anclas maestras

| Entidad | Ancla maestra | Cómo se hace |
| --- | --- | --- |
| **Personaje** | `A0` retrato de identidad: pecho arriba, de frente, expresión neutra, luz suave y pareja, fondo gris claro liso. Opcional `A0-cuerpo`: cuerpo entero con el vestuario `V1`, mismo fondo. | Nano Banana Pro con la ficha de identidad de la biblia. Si es una persona real, su foto (con permiso) es la maestra. Genera 4 variantes, elige una, súbela a 2K. |
| **Producto** | `A0` packshot en tres cuartos sobre fondo blanco o gris liso, luz de estudio suave, proporciones exactas, etiqueta lisa. | La foto real del producto siempre gana. Si no hay, Nano Banana Pro con la ficha de producto. |
| **Lugar** | `A0` plano general vacío, sin personas, con la luz base `L1` y el párrafo fijo del set. Si el lugar se ve siempre desde un punto concreto (el interior de un coche desde el copiloto), pon ese encuadre en `encuadre_en` del ancla. | Nano Banana 2.1 o Pro con el prefijo de estilo + `disposicion_en`. |

La luz neutra y el fondo liso en personajes y productos no son estética: dejan la identidad sin contaminar. Flow recomienda referencias de sujeto o producto sobre fondo liso o recortado. Un ancla de personaje con un fondo cargado mete ese fondo en todos los planos.

En Flow, crea un **personaje** por cada persona recurrente: Characters → New Character → sube `A0` (y `A0-cuerpo`) → nombre = el handle sin `@` → Select a voice → Add to Character → Done. Un personaje admite 1 o 2 imágenes y una voz. Desde entonces se invoca con `@Valeria` en cualquier prompt. Guarda lugares y productos en una colección «Anclas» del proyecto.

### Nivel 1 · Anclas derivadas

Se generan **editando la maestra**, no desde cero. Cada derivada cambia una sola cosa y declara lo que se conserva:

- **Personaje:** perfil, tres cuartos, espalda; las expresiones que el guion necesita (sorpresa, risa contenida); el vestuario `V2`; la luz de una escena (`L2`, noche).
- **Lugar:** contraplano, zonas concretas (la barra, la puerta), otra hora del día con la misma disposición.
- **Producto:** otros ángulos, en la mano del personaje, abierto o en uso.

Prompt de derivada (plantilla; `flowprompt.py prompts` la rellena):

```
Using the attached image as the identity reference, keep exactly the same face, facial proportions, hairstyle, skin tone, age and clothing. Change only: [una sola variación]. [prefijo de estilo]. [luz]. Plain light grey seamless background. No text, no watermark.
```

### Nivel 2 · Fotograma clave del plano (K)

Es la imagen que decide el plano: encuadre, lente, pose inicial, luz y lugar exactos. Se compone en Nano Banana adjuntando las anclas aprobadas (personaje, lugar, producto) y describiendo el primer instante del plano según la ficha del storyboard. Después Flow lo anima con **Frames to video**.

```
Using the attached references: [@Valeria (character), @TostaduriaSantaRita (location), @BolsaOrigen (product)]. Compose the first frame of the shot: [encuadre y ángulo], [lente y profundidad de campo]. [Estado inicial: pose, mirada, dónde está cada cosa]. [Luz L#]. Keep the character's face, hair and clothing identical to her reference, the product identical to its reference and the layout of the place identical to the location reference. [prefijo de estilo]. No text, no watermark.
```

El fotograma clave lleva la relación de aspecto del video (9:16 o 16:9). Si el plano termina en un estado preciso (una transformación, el producto en una posición exacta), genera también `K##f` y usa Frames con inicio y fin (máximo 10 s en Omni 1.2).

### Relevos (R)

Cuando el plano siguiente continúa la acción sin cambiar de cámara, su inicio es el último fotograma del clip aprobado: en Flow, pausa al final y **Save frame**, o usa el `ultimo.png` que deja `qc_clips.py`. Si la acción continúa más de 10 s en el mismo plano, **Extend** (Omni Flash 1.2, de pago) mantiene mejor la continuidad: usa los últimos 10 s como contexto y admite hasta 3 imágenes de referencia.

## Reglas que no se rompen

1. **Nada recurrente sale solo de texto.** Cada aparición de un personaje, producto o lugar recurrente lleva su ancla: como fotograma clave, como ingrediente o como `@Personaje`. El texto a video solo sirve para recursos sin identidad (cielo, textura, multitud lejana).
2. **Deriva desde la maestra, no desde copias.** Una edición de una edición de una edición pierde la cara poco a poco. Profundidad máxima: maestra → derivada → fotograma clave. Si necesitas otra variante, vuelve a la maestra.
3. **Re-ancla cada dos relevos.** Encadenar el último fotograma de un clip como inicio del siguiente acumula deriva. Tras dos relevos seguidos, compón un fotograma clave nuevo desde las anclas.
4. **Una variación por derivada.** Cambiar ángulo, ropa y luz a la vez abre la puerta a cambiar también la cara.
5. **Cada ancla, una función.** La identidad (cara) no comparte imagen con la escena. Lugares sin personas; personajes y productos sobre fondo liso.
6. **Puerta de identidad antes de gastar créditos.** Cada fotograma clave se compara lado a lado con la maestra (rasgos de `no_cambiar` de la biblia) y se aprueba antes de animarlo. Las imágenes en Flow no gastan créditos; el video sí. Todo lo que se pueda decidir en imagen se decide en imagen.
7. **Respeta el límite de referencias del modelo** (`assets/flow_capacidades.json`): Omni Flash 1.2 admite hasta 6 imágenes (3 por personaje, 2 personajes); Veo 3.1 Lite y Fast, 3 ingredientes; Extend, 3. Si un plano reúne más identidades, compón un fotograma clave que las contenga y anímalo con Frames.
8. **Sin texto en las anclas.** Ni carteles, ni etiquetas legibles, ni marcas de agua: lo que se escribe sale deformado y cambia entre planos. El texto va en el montaje.
9. **Todo queda registrado** en `anclas.json`: id, entidad, nivel, padres, archivo, modelo, prompt y estado. `flowprompt.py validar` rechaza un plano que use un ancla no aprobada o inexistente.
10. **Referencia solo de estilo** (`"solo_estilo": ["Lugar.A0"]` en el fotograma clave). Úsala cuando el encuadre no muestra el lugar, por ejemplo una mirada al suelo o un primer plano de las manos. Así el padre aporta color, luz y texturas sin imponer su composición. Si el lugar se adjunta como referencia normal, Nano Banana copia el plano general. Se vio en la-piscina-azul, K01 v1: 4 de 4 imágenes repitieron el patio entero con las piernas estiradas, y la v2 con `solo_estilo` sí salió mirando al suelo.

## Elegir el modo de Flow para cada plano

| Situación del plano | Modo | Qué se adjunta |
| --- | --- | --- |
| Personaje o producto recurrente en una composición concreta (el caso normal) | **Frames** (inicio) | `K##` |
| Transformación o final exacto | **Frames** (inicio y fin) | `K##` + `K##f` |
| Acción libre de 1–2 personajes donde el encuadre puede variar | **Ingredients** | Anclas del personaje (`@Handle`) + lugar + producto |
| La acción continúa sin corte | **Extend** (Omni 1.2) o **Frames** con `R##` | El clip anterior o su último fotograma |
| Un clip bueno con un defecto localizado | **Editar** (Omni 1.2, hasta 3 turnos) | El clip + el ancla si hay que restaurar algo |
| Recurso sin entidades recurrentes | **Texto** | — |

Frames da el máximo control y es el modo por defecto. Ingredients deja más libertad al modelo: úsalo cuando esa libertad aporte (movimiento complejo, cámara que descubre), y revísalo más en el QC.

## Nombres de archivo

```
02-anclas/personajes/Valeria.A0.png         maestra (retrato)
02-anclas/personajes/Valeria.A0-cuerpo.png  maestra (cuerpo entero, V1)
02-anclas/personajes/Valeria.A1-perfil.png  derivada
02-anclas/lugares/TostaduriaSantaRita.A0.png
02-anclas/productos/BolsaOrigen.A0.png
02-anclas/fotogramas/K01.png  K01f.png
02-anclas/relevos/R02.png                   último fotograma aprobado de P01, inicio de P02
```

El id del ancla es el nombre del archivo sin extensión. La entidad es el handle con `@`.

## Qué revisar en una ancla antes de aprobarla

- Cara: simetría razonable, ojos alineados, dientes y orejas normales; rasgos de `no_cambiar` presentes.
- Manos (si se verán): cinco dedos, articulaciones posibles, contacto real con los objetos.
- Producto: proporciones de la ficha, sin texto inventado, bordes y tapas coherentes.
- Lugar: coincide con el párrafo fijo (puerta, ventana, muebles en su sitio), perspectiva sin líneas imposibles, sin carteles con letras.
- Luz: dirección y temperatura de la `L#` asignada.
- Formato: relación de aspecto correcta en los fotogramas clave; maestras descargadas en 2K.
