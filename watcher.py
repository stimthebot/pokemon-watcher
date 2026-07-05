import json
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime

# =========================
# CONFIG
# =========================
STATE_FILE = "state.json"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SITES = {
    "Feenturm": "https://feenturm.de/collections/pokemon",
    "TCGViert Pokemon": "https://tcgviert.com/collections/pokemon",
    "TCGViert Vorbestellung": "https://tcgviert.com/collections/vorbestellungen/vorbestellungen",
    "Elbenwald": "https://www.elbenwald.de/pokemon/sammelkarten",
    "Tabletop Dragon": "https://www.tabletop-dragon.de/shop_de/trading-card-games/pokemon/vorbestellung.html",
    "Take-It-Shop": "https://take-it-shop.de/search?q=Pokemon"
}

# =========================
# STATE
# =========================
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# =========================
# DISCORD
# =========================
def send_discord(shop, title, url):
    if not DISCORD_WEBHOOK:
        print(f"Webhook nicht gesetzt. Produkt (wäre gesendet worden): {title}")
        return
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={
                "content": f"🆕 Neues Pokémon Produkt\n\n🏪 Shop: {shop}\n📦 Produkt: {title}\n🔗 Link: {url}\n🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            },
            timeout=10
        )
    except Exception as e:
        print("Discord Fehler:", e)

# =========================
# FETCH & CLEAN
# =========================
def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text, r.status_code
    except Exception as e:
        print(f"Fehler beim Laden von {url}: {e}")
        return "", 500

def clean(t):
    if not t:
        return ""
    return " ".join(t.split())

# =========================
# REAL PRODUCT FILTER
# =========================
def is_real_product(title, url):
    if not title:
        return False

    title = title.lower()
    url = url.lower()

    bad_keywords = [
        "login", "datenschutz", "impressum", "newsletter", "warenkorb", 
        "konto", "facebook", "instagram", "tiktok", "youtube", 
        "startseite", "versand", "agb", "faq", "kontakt", "zurück"
    ]

    if any(b in title for b in bad_keywords):
        return False

    if len(title) < 8:
        return False

    if not any(x in title for x in ["pokemon", "pokémon", "tcg", "booster", "box", "display", "tin", "deck"]):
        return False

    return True

# =========================
# PARSER
# =========================
def parse_generic(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue

        title = clean(a.get_text())
        
        if href.startswith("/"):
            url = base_url + href.split("?")[0]
        else:
            url = href.split("?")[0]

        if not is_real_product(title, url):
            continue

        products.append((title, url))

    return products

# =========================
# SHOP RUN
# =========================
def run_shop(name, url, state):
    print(f"\n[{name}] Prüfe...")
    html, status = fetch(url)
    
    if status != 200:
        print(f"Fehler: Status {status}")
        return state

    base_url = "/".join(url.split("/")[:3])
    products = parse_generic(html, base_url)
    print(f"{len(products)} potenzielle Produkte gefunden.")

    # Bestehende URLs laden, um Duplikate zu vermeiden
    known = state.get(name, [])
    known_urls = {p["url"] if isinstance(p, dict) else p for p in known}

    new_list = list(known)

    for title, url in products:
        if url not in known_urls:
            print("✨ Neues Produkt gefunden:", title)
            send_discord(name, title, url)
            
            new_list.append({
                "title": title,
                "url": url
            })
            known_urls.add(url)

    state[name] = new_list
    return state

# =========================
# MAIN (Ohne while-Schleife)
# =========================
def main():
    print("=" * 60)
    print("Pokemon Multi-Shop Watcher V5 (GitHub Actions Ready)")
    print("=" * 60)

    state = load_state()

    # Jeder Shop wird genau einmal geprüft
    for name, url in SITES.items():
        try:
            state = run_shop(name, url, state)
        except Exception as e:
            print(f"Fehler beim Prüfen von {name}: {e}")

    save_state(state)
    print("\nDurchlauf beendet. State wurde lokal aktualisiert.")

if __name__ == "__main__":
    main()
