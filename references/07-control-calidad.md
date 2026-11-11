# Etapa 6 · Control de calidad y corrección

Cada clip se revisa antes de aprobarlo, y el video completo se revisa antes de entregarlo. Las mediciones automáticas señalan dónde mirar; la decisión sale de mirar los fotogramas y de reproducir el clip. No se aprueba nada que no se haya observado.

## Revisión de un clip

```bash
python scripts/qc_clips.py <proyecto> P01 05-clips/raw/P01_v1.mp4
```

Hace, sin gastar créditos:

| Comprobación | Qué detecta | Tipo |
| --- | --- | --- |
| Formato | Duración, resolución, relación de aspecto y fps frente al plan; si trae audio | Bloqueante si no coincide la relación de aspecto o la duración se aleja más de 0,5 s |
| Fidelidad al fotograma inicial | En `frames`, compara el primer fotograma con `K##` (similitud estructural y color) | Aviso si baja de 0,55: el modelo no respetó el inicio o lo recortó |
| Fidelidad al final | En `frames_ultimo`, compara el último con `K##f` | Aviso |
| Cortes internos | Cambios de plano dentro del clip | Bloqueante si `toma_unica` es `true` (Omni corta por defecto) |
| Parpadeo | Saltos bruscos de luminancia entre fotogramas sin corte | Aviso |
| Salto de luz o de escena | El color del fondo (mitad superior) cambia en 0,5 s y no vuelve, aunque la composición se parezca. Pasa en Frames cuando inicio y fin no comparten luz ni fondo | Bloqueante con ΔE ≥ 4, aviso desde 1,8 (umbral medido en la-piscina-azul) |
| Congelado y negro | Tramos quietos de más de 1 s o fotogramas negros | Aviso |
| Deriva de color | Distancia de color (ΔE en Lab) entre cada fotograma y el ancla del plano | Aviso por encima de 12: la luz o el grado cambió |
| Caras (opcional, `--caras`) | Número de caras por fotograma y recortes de cara junto a la del ancla | Aviso si aparecen más caras de las previstas |

Y deja en `07-qc/P01/`:
- `hoja.jpg`: el ancla y el fotograma clave a la izquierda, 12 fotogramas del clip con su tiempo y los cortes marcados.
- `caras.jpg` (con `--caras`): la cara del ancla y las de los fotogramas, a la misma escala.
- `ultimo.png`: el último fotograma, listo para ser el relevo `R##` del plano siguiente.
- `qc.json`: las medidas y avisos.

**Después mira `hoja.jpg` (y `caras.jpg`) con la herramienta de lectura de imágenes, y reproduce el clip.** Recorre la lista de defectos de abajo. Las métricas no ven una mano con seis dedos.

## Defectos que se buscan

| Familia | Qué mirar | Gravedad habitual |
| --- | --- | --- |
| **Identidad** | Cara distinta a la maestra (forma, ojos, nariz, edad), pelo que cambia de color o largo, rasgos de `no_cambiar` que desaparecen | Bloqueante |
| **Deformaciones** | Manos (dedos de más o de menos, fusionados), extremidades que se doblan mal, dientes, ojos desalineados, cuerpos que se funden con objetos | Bloqueante si se ve a tamaño de entrega |
| **Producto** | Proporciones, forma, tapa o etiqueta que cambian; texto inventado en la etiqueta | Bloqueante |
| **Lugar** | Disposición distinta al párrafo del set (la puerta cambió de lado), objetos que aparecen o desaparecen, perspectiva imposible | Bloqueante si rompe la geografía; mayor si es un detalle |
| **Movimiento** | Pies que patinan, objetos que flotan o atraviesan, transformaciones (morphing), cámara imposible, velocidad irreal, gesto que no termina | Mayor |
| **Continuidad** | Vestuario, objetos o luz que no coinciden con `estado_final` del plano anterior; salto de eje (180°); mirada en la dirección equivocada | Mayor |
| **Storyboard** | La acción, el encuadre o el movimiento de cámara no son los del plan; el estado final no se alcanza | Bloqueante si cambia el sentido; mayor si es de forma |
| **Texto** | Letras, subtítulos o marcas que aparecen en la imagen | Bloqueante (o se recorta fuera del `uso`) |
| **Audio** | Música, voces o risas no pedidas; diálogo distinto al guion; mala sincronía labial | Mayor (se silencia o se regenera) |
| **Técnico** | Parpadeo, compresión, resolución baja, cortes internos no pedidos | Mayor |

Un defecto que cae fuera del tramo `uso` del plano no cuenta: se recorta. Anótalo igual.

## Escalera de corrección

Aplica el primer peldaño que resuelva el defecto. Cada intento se registra en la bitácora.

1. **Recortar.** Si el defecto está al principio o al final, ajusta `uso`. Cero créditos.
2. **Editar el clip** (Omni Flash 1.2): un defecto localizado (una mano, un objeto que sobra, un texto). Prompt corto + «Keep everything else the same.» Máximo 3 turnos.
3. **Regenerar con el mismo prompt** solo si el fallo parece aleatorio (una variante buena entre varias). Pide x2.
4. **Corregir el prompt:** el defecto se repite → la causa está en el prompt. Simplifica la acción, mueve la restricción arriba, quita palabras ambiguas, nombra el papel de cada referencia.
5. **Reforzar el ancla:** identidad o lugar que derivan → mejor fotograma clave (más cercano a la maestra, mejor luz, cara más grande), o pasa de Ingredients a Frames.
6. **Cambiar el modo o el modelo:** Frames con inicio y fin para fijar el final; Extend en vez de encadenar relevos; Omni 1.2 en vez de Veo para acciones con intervalos.
7. **Replantear el plano:** dividir la acción en dos planos, cambiar el encuadre (manos fuera de cuadro, cara más grande), tapar con un plano de reacción o de detalle.

Límite: **tres generaciones fallidas del mismo plano** → para, vuelve al peldaño 6 o 7 y cuéntaselo al usuario con el coste gastado. Regenerar diez veces el mismo prompt no es control de calidad.

## Revisión del video completo

Cuando el montaje existe (motion-studio):

1. `node render.mjs --sheet` y `python sheet.py`, o la hoja de `qc_clips.py` por plano: mira la secuencia entera de fotogramas buscando saltos de identidad y de luz **entre** planos, que el QC por clip no ve.
2. `node render.mjs --ritmo` y `ritmo.py`: energía por tramos frente a la curva del storyboard.
3. `python verificar.py` sobre la exportación: formato, LUFS, picos, negros y congelados.
4. Reproduce la pieza completa. Comprueba cortes, continuidad de mirada y dirección, sincronía y lectura de rótulos.
5. Puntúa con las rúbricas de motion-studio y con estas cuatro, de 1 a 10, con evidencia por plano y tiempo:

| Criterio | 8/10 significa |
| --- | --- |
| **Consistencia de identidad** | Cada personaje, producto y lugar se reconoce como el mismo en todos los planos; ningún rasgo de `no_cambiar` cambia |
| **Integridad física** | Ninguna deformación visible a tamaño de entrega; movimiento creíble |
| **Fidelidad al storyboard** | Acciones, encuadres y enlaces son los aprobados, o los cambios están acordados |
| **Continuidad entre planos** | Vestuario, objetos, luz, eje y mirada coinciden con el libro de estado |

Un bloqueante abierto limita su criterio a 4. Objetivo: 8 o más en todos. Corrige los tres problemas más graves por ronda, máximo tres rondas; después, presenta los pendientes al usuario sin subir notas.

Anota todo en `07-qc/REVISION.md`: plano, tiempo, defecto, peldaño aplicado, resultado y créditos.
