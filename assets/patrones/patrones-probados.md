# Patrones probados

Biblioteca de lo que funciona (y lo que no) con Flow, las herramientas y el estilo del usuario. Léela antes de planificar un proyecto: lo que está aquí, con evidencia, tiene prioridad sobre las recomendaciones generales de las guías.

Se añade con `python scripts/bitacora.py promover …`. Un patrón necesita evidencia (proyecto, planos, resultado). Un antipatrón, al menos dos fallos. Si algo deja de funcionar porque Flow cambió, se marca «obsoleto» con la fecha; no se borra.

## Patrones

### Resolver en imagen antes de gastar en video
- **Estado:** confirmado · 2026-11-10
- **Contexto:** Flow, Nano Banana 2.1, imágenes 9:16 x2 y reescalado a 2K.
- **Técnica:** Generar anclas, derivadas y fotogramas clave con Nano Banana; solo se anima lo que ya está aprobado en imagen.
- **Evidencia:** Piloto «La guerra de los pasteles» (canal Ojalá No, 10 nov 2026): 13 prompts × 2 imágenes y 4 reescalados a 2K con 0 créditos de Flow.

### Criatura quieta en los planos donde no actúa
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames, 720p; criatura sin extremidades (puffle) mientras la cámara se mueve
- **Técnica:** Declarar la criatura en 'quietos' del plano: el prompt dice que se queda completamente quieta, solo parpadea y nunca muestra patas ni brazos, en lugar de su regla de movimiento
- **Evidencia:** puffle-que-dejaste (11 nov 2026): P02 v3 y v4 sin 'quietos' sacaron pies (2 de 2); P02 v5 y P04 v1 y v2 con 'quietos', limpias (3 de 3)

### Toma continua: relevo de inicio y fotograma clave de fin
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames con inicio y fin; escena en primera persona dividida en clips de 5-6 s
- **Técnica:** Cada clip empieza en el último fotograma aprobado del anterior (relevo subido a Flow) y, cuando hay que volver a la identidad aprobada, termina en un fotograma clave; en el montaje el clip siguiente empieza un fotograma después
- **Evidencia:** puffle-que-dejaste (11 nov 2026): P02 v3, v4 y v5 terminaron en K02 con similitud 0,97; las tres uniones del render final no se notan (hoja 07-qc/final)

### Todo clip con un personaje que aparece termina en un fotograma clave
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2; clip de llegada que descubre el lugar y al personaje
- **Técnica:** Si un clip descubre el lugar o al personaje a mitad de camino, usar Frames con inicio y fin (fin = fotograma clave aprobado). Con solo el inicio, el modelo inventa lo que no ve en el primer fotograma.
- **Evidencia:** la-piscina-azul (11 nov 2026): P01 con solo K01 (botas en la hierba) inventó piscina rectangular y otras casas (2 de 2). P01 de K01 a K02 llegó al patio correcto en 2 de 2, con unión SSIM 0,97 con el clip siguiente

### Revelación en un reflejo: fotograma final compuesto con la orilla real vacía
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames con inicio y fin; personajes que solo existen en el reflejo del agua
- **Técnica:** Componer en Nano Banana el fotograma final (orilla real vacía, personajes invertidos en el agua) y animar desde el plano anterior con «on the real far rim there is nobody». Los personajes del reflejo NO se declaran como entidad del plano (si se nombran, el prompt los describe de pie y aparecen en la orilla).
- **Evidencia:** la-piscina-azul P05 (11 nov 2026): 360p ×2 y 720p ×2, 4 de 4 llegan al reflejo con la orilla vacía. En el fotograma clave, 1 de 4 salió bien a la primera (K05 n.º 2)

## Heredados, pendientes de confirmar en un proyecto propio

Vienen de la documentación oficial o de skills revisadas. Pasan a «Patrones» cuando la bitácora los confirme.

### Plano único en Omni Flash
- **Fuente:** documentación de Gemini Omni Flash (aistudio.google.com/docs/omni).
- **Técnica:** Omni crea varios planos por defecto; para un plano único, «Single continuous shot. No scene cuts.» al principio del prompt.

### Ediciones cortas en Omni
- **Fuente:** documentación de Gemini Omni Flash.
- **Técnica:** Una corrección por turno y «Keep everything else the same.» al final.

### Gesto pequeño sobre croma
- **Fuente:** skill director-de-collage (Omni 1.1 Flash).
- **Técnica:** «Locked-off static camera, no camera movement, no zoom…» y «The plain flat green background stays perfectly flat and unchanged» para que la IA no mueva la cámara ni el fondo.

### Diálogo sin subtítulos
- **Fuente:** skill prompt-videos (Replicate).
- **Técnica:** Diálogo tras dos puntos, sin comillas, con «(no subtitles)».

## Antipatrones

### Encadenar ediciones de ediciones
- **Fuente:** práctica general de consistencia; pendiente de medir en la bitácora.
- **Problema:** Cada edición sucesiva de una imagen se aleja un poco de la cara original. Derivar siempre desde la maestra.

### Mucha distancia y un cambio de postura en el mismo clip
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames con inicio y fin, 5 y 8 s
- **Problema:** Si entre el inicio y el fin la cámara recorre mucha distancia (de plano general a primer plano) y además el personaje cambia de postura (sentado → de pie), el modelo hace bien la primera mitad y luego salta al fotograma final. Alargar el clip no lo arregla. Hay que dividirlo con un fotograma intermedio derivado (`derivada_de`) en dos clips cortos: uno para el cambio de postura y otro para el acercamiento.
- **Evidencia:** la-piscina-azul P03 (11 nov 2026): de 5 s, 1 de 2 con salto; de 8 s, 2 de 2 con salto (~4,1 y ~4,7 s). Dividido en P03a + P03b con K02b: 3 de 4 variantes limpias, uniones con SSIM de 0,98–0,99

### Inicio y fin de un clip con luz o fondo distintos
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames con inicio y fin, 720p
- **Problema:** Si el fotograma de inicio y el de fin no comparten luz, fondo y posición del personaje (por ejemplo, uno editado aparte), el modelo no interpola: a mitad de clip «salta» de una foto a la otra, sin corte pero visible. Los fotogramas de un mismo clip se derivan uno del otro (editar el de fin para hacer el de inicio) o de la misma imagen. `qc_clips.py` lo marca como «salto de luz o de escena».
- **Evidencia:** la-piscina-azul P04 v1 y v2 (11 nov 2026): 2 de 2 con salto (a 3,1 s y a 2,2–2,8 s) entre K03 editado (casas pastel, Pablo sentado lejos) y K04 (casas oscuras, Pablo cerca)

### Pedir a una criatura sin extremidades que salte o se alegre
- **Estado:** confirmado · 2026-11-11
- **Contexto:** Omni Flash 1.2, Frames, 720p; puffle rosa (bola de pelo sin patas)
- **Problema:** «bounces up and down with joy» hace que el modelo le añada patas, brazos y boca y lo mueva de sitio. Hay que describir el movimiento físico sin extremidades («hops like a soft rubber ball, squashing when it lands») en movimiento_en y excluir «legs, feet, arms or hands on the creature».
- **Evidencia:** puffle-que-dejaste, P02 v1 y v2 (11 nov 2026): 2 de 2 variantes con patas y brazos desde 3,3 s; 0,3-3,2 s limpios
