# Etapa 2 · Biblia visual

La biblia es el contrato de identidad del video. Todo prompt sale de ella, palabra por palabra. Si un dato no está en la biblia, el modelo lo inventa en cada clip, y cada clip lo inventa distinto.

Fuente de verdad: `01-biblia/biblia.json`. `python scripts/flowprompt.py biblia` genera `01-biblia/BIBLIA.md` para presentarla al usuario. No edites el Markdown a mano: cambia el JSON y vuelve a generarlo.

## Qué define

| Bloque | Qué fija | Cómo se escribe |
| --- | --- | --- |
| **Estilo** | Lenguaje (realista, animación 3D, stop-motion, anime…), cámara y película, grano, contraste | `estilo.prefijo_en`: una frase en inglés que abre todos los prompts de imagen y de video. Concreta: «Photorealistic cinematic still, shot on 35mm film, natural skin texture, soft film grain, gentle contrast». Nunca «epic», «stunning», «masterpiece». Opcional `estilo.prefijo_referencias_en`: el mismo medio sin la luz ni el cielo de las escenas, para las anclas de personajes y productos sobre fondo neutro. |
| **Paleta** | 3–6 colores con papel (dominante, acento, sombra) | Cada color con `hex` (para el montaje) y `nombre_en` («deep teal», «burnt orange»). En los prompts solo va el nombre: un código hex en un prompt puede salir escrito en la imagen. |
| **Iluminaciones** | Un esquema por escena o momento: `L1`, `L2`… | Fuente, dirección, dureza, temperatura en palabras («warm tungsten», no «3200K»), contraste y relación sujeto/fondo. |
| **Texturas y materiales** | Superficies que se repiten: madera, metal, tela, piel | Una frase por material. |
| **Personajes** | Identidad fija | Ficha de identidad (ver abajo), en inglés, literal. |
| **Lugares** | Disposición del espacio | Párrafo fijo del set (ver abajo). |
| **Productos** | Forma, proporciones, materiales, etiqueta | Ficha de producto (ver abajo). |
| **Política de texto** | Qué texto puede aparecer en imagen | Por defecto ninguno: rótulos, logos y subtítulos se ponen en el montaje. |
| **Política de audio** | Nativo de Flow, en postproducción o mixto | Ver `06-produccion-audio.md`. |

## Ficha de identidad de un personaje

Escríbela una vez, en inglés, y pégala igual en cada prompt donde el personaje no tenga una imagen de inicio que ya lo muestre. Cambiar una palabra («auburn» por «reddish») es pedir otra persona.

Campos de `personajes[]`:

- `handle`: `@` + PascalCase, sin espacios ni tildes (`@Valeria`, `@DonAurelio`). Es el mismo nombre en la biblia, en Flow (Characters), en los archivos y en los prompts.
- `identidad_en`: edad aproximada, complexión, piel, forma de cara, ojos, nariz, pelo (color, largo, peinado), rasgos distintivos (lunar, cicatriz, gafas). Entre 30 y 60 palabras. Rasgos visibles, no carácter.
- `vestuario_en`: por `V1`, `V2`… si cambia de ropa en la historia. Prenda, color, material y estado («faded olive canvas apron with a small burn mark on the left pocket»).
- `forma`: `humano` (por defecto), `criatura` (mascotas y seres sin extremidades, como el puffle) o `animado` (personajes de serie o de juego con brazos y piernas que **conservan su diseño de dibujo o de 3D** dentro del mundo real, como los Backyardigans). Cambia las plantillas:
  - una criatura se retrata entera y se conservan «forma, colores y ojos»;
  - un personaje animado se retrata entero en tres cuartos como hoja de diseño («not turned into a realistic animal»), se conservan «diseño, proporciones, colores, ojos y vestuario» y, cuando está en `quietos`, solo parpadea y respira, sin prohibirle las extremidades.
- `nombre_en`: cómo se nombra en los prompts de Frames, donde no hay referencias adjuntas («the small pink fluffy creature»). Sin él, se usa el handle sin `@`.
- `movimiento_en` (criaturas): cómo se mueve, empezando por el verbo, porque va detrás del nombre en cada prompt de video («has no legs and no arms and moves only by hopping like a soft rubber ball»). Sin esto, al pedir que salte o se alegre, el modelo le inventa patas y brazos (visto en el piloto del puffle, nov 2026).
- `voz`: para el audio nativo o la locución (nombre de la voz en Flow o en el servicio de voz, tono, acento).
- `no_cambiar`: lista corta de lo que define al personaje y el QC vigila primero (la cicatriz, el corte de pelo, el delantal).

Personas reales: solo con su permiso y sus fotos como ancla maestra. Flow no admite editar imágenes de ciertas personas reconocibles; si se rechaza, usa espaldas, siluetas, manos u objetos.

## Párrafo fijo del set (lugares)

Para cada lugar, un párrafo en inglés que describe la disposición física, siempre igual: tamaño, dónde están la puerta y la ventana, muebles y su posición, de dónde entra la luz, y desde qué lado mira la cámara principal. Es lo que mantiene la geografía entre planos. Incluye:

- `handle`: `@CafeNocturno`, `@TostaduriaSantaRita`.
- `disposicion_en`: el párrafo fijo.
- `eje`: dónde está la línea de acción para respetar la regla de 180° («la barra queda siempre a la izquierda del cuadro en los planos de Valeria»).
- `luz_base`: la iluminación `L` por defecto.

## Ficha de producto

- `handle`: `@BolsaOrigen`.
- `nombre_en`: cómo se nombra en los prompts de Frames, donde no hay referencias adjuntas («the coffee bag»).
- `descripcion_en`: forma, proporciones (alto × ancho, si es cilíndrico o plano), material, acabado (mate, brillante), colores con nombre y la zona de etiqueta.
- `texto_real`: lo que dice la etiqueta. **No se pide al modelo que lo escriba**: se deja la etiqueta lisa o se usa la foto real del producto como ancla. El logo y el texto se colocan en el montaje si hace falta legibilidad.
- `foto_real`: si existe, es el ancla maestra. Una foto real siempre gana a una imagen generada.

## Cómo se construye y aprueba

1. Parte del brief aprobado (etapa 0). Si hay referencias visuales del usuario, extrae de ellas paleta, luz y estilo; no copies obras ajenas.
2. Redacta la biblia en `biblia.json` y genera `BIBLIA.md`.
3. Presenta un resumen legible: estilo en una frase en español, paleta con muestras, quién es cada personaje y cómo se ve cada lugar. Las anclas maestras (etapa 3) son la prueba visual de la biblia: se aprueban juntas.
4. Cambios posteriores: sube la versión en `biblia.json` → `version`. Los planos ya generados con la versión anterior se revisan en el QC por si quedan desalineados.

## Errores frecuentes

- Describir carácter en vez de rasgos: «a kind, wise barista» no fija una cara.
- Paletas con hex o temperaturas Kelvin dentro de los prompts: aparecen como texto en la imagen.
- Estilo distinto en cada prompt (35mm en uno, «digital cinema» en otro): cambia el grano y el color entre planos.
- Personajes demasiado genéricos («a young woman with brown hair»): el modelo no tiene nada que conservar. Añade 2 o 3 rasgos distintivos.
- Etiquetas con texto pedido al modelo: el texto sale deformado y cambia entre planos.
