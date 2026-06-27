from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright
import re
import requests
import time

app = FastAPI(title="Huevsite Badge Generator")

# Diccionario en memoria para guardar los resultados y evitar la lentitud de Playwright
# Estructura: { "username": {"svg": b"...", "timestamp": 12345678} }
CACHE_MEMORIA = {}
CACHE_EXPIRACION_SEGUNDOS = 300  # 5 minutos


def build_svg_response(content: bytes) -> Response:
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return Response(
        content=content,
        media_type="image/svg+xml",
        headers=headers,
    )


def generate_shields_response(score: str):
    label_color = "ccff00"
    color_fondo = "111111"
    
    if score in ["N/A", "Error"]:
        label_color = "lightgrey"
        color_fondo = "grey"
        
    shields_url = f"https://img.shields.io/badge/HuevScore-{score}-{color_fondo}?style=for-the-badge&labelColor={label_color}&color={color_fondo}"
    
    try:
        badge_response = requests.get(shields_url)
        return badge_response.content
    except Exception:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20"><text x="5" y="14" fill="red">Error Badge</text></svg>'.encode('utf-8')


def scraping_score(username: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        
        try:
            print(f"Scraping en tiempo real para: {username}...")
            page.goto(f"https://huevsite.io/{username}", wait_until="networkidle")
            page.wait_for_selector("text=building your huevsite…", state="detached", timeout=10000)
            page.wait_for_timeout(500)
            body_text = page.locator("body").inner_text()
            browser.close()
    
            match = re.search(r'(?:score|impact|builder\s+score)[\s\n]*\+?(\d+)', body_text, re.IGNORECASE)
            if not match:
                match = re.search(r'(\d+)[\s\n]*(?:score|impact|builder\s+score)', body_text, re.IGNORECASE)

            return match.group(1) if match else "N/A"
            
        except Exception as e:
            print(f"Error en Playwright: {e}")
            try:
                browser.close()
            except:
                pass
            return "Error"


@app.get("/badge/{username}")
def get_badge(username: str):
    username_lower = username.lower()
    ahora = time.time()
    
    # Si el badge está en caché y no ha expirado, lo devolvemos al instante (GitHub AMA ESTO)
    if username_lower in CACHE_MEMORIA:
        datos_cache = CACHE_MEMORIA[username_lower]
        if ahora - datos_cache["timestamp"] < CACHE_EXPIRACION_SEGUNDOS:
            print(f"¡Caché Hit! Entregando badge instantáneo para {username_lower}")
            return build_svg_response(datos_cache["svg"])
            
    # Si no está en caché o ya expiró, hacemos el proceso lento una sola vez
    score = scraping_score(username_lower)
    svg_content = generate_shields_response(score)
    
    # Guardamos en la caché de memoria
    CACHE_MEMORIA[username_lower] = {
        "svg": svg_content,
        "timestamp": ahora
    }
    
    return build_svg_response(svg_content)
