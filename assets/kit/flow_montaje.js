// Montaje de clips de Flow para motion-studio (modo animación).
// Lee recursos/flow/clips.json (lo escribe a_motion_studio.py) y dibuja, para cada t, el fotograma
// que toca de cada clip, con fundidos entre planos cuando el plan los declara.
// Contrato de motion-studio: todo depende solo de t; sin relojes, sin estado entre fotogramas.
// Requiere kit/secuencia.js cargado antes.
(function (g) {
  'use strict';

  async function crearMontajeFlow(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Montaje Flow: no se pudo leer ${url} (${r.status})`);
    const datos = await r.json();
    if (typeof g.crearSecuencia !== 'function') throw new Error('Montaje Flow: carga kit/secuencia.js antes');
    const clips = datos.clips.map(c => Object.freeze({
      ...c,
      sec: g.crearSecuencia({ ruta: c.ruta, cantidad: c.cantidad, fps: c.fps, primero: c.primero || 0,
                              digitos: c.digitos || 4, extension: c.extension || 'png', cache: 3 })
    }));
    if (!clips.length) throw new Error('Montaje Flow: clips.json no tiene clips');
    const fin = c => c.inicio + c.duracion;

    // Clips visibles en t, en orden de dibujo, con su opacidad.
    function capas(t) {
      const activos = clips.filter(c => t >= c.inicio && t < fin(c));
      if (!activos.length) {
        const c = t < clips[0].inicio ? clips[0] : clips[clips.length - 1];
        return [{ clip: c, local: t < c.inicio ? 0 : c.duracion - 1e-6, alfa: 1 }];
      }
      return activos.map((c, i) => {
        let alfa = 1;
        if (i > 0 && c.fundido_entrada > 0 && t < c.inicio + c.fundido_entrada) {
          alfa = Math.max(0, Math.min(1, (t - c.inicio) / c.fundido_entrada));
        }
        return { clip: c, local: Math.min(Math.max(t - c.inicio, 0), c.duracion - 1e-6), alfa };
      });
    }

    function cubrir(ctx, im, W, H, alfa) {
      const s = Math.max(W / im.width, H / im.height);
      const w = im.width * s, h = im.height * s;
      ctx.save();
      ctx.globalAlpha = alfa;
      ctx.drawImage(im, (W - w) / 2, (H - h) / 2, w, h);
      ctx.restore();
    }

    return {
      datos,
      duracion: datos.duracion_total,
      // Plano y tiempo local en t (para anclar rótulos al plano).
      planoEn(t) {
        const c = capas(t);
        const arriba = c[c.length - 1];
        return { id: arriba.clip.id, local: arriba.local, inicio: arriba.clip.inicio };
      },
      async dibujar(ctx, t, W, H) {
        for (const { clip, local, alfa } of capas(t)) {
          const im = await clip.sec.fotograma(local);
          cubrir(ctx, im, W, H, alfa);
        }
      },
    };
  }

  g.crearMontajeFlow = crearMontajeFlow;
})(globalThis);
