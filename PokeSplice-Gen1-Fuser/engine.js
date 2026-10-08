/* Pixel fusion engine — no backend, ML inference, canvas libraries, or pre-made fusion images. */
(function (global) {
  'use strict';
  const SIZE = 96;
  const PALETTES = {
    gameboy: ['#0f380f', '#306230', '#8bac0f', '#9bbc0f'],
    blue: ['#172b51', '#36629b', '#80b8d0', '#d9edf0'],
    red: ['#4b2034', '#9b4c59', '#e89c85', '#f9dac3'],
    sepia: ['#362a24', '#77604d', '#bba478', '#f5e9c3']
  };
  function makeCanvas(width, height) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    return canvas;
  }
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  function looksLikeWhiteBg(data, at) {
    const a = data[at + 3];
    if (a < 20) return true;
    const r = data[at], g = data[at + 1], b = data[at + 2];
    return r > 237 && g > 237 && b > 237 && Math.max(r, g, b) - Math.min(r, g, b) < 16;
  }
  function extract(image) {
    const width = image.naturalWidth || image.width;
    const height = image.naturalHeight || image.height;
    if (!width || !height || width > 512 || height > 512) throw new Error('Unable to read sprite pixels.');
    const source = makeCanvas(width, height);
    const context = source.getContext('2d', { willReadFrequently: true });
    context.imageSmoothingEnabled = false;
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, width, height);
    const data = pixels.data;
    const count = width * height;
    let transparent = false;
    for (let i = 0; i < count; i++) if (data[i * 4 + 3] < 20) { transparent = true; break; }
    // Some image archives use opaque white backgrounds; flood-fill just the exterior
    // so white eyes, claws, and internal details are preserved.
    if (!transparent) {
      const seen = new Uint8Array(count);
      const queue = new Int32Array(count);
      let start = 0, end = 0;
      function enqueue(x, y) {
        if (x < 0 || y < 0 || x >= width || y >= height) return;
        const i = y * width + x;
        if (seen[i] || !looksLikeWhiteBg(data, i * 4)) return;
        seen[i] = 1;
        queue[end++] = i;
      }
      for (let x = 0; x < width; x++) { enqueue(x, 0); enqueue(x, height - 1); }
      for (let y = 0; y < height; y++) { enqueue(0, y); enqueue(width - 1, y); }
      while (start < end) {
        const i = queue[start++], x = i % width, y = Math.floor(i / width);
        enqueue(x - 1, y); enqueue(x + 1, y); enqueue(x, y - 1); enqueue(x, y + 1);
      }
      for (let i = 0; i < count; i++) if (seen[i]) data[i * 4 + 3] = 0;
    }
    let minX = width, minY = height, maxX = -1, maxY = -1;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      if (data[(y * width + x) * 4 + 3] < 20) continue;
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    if (maxX < 0) throw new Error('A sprite was blank, so it cannot be fused.');
    context.putImageData(pixels, 0, 0);
    const sw = maxX - minX + 1, sh = maxY - minY + 1;
    const cropped = makeCanvas(sw, sh);
    cropped.getContext('2d').drawImage(source, minX, minY, sw, sh, 0, 0, sw, sh);
    const cutData = cropped.getContext('2d', {willReadFrequently:true}).getImageData(0, 0, sw, sh).data;
    const rowCounts = new Array(sh).fill(0);
    const rowCenters = new Array(sh).fill(sw / 2);
    for (let y = 0; y < sh; y++) {
      let sum = 0, qty = 0;
      for (let x = 0; x < sw; x++) {
        if (cutData[(y * sw + x) * 4 + 3] < 20) continue;
        qty++; sum += x + .5;
      }
      rowCounts[y] = qty;
      if (qty) rowCenters[y] = sum / qty;
    }
    return { canvas: cropped, width: sw, height: sh, rowCounts, rowCenters };
  }
  function seamAt(sprite, fraction, smart) {
    const h = sprite.height;
    const goal = clamp(Math.round(h * fraction), 2, h - 2);
    if (!smart || h < 16) return goal;
    const radius = Math.max(2, Math.round(h * .085));
    const from = clamp(goal - radius, 2, h - 2);
    const to = clamp(goal + radius, 2, h - 2);
    let best = goal, bestScore = Infinity;
    for (let y = from; y <= to; y++) {
      // Prefer a natural narrowing of the silhouette near the requested split.
      // Avoid seeking excessively far from the manual preference.
      const local = (sprite.rowCounts[y - 1] + sprite.rowCounts[y] + sprite.rowCounts[y + 1]) / 3;
      const score = local + Math.abs(y - goal) * 1.25;
      if (score < bestScore) { best = y; bestScore = score; }
    }
    return best;
  }
  function jointCenter(sprite, from, to) {
    let weightedSum = 0, weight = 0;
    for (let y = Math.max(0, from); y <= Math.min(sprite.height - 1, to); y++) {
      const w = sprite.rowCounts[y];
      weightedSum += sprite.rowCenters[y] * w;
      weight += w;
    }
    return weight ? weightedSum / weight : sprite.width / 2;
  }
  function recolor(canvas, paletteName) {
    const stops = PALETTES[paletteName];
    if (!stops) return;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    const image = context.getImageData(0, 0, canvas.width, canvas.height);
    const data = image.data;
    const colors = stops.map(hex => [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]);
    // Classic four-ink palette, quantized from source luminance.
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 20) continue;
      const lum = .2126 * data[i] + .7152 * data[i + 1] + .0722 * data[i + 2];
      const bucket = lum < 71 ? 0 : lum < 143 ? 1 : lum < 213 ? 2 : 3;
      data[i] = colors[bucket][0];
      data[i + 1] = colors[bucket][1];
      data[i + 2] = colors[bucket][2];
    }
    context.putImageData(image, 0, 0);
  }
  // Pixel-space masks produce a naturally uneven neck edge while retaining
  // the original silhouette. No blur, resampling, or generative model is used.
  function maskedSection(sprite, cut, part, mode, sideKeep = null) {
    if (mode === 'classic') return sprite.canvas;
    const copy = makeCanvas(sprite.width, sprite.height);
    const ctx = copy.getContext('2d', {willReadFrequently:true});
    ctx.drawImage(sprite.canvas, 0, 0);
    const image = ctx.getImageData(0, 0, sprite.width, sprite.height);
    for (let y = 0; y < sprite.height; y++) {
      const center = sprite.rowCenters[y] || sprite.width / 2;
      for (let x = 0; x < sprite.width; x++) {
        const distance = clamp(Math.abs(x + .5 - center) / Math.max(5, sprite.width * .5), 0, 1);
        // The middle of the cut is slightly lower than the edges, like a neck.
        const offset = Math.round(3 - 5 * distance * distance);
        const boundary = cut + offset;
        let keep = part === 'head' ? y < boundary : y >= boundary;
        if (!keep && part === 'body' && sideKeep && y >= cut - Math.round(sprite.height * .28)) {
          const screenX = sideKeep.bodyX + (x + .5) * sideKeep.bodyScale;
          keep = screenX < sideKeep.headX - 2 || screenX > sideKeep.headX + sideKeep.headW + 2;
        }
        if (!keep) image.data[(y * sprite.width + x) * 4 + 3] = 0;
      }
    }
    ctx.putImageData(image, 0, 0);
    return copy;
  }
  function neckInk(sprite, cut) {
    const data = sprite.canvas.getContext('2d', {willReadFrequently:true}).getImageData(0, 0, sprite.width, sprite.height).data;
    const x0 = Math.max(0, Math.floor(sprite.rowCenters[Math.max(0, cut - 1)] - 3));
    const x1 = Math.min(sprite.width - 1, x0 + 6);
    for (let y = Math.min(sprite.height - 1, cut); y >= Math.max(0, cut - 7); y--) {
      for (let x = x0; x <= x1; x++) {
        const i = (y * sprite.width + x) * 4;
        if (data[i + 3] > 220) return `rgb(${data[i]},${data[i + 1]},${data[i + 2]})`;
      }
    }
    return '#5a5a5a';
  }
  function fuse(headImage, bodyImage, output, options = {}) {
    if (!output || typeof output.getContext !== 'function') throw new Error('Missing result canvas.');
    const head = extract(headImage), body = extract(bodyImage);
    const fraction = clamp(Number(options.splice ?? 46) / 100, .3, .64);
    const requestedHeadSize = clamp(Number(options.headSize ?? 100) / 100, .65, 1.5);
    const smart = options.smart !== false;
    const mode = ['classic', 'contour', 'graft'].includes(options.mode) ? options.mode : 'contour';
    const headCut = seamAt(head, fraction + .04, smart);
    const bodyCut = seamAt(body, fraction - .07, smart);
    const context = output.getContext('2d', {willReadFrequently:true});
    output.width = SIZE; output.height = SIZE;
    context.imageSmoothingEnabled = false;
    context.clearRect(0, 0, SIZE, SIZE);

    const bodyScale = Math.min(1.48, 67 / body.width, 69 / body.height);
    const bodyX = Math.round((SIZE - body.width * bodyScale) / 2);
    const bodyY = Math.round(84 - body.height * bodyScale);
    const bodyJointY = Math.round(bodyY + bodyCut * bodyScale);
    const bodyJointX = bodyX + jointCenter(body, bodyCut, bodyCut + 4) * bodyScale;

    const fitWidth = Math.min(1.55, 47 / head.width, (body.width * bodyScale * 1.02) / head.width);
    const fitHeight = Math.min(1.6, 43 / Math.max(headCut, 1));
    const headScale = Math.min(fitWidth, fitHeight) * requestedHeadSize;
    const headW = Math.max(1, Math.round(head.width * headScale));
    const headH = Math.max(1, Math.round(head.height * headScale));
    const headJoint = jointCenter(head, headCut - 5, headCut - 1);
    const overlap = clamp(Number(options.overlap ?? 3), 0, 12);
    const shiftX = clamp(Number(options.shiftX ?? 0), -18, 18);
    const shiftY = clamp(Number(options.shiftY ?? 0), -12, 12);
    let headX = Math.round(bodyJointX - headJoint * headScale + shiftX);
    let headY = Math.round(bodyJointY - headCut * headScale + overlap + shiftY);
    headX = clamp(headX, 2, Math.max(2, SIZE - 2 - headW));
    headY = clamp(headY, 2, Math.max(2, SIZE - 4 - headH * .38));

    if (mode === 'classic') {
      const bodyLowerHeight = body.height - bodyCut;
      if (bodyLowerHeight > 0) context.drawImage(body.canvas, 0, bodyCut, body.width, bodyLowerHeight,
        bodyX, bodyJointY, Math.round(body.width * bodyScale), Math.round(bodyLowerHeight * bodyScale));
    } else {
      context.drawImage(maskedSection(body, bodyCut, 'body', mode,
        mode === 'graft' ? {bodyX, bodyScale, headX, headW} : null),
        bodyX, bodyY, Math.round(body.width * bodyScale), Math.round(body.height * bodyScale));
    }
    const jointGap = bodyJointY - (headY + headCut * headScale);
    if (jointGap > 0 && jointGap < 9) {
      const center = Math.round((bodyJointX + headX + headJoint * headScale) / 2);
      context.fillStyle = neckInk(body, bodyCut);
      context.fillRect(center - 3, Math.round(headY + headCut * headScale) - 1, 6, Math.ceil(jointGap) + 3);
    }
    if (mode === 'classic') {
      context.drawImage(head.canvas, 0, 0, head.width, headCut,
        headX, headY, headW, Math.max(1, Math.round(headCut * headScale)));
    } else {
      context.drawImage(maskedSection(head, headCut, 'head', mode), headX, headY, headW, headH);
    }
    recolor(output, options.palette || 'original');
    return {headCut, bodyCut, pixels:SIZE, headScale, bodyScale, mode};
  }
  global.FusionEngine = Object.freeze({fuse, extract, seamAt, PALETTES, SIZE});
})(window);