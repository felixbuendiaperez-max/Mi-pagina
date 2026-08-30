import os
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Radar Félix
INTERVALO = 180  # revisar cada 3 minutos

MODELOS = [
    "toyota avanza",
    "toyota rav4",
    "toyota fortuner",
    "toyota prado",
    "toyota hilux",
    "toyota yaris",
    "hyundai santa fe",
    "hyundai elantra",
    "hyundai accent",
    "hyundai h-1",
    "kia sorento",
    "kia rio",
    "kia cerato",
]

DB = "vistos.db"


def iniciar_db():
    conn = sqlite3.connect(DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS vistos "
        "(url TEXT PRIMARY KEY)"
    )
    conn.commit()
    return conn


def ya_visto(conn, url):
    fila = conn.execute(
        "SELECT 1 FROM vistos WHERE url = ?", (url,)
    ).fetchone()
    return fila is not None


def guardar(conn, url):
    conn.execute(
        "INSERT OR IGNORE INTO vistos(url) VALUES (?)", (url,)
    )
    conn.commit()


def enviar_telegram(texto):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Faltan variables de Telegram")
        return

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
            "disable_web_page_preview": False,
        },
        timeout=20,
    ).raise_for_status()


def obtener_publicaciones():
    url = "https://neoauto.com/"

    respuesta = requests.get(
        url,
        headers={
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        timeout=30,
    )

    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")

    resultados = []

    for enlace in soup.find_all("a", href=True):
        texto = " ".join(enlace.stripped_strings).strip()
        href = urljoin(url, enlace["href"])

        texto_busqueda = texto.lower()

        if any(modelo in texto_busqueda for modelo in MODELOS):
            resultados.append((texto, href))

    return resultados


def ejecutar():
    conn = iniciar_db()

    print("RADAR FELIX INICIADO")

    while True:
        try:
            publicaciones = obtener_publicaciones()

            for titulo, url in publicaciones:
                if not ya_visto(conn, url):
                    mensaje = (
                        "🚨 RADAR FÉLIX\n\n"
                        f"🚗 {titulo}\n\n"
                        f"🔗 {url}"
                    )

                    enviar_telegram(mensaje)
                    guardar(conn, url)

            print(
                f"Revisión terminada: "
                f"{len(publicaciones)} coincidencias"
            )

        except Exception as error:
            print("Error:", error)

        time.sleep(INTERVALO)

ejecutar()    
