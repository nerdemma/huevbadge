from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright
import re
import requests

app = FastAPI(title="Huevsite Badge Generator")


def generate_shields_response(score: str):
    # Definimos colores por defecto (Gris si falla, Verde/Negro Oficial si todo está bien)
    label_color = "ccff00"  # Verde lima oficial
    color_fondo = "111111"  # Negro oficial
    
    if score in ["N/A", "Error"]:
        label_color = "lightgrey"
        color_fondo = "grey"
    
    # URL oficial unificada con el emoji del huevo 🥚 y el estilo 'for-the-badge'
    shields_url = f"https://img.shields.io/badge/🥚Score-{score}-{color_fondo}?style=for-the-badge&labelColor={label_color}&color={color_fondo}"
    
    try:
        badge_response = requests.get(shields_url)
        
        # Cabeceras anti-caché cruciales para engañar al proxy de GitHub (Camo)
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        return Response(
            content=badge_response.content, 
            media_type="image/svg+xml", 
            headers=headers
        )
    except Exception:
        fallback_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20"><text x="5" y="14" fill="red">Error Badge</text></svg>'
        return Response(content=fallback_svg, media_type="image/svg+xml")


def scraping_score(username: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        
        try:
            print(f"Conectando a huevsite.io/{username}...")
            page.goto(f"https://huevsite.io/{username}", wait_until="networkidle")
            
            print("Esperando a que termine la pantalla de carga...")
            page.wait_for_selector("text=building your huevsite…", state="detached", timeout=15000)
            page.wait_for_timeout(1000)
            body_text = page.locator("body").inner_text()
            browser.close()
    
            match = re.search(r'(?:score|impact|builder\s+score)[\s\n]*\+?(\d+)', body_text, re.IGNORECASE)
            if not match:
                match = re.search(r'(\d+)[\s\n]*(?:score|impact|builder\s+score)', body_text, re.IGNORECASE)

            return match.group(1) if match else "N/A"
            
        except Exception:
            browser.close()
            return "Error"


@app.get("/badge/{username}")
def get_badge(username: str):
    # 1. Ejecutamos el scraper
    score = scraping_score(username)
    
    # 2. Devolvemos la respuesta usando la función con cabeceras que corrigen a GitHub
    return generate_shields_response(score)