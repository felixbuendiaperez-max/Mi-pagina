import os
import time
import sqlite3
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


# =========================
# CONFIGURACION TELEGRAM
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =========================
# RADAR FELIX
# =========================

INTERVALO = 180

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


# =========================
# PAGINAS A REVISAR
# =========================

def obtener_urls_busqueda():
    configuradas = os.getenv("NEOAUTO_SEARCH_URLS", "").strip()

    if configuradas:
        texto = configuradas.replace("\n", ";").replace(",", ";")
        urls = [u.strip() for u in texto.split(";") if u.strip()]

        if urls:
            return urls

    return [
        "https://neoauto.com/venta-de-autos-usados"
    ]


URLS_BUSQUEDA = obtener_urls_busqueda()


# =========================
# BASE DE DATOS
# =========================

def iniciar_db():
    conn = sqlite3.connect("vistos.db")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vistos (
            url TEXT PRIMARY KEY
        )
        """
    )

    conn.commit()
    return conn


def ya_visto(conn, url):
    cursor = conn.execute(
        "SELECT 1 FROM vistos WHERE url = ?",
        (url,)
    )
    return cursor.fetchone() is not None


def guardar(conn, url):
    conn.execute(
        "INSERT OR IGNORE INTO vistos(url) VALUES (?)",
        (url,)
    )
    conn.commit()


# =========================
# TELEGRAM
# =========================

def enviar_telegram(mensaje):
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: falta TELEGRAM_BOT_TOKEN")
        return False

    if not TELEGRAM_CHAT_ID:
        print("ERROR: falta TELEGRAM_CHAT_ID")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    datos = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "disable_web_page_preview": False,
    }

    try:
        respuesta = requests.post(
            url,
            json=datos,
            timeout=20
        )
        respuesta.raise_for_status()
        return True

    except Exception as error:
        print("Error enviando Telegram:", error)
        return False


# =========================
# BUSCAR PUBLICACIONES
# =========================

def obtener_publicaciones():
    resultados = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/124.0 Safari/537.36"
        )
    }

    for pagina in URLS_BUSQUEDA:
        try:
            respuesta = requests.get(
                pagina,
                headers=headers,
                timeout=30
            )
            respuesta.raise_for_status()

            soup = BeautifulSoup(
                respuesta.text,
                "html.parser"
            )

            for enlace in soup.find_all("a", href=True):
                titulo = " ".join(
                    enlace.stripped_strings
                ).strip()

                url = urljoin(
                    pagina,
                    enlace.get("href")
                )

                texto_busqueda = (
                    f"{titulo} {url}"
                ).lower()

                if any(
                    modelo in texto_busqueda
                    for modelo in MODELOS
                ):
                    resultados.append(
                        (titulo or "Publicacion NeoAuto", url)
                    )

        except Exception as error:
            print(f"Error revisando {pagina}:", error)

    unicos = {}

    for titulo, url in resultados:
        unicos[url] = titulo

    return [
        (titulo, url)
        for url, titulo in unicos.items()
    ]


# =========================
# EJECUCION DEL RADAR
# =========================

def ejecutar():
    conn = iniciar_db()

    print("RADAR FELIX INICIADO")

    enviar_telegram(
        "RADAR FELIX INICIADO\n"
        "Revision automatica cada 3 minutos."
    )

    while True:
        try:
            publicaciones = obtener_publicaciones()
            nuevas = 0

            for titulo, url in publicaciones:
                if not ya_visto(conn, url):
                    mensaje = (
                        "RADAR FELIX\n\n"
                        f"{titulo}\n\n"
                        f"{url}"
                    )

                    if enviar_telegram(mensaje):
                        guardar(conn, url)
                        nuevas += 1

            print(
                "Revision terminada:",
                len(publicaciones),
                "coincidencias -",
                nuevas,
                "nuevas"
            )

        except Exception as error:
            print("Error general del radar:", error)

        time.sleep(INTERVALO)


ejecutar()
