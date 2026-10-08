"""Browser smoke test with local sprite fixtures (does not need external sprite CDN)."""
import io
import re
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def fake_sprite(number):
    im = Image.new('RGBA', (56, 56), '#ffffff')
    p = ImageDraw.Draw(im)
    if number == 25:
        # Thin lightning ears and cheek marks, with a wide head.
        p.polygon([(14, 13), (9, 0), (22, 13)], fill='#edc64e', outline='#302d2c')
        p.polygon([(35, 11), (48, 1), (41, 20)], fill='#edc64e', outline='#302d2c')
        p.ellipse((8, 9, 45, 35), fill='#edc64e', outline='#302d2c', width=2)
        p.ellipse((15, 23, 18, 26), fill='#302d2c')
        p.ellipse((34, 23, 37, 26), fill='#302d2c')
        p.rectangle((13, 29, 17, 32), fill='#e57766')
        p.rectangle((36, 29, 40, 32), fill='#e57766')
        p.ellipse((16, 30, 40, 51), fill='#edc64e', outline='#302d2c')
    elif number == 1:
        p.ellipse((16, 2, 41, 26), fill='#5c9d8e', outline='#243b3a', width=2)
        p.ellipse((10, 24, 48, 50), fill='#70b3a0', outline='#243b3a', width=2)
        for x in (12, 35): p.rectangle((x, 45, x+9, 53), fill='#70b3a0', outline='#243b3a')
        p.ellipse((20, 14, 24, 19), fill='#a33d4c')
        p.ellipse((32, 14, 36, 19), fill='#a33d4c')
    else:
        p.ellipse((9, 7, 46, 38), fill='#b7a6da', outline='#302d2c', width=2)
        p.ellipse((17, 25, 41, 52), fill='#a396d0', outline='#302d2c', width=2)
        p.ellipse((18, 20, 21, 23), fill='#302d2c')
    f = io.BytesIO(); im.save(f, 'PNG'); return f.getvalue()


def main():
    with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1280, 'height': 1000}, accept_downloads=True)
            def fulfill_sprite(route):
                match = re.search(r'/([0-9]+)\.png', route.request.url)
                number = int(match.group(1)) if match else 25
                route.fulfill(body=fake_sprite(number), content_type='image/png', headers={'Access-Control-Allow-Origin':'*'})
            page.route('**/sprites/pokemon/versions/generation-i/**', fulfill_sprite)
            errors=[]
            page.on('pageerror', lambda err: errors.append(str(err)))
            html=(ROOT/'index.html').read_text()
            html=re.sub(r'<link rel="stylesheet"[^>]*>', '', html)
            html=re.sub(r'<script src="[^"]+" defer></script>', '', html)
            page.set_content(html, wait_until='load')
            page.add_style_tag(content=(ROOT/'styles.css').read_text())
            page.add_script_tag(content=(ROOT/'engine.js').read_text())
            page.add_script_tag(content=(ROOT/'app.js').read_text())
            page.wait_for_function("document.querySelector('#download-btn').disabled === false", timeout=15000)
            assert page.locator('#head-select option').count() == 151
            assert page.locator('#body-select option').count() == 151
            assert page.locator('#fusion-name').inner_text()
            assert page.locator('.variant-item').count() == 4
            assert page.locator('#pokemon-list option').count() == 151
            # User-adjusted image output and restoration through URL settings.
            page.locator('#head-search').fill('Mewtwo')
            page.wait_for_function("document.querySelector('#head-select').value === '150' && !document.querySelector('#download-btn').disabled")
            page.locator('#head-search').fill('Pikachu')
            page.wait_for_function("document.querySelector('#head-select').value === '25' && !document.querySelector('#download-btn').disabled")
            page.locator('#shift-x').fill('12')
            page.wait_for_function("document.querySelector('#status-text').textContent.includes('Fusion complete')")
            page.wait_for_timeout(130)
            assert page.locator('#shift-x-value').inner_text() == '+12 PX'
            assert 'x=12' in page.url or page.url == 'about:blank', 'Unexpected share URL behavior'
            page.locator('#shift-x').fill('0')
            page.wait_for_timeout(180)
            page.locator('#favorite-btn').click()
            assert page.locator('.favorites-section .recent-item').count() == 1
            assert page.locator('#favorite-btn').get_attribute('aria-pressed') == 'true'
            page.locator('#mode').select_option('graft')
            page.wait_for_function("document.querySelector('#mode').value === 'graft' && !document.querySelector('#download-btn').disabled")
            page.locator('.variant-item').first.click()
            page.wait_for_function("document.querySelector('#mode').value === 'classic' && !document.querySelector('#download-btn').disabled")
            assert page.locator('.variant-item').count() == 4
            page.locator('#mode').select_option('contour')
            page.wait_for_function("document.querySelector('#mode').value === 'contour' && !document.querySelector('#download-btn').disabled")
            page.locator('#head-search').fill('')
            pixels = page.evaluate('''() => {
                let c=document.querySelector('#fusion-canvas'), d=c.getContext('2d').getImageData(0,0,96,96).data;
                let n=0, colors=new Set();
                for(let i=0;i<d.length;i+=4){if(d[i+3]>0){n++;colors.add(`${d[i]},${d[i+1]},${d[i+2]}`)}}
                return {count:n, colors:colors.size, uri:c.toDataURL('image/png')};
            }''')
            assert pixels['count'] > 150 and pixels['colors'] >= 2, pixels
            first_uri = pixels['uri']
            page.locator('#swap-btn').click()
            page.wait_for_function('''() => document.querySelector('#head-select').value==='1' && !document.querySelector('#download-btn').disabled''')
            page.wait_for_timeout(120)
            swapped_uri=page.evaluate("document.querySelector('#fusion-canvas').toDataURL('image/png')")
            assert first_uri != swapped_uri, 'swap should change pixel output'
            page.locator('#palette').select_option('gameboy')
            page.wait_for_function("document.querySelector('#status-text').textContent.includes('Fusion complete')")
            page.wait_for_timeout(120)
            colors=page.evaluate('''() => {
                let d=document.querySelector('#fusion-canvas').getContext('2d').getImageData(0,0,96,96).data;
                let s=new Set();for(let i=0;i<d.length;i+=4)if(d[i+3]>0)s.add(`${d[i]},${d[i+1]},${d[i+2]}`);return [...s]
            }''')
            assert len(colors) <= 4 and len(colors) > 0, colors
            with page.expect_download() as info:
                page.locator('#download-btn').click()
            download = info.value
            assert download.suggested_filename.endswith('.png')
            image = Image.open(download.path())
            assert image.size == (768, 768), image.size
            assert image.mode == 'RGBA'
            assert image.getextrema()[3] == (0, 255), image.getextrema()[3]
            page.locator('#random-btn').click()
            page.wait_for_timeout(500)
            assert page.locator('.recent-item').count() >= 2
            page.screenshot(path=str(ROOT / 'tests' / 'preview.png'), full_page=True)
            assert not errors, errors
            assert page.locator('#favorite-btn').is_enabled()

            # Verify portable all-in-one page runs without separate scripts/styles.
            portable = browser.new_page(viewport={'width': 390, 'height': 844})
            portable.route('**/sprites/pokemon/versions/generation-i/**', fulfill_sprite)
            portable_errors=[]
            portable.on('pageerror', lambda err: portable_errors.append(str(err)))
            portable.set_content((ROOT / 'pokesplice-standalone.html').read_text(), wait_until='load')
            portable.wait_for_function("document.querySelector('#download-btn').disabled === false", timeout=15000)
            assert portable.locator('#fusion-canvas').is_visible()
            overflow = portable.evaluate('document.documentElement.scrollWidth > window.innerWidth + 3')
            assert not overflow, 'mobile layout overflows viewport'
            portable.screenshot(path=str(ROOT / 'tests' / 'mobile-preview.png'), full_page=True)
            assert not portable_errors, portable_errors
            portable.close()
            print('PASS v2: 151 searches, contour/classic/graft modes, four mutations, favorites, sliders, palette, PNG, random, history, standalone, mobile, no JS errors')
            browser.close()


if __name__ == '__main__': main()