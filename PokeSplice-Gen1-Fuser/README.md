# POKÉ//SPLICE v2 — Gen I Pokémon Fusion Lab 🧬

An open, static browser app that procedurally fuses any two of the original **151 Pokémon** using actual Generation I front sprites. **No login, server, API key, machine-learning model, or pre-made fusion images.**

## Launch

Open **`pokesplice-standalone.html`** for a self-contained copy, or open **`index.html`** with the adjacent JS and CSS files. You'll need internet access to fetch the two original sprites via the [PokéAPI sprites GitHub repository](https://github.com/PokeAPI/sprites) (jsDelivr CDN, with raw GitHub fallback). After the images load, *all fusion generation happens inside your browser*.

This can be published as a static site on GitHub Pages, or run from a local server via `python -m http.server 8000`.

## What's new in v2

- **Three fusion algorithms:** `Contour` (default) computes a curved per-pixel neck boundary using silhouette centroids, `Graft` additionally retains exposed side parts of the body donor, and `Classic` keeps the v1 straight horizontal cut for comparison.
- **Mutation Explorer:** four clickable variations appear automatically for every pair. They use the same two sprites without downloading anything else.
- **Search by name or Pokédex number** for both parents, plus the full original 151-species dropdowns.
- **Fine-tuning:** adjustable head size, splice height, horizontal head shift, neck overlap, and automatic seam detection. Supports difficult combinations without manually editing the pixel art.
- **Favorites:** save up to 24 exact fusion recipes + thumbnails in browser storage, separate from the 12-item recent mutations list.
- **Shareable URL settings** cover all v2 controls and can restore an exact pair and splice recipe on a static host.
- Sprite variants from Red/Blue, Yellow, and Japanese Red/Green; optional Game Boy green, blue, red and sepia palettes.
- Pixelated transparent 768×768 PNG export, responsive layouts for phone/tablet/desktop, and a single-file version.

**Combinations:** 151 heads × 151 bodies = 22,801 directed pairings, each with more visual variants and tuning options.

## Fusion engine

All generated art uses Canvas2D nearest-neighbor sampling to retain original sprite pixels. The engine removes only the sprite's exterior white background (via flood fill when needed), crops the sprite, collects per-row silhouette pixel counts and horizontal centers, and picks a narrower cut within the user's target range. In Contour/Graft mode it applies a tapered, nonstraight alpha mask separately to the head and body pieces, aligns their necks, and optionally keeps exterior side pixels from the body sprite. No anatomical labels or AI understanding of the character is inferred: species with strange outlines can still produce some *extremely cursed* combinations.

**Privacy:** Pokémon selections and favorites stay in the browser's localStorage. The project does not phone home with your fusion choices. The two Pokémon sprite images are requested from external public hosts and require internet access.

## Source files

- `index.html` — complete accessible interface and controls.
- `styles.css` — responsive visual design.
- `engine.js` — Canvas2D procedural silhouette and fusion engine.
- `app.js` — Pokédex, image fetches, mutation explorer, save/history, sharing, PNG export.
- `pokesplice-standalone.html` — all source combined into one HTML file, no build tools.
- `tests/test-browser.py` — Playwright browser smoke test using synthetic fixture sprites (no external sprite network required).
- `tests/preview.png` and `tests/mobile-preview.png` — browser verification screenshots.

## Run tests

Requires Python 3, Pillow, Playwright, and Chromium. From this folder:

```sh
python tests/test-browser.py
```

## Rights

The application code is an unofficial fan project. Pokémon names and sprites belong to their respective owners, and the site is not affiliated with Nintendo, Game Freak, The Pokémon Company, or PokéAPI. Sprite assets are fetched live rather than redistributed in the ZIP.
