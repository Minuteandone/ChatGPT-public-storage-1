# POKÉ//SPLICE — Gen I Pokémon Fusion Lab

A static, client-side browser app that automatically fuses Pokémon from the original 151 using authentic Generation I front sprites (Red/Blue, Yellow, or Japanese Red/Green). **No backend, no API key, no AI image generation, no pre-rendered fusion database.**

## Run it

Unzip the folder and open `index.html` in a modern browser with internet access. The app downloads **only the two Pokémon sprites you pick**, directly from the publicly available [PokéAPI sprites repository](https://github.com/PokeAPI/sprites), using jsDelivr with GitHub Raw fallback. The rest of the app works locally. You can also host these files on GitHub Pages or any basic static web host (no build or server configuration needed).

> The sprite files are fetched from the internet and are **not** bundled inside this ZIP. Canvas export needs CORS-enabled hosts; the app uses cross-origin anonymous images and the sprite CDN/raw host. If opening from `file://` on a browser with unusually strict restrictions, serve the files from a local HTTP server instead (`python -m http.server 8000` from this directory, then visit `http://localhost:8000`).

## Features

- All **151** original Pokémon selectable separately for **head** and **body** — 151² = 22,801 ordered pairings (including self-fusions).
- Native Canvas 2D sprite extraction, background cleanup, automatic body/head split, silhouette-aware seam position, and neck alignment.
- Generation I Red/Blue, Yellow, and Japan Red/Green editions.
- Color remapping to Game Boy green, blue, red, sepia, or original sprite colors.
- Live head-size, splice-height, and automatic seam controls.
- Random pair, swap, download a **transparent 768×768 PNG**, browser-only recent fusion gallery, and URL sharing on hosted deployments.
- Responsive design for mobile, tablet, and desktop; all processing runs entirely within the browser.

## How fusion works

1. Decode each Pokémon sprite into the Canvas 2D API.
2. Remove transparent or flood-filled white exterior background pixels, then compute sprite bounding boxes and row-by-row silhouette centroids.
3. Find a likely neck or transition row near the chosen splice height, with an optional narrowest-usable-row heuristic.
4. Preserve the **lower half** of the body donor and the **upper half** of the head donor, scale to a common 96×96 sprite stage, and align both by their local seam centroids.
5. Optionally recolor using a four-ink palette; use nearest-neighbor rendering for sharp pixels.

This is a **procedural pixel-art compositor**, not a semantic segmentation neural network. Especially weird Pokémon (Ditto, Gastly, Voltorb, Onix, Magnemite, etc.) may have goofy cuts; that's why the adjustable head size and splice height controls exist.

## Files

- `index.html` — page markup and controls.
- `pokesplice-standalone.html` — convenient all-in-one HTML file that contains the app’s CSS and JS.
- `styles.css` — responsive lab / Pokédex-inspired visual design.
- `engine.js` — self-contained browser Canvas fusion engine.
- `app.js` — all 151 names, sprite fetching, interactions, history, link sharing, export.
- `tests/test-browser.py` — optional browser smoke test with synthetic sprites; requires Python, Pillow, and Playwright/Chromium to execute.

## Credits / rights

The application code was newly created for this project. Pokémon names, characters, and sprites belong to their respective owners. Sprites are fetched from the [PokéAPI sprites repository](https://github.com/PokeAPI/sprites). This is an unofficial fan project, not endorsed by Nintendo, Game Freak, The Pokémon Company, or PokéAPI.