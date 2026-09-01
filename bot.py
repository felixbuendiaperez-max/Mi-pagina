import os
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin

load_dotenv("/public/.env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_SECONDS = int(os.getenv("CHECK_SECONDS", "600"))
MAX_ITEMS = int(os.getenv("MAX_ITEMS_PER_SCAN", "10"))
DB_PATH = os.getenv("DB_PATH", "/public/neoauto_radar.db")

MODELOS = {
    "Toyota Avanza": "toyota-avanza",
    "Toyota RAV4": "toyota-rav4",
    "Toyota Fortuner": "toyota-fortuner",
    "Toyota Prado": "toyota-prado",
    "Toyota Hilux": "toyota-hilux",
    "Toyota Yaris": "toyota-yaris",
    "Hyundai Santa Fe": "hyundai-santa-fe",
    "Hyundai Elantra": "hyundai-elantra",
    "Hyundai Accent": "hyundai-accent",
    "Hyundai H-1": "hyundai-h-1",
    "Kia Sorento": "kia-sorento",
    "Kia Rio": "kia-rio",
    "Kia Cerato": "kia-cerato",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"
}


def conectar_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS vistos (
            url TEXT PRIMARY KEY,
            modelo TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    return db


def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": texto,
            "disable_web_page_preview": False
        },
        timeout=20
    )
    r.raise_for_status()


def obtener_anuncios(modelo, slug):
    url_busqueda = (
        f"https://neoauto.com/"
        f"venta-de-autos-usados-{slug}-en-lima"
    )

    r = requests.get(
        url_busqueda,
        headers=HEADERS,
        timeout=25
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    encontrados = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()

        if not href:
            continue

        enlace = urljoin(url_busqueda, href)

        if "neoauto.com" not in enlace:
            continue

        texto = (
            a.get_text(" ", strip=True)
            + " "
            + enlace
        ).lower()

        

    if enlace not in encontrados:
        encontrados.append(enlace)

    return encontrados


def ya_visto(db, enlace):
    fila = db.execute(
        "SELECT 1 FROM vistos WHERE url=?",
        (enlace,)
    ).fetchone()

    return fila is not None


def guardar(db, modelo, enlace):
    db.execute(
        "INSERT OR IGNORE INTO vistos(url, modelo) VALUES (?, ?)",
        (enlace, modelo)
    )
    db.commit()


def revisar():
    db = conectar_db()

    nuevos = 0

    for modelo, slug in MODELOS.items():

        print(f"Buscando: {modelo}")

        try:
            anuncios = obtener_anuncios(modelo, slug)

            print(f"  encontrados: {len(anuncios)}")

            for enlace in anuncios:

                if ya_visto(db, enlace):
                    continue

                guardar(db, modelo, enlace)

                nuevos += 1

                mensaje = (
                    "🚨 NUEVO VEHÍCULO EN NEOAUTO\n\n"
                    f"🚘 {modelo}\n\n"
                    f"🔗 {enlace}"
                )

                enviar_telegram(mensaje)

                print(f"  NUEVO: {enlace}")

                if nuevos >= MAX_ITEMS:
                    print("Límite de avisos alcanzado.")
                    db.close()
                    return

        except Exception as e:
            print(f"Error con {modelo}: {e}")

        time.sleep(2)

    db.close()

    print(f"Revisión terminada. Nuevos: {nuevos}")


def main():
    if not TOKEN or not CHAT_ID:
        print("ERROR: faltan datos de Telegram en .env")
        return

    print("=" * 45)
    print("NEOAUTO RADAR FELIX")
    print(f"Modelos vigilados: {len(MODELOS)}")
    print(f"Intervalo: {CHECK_SECONDS} segundos")
    print("=" * 45)

    enviar_telegram(
        "🟢 NeoAuto Radar Félix iniciado.\n"
        f"Vigilando {len(MODELOS)} modelos."
    )

    while True:

        try:
            revisar()

        except Exception as e:
            print("Error general:", e)

        print(
            f"Esperando {CHECK_SECONDS} segundos "
            "para la próxima revisión..."
        )

        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
