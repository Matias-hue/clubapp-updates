#utils/updater.py

import requests
import tempfile
import subprocess
import os

from version import VERSION

GITHUB_API = "https://api.github.com/repos/Matias-hue/clubapp-updates/releases/latest"


def obtener_version_online():

    resultado = None

    try:
        response = requests.get(GITHUB_API, timeout=10)

        if response.status_code == 200:

            data = response.json()

            resultado = {
                "version": data["tag_name"].replace("v", ""),
                "download_url": data["assets"][0]["browser_download_url"]
            }

    except Exception:
        resultado = None

    return resultado


def hay_actualizacion():

    resultado = False

    online = obtener_version_online()

    if online:

        if online["version"] != VERSION:
            resultado = True

    return resultado


def descargar_actualizacion():

    resultado = False

    online = obtener_version_online()

    if online:

        try:

            url = online["download_url"]

            carpeta_temp = tempfile.gettempdir()

            ruta_instalador = os.path.join(
                carpeta_temp,
                "ClubApp_Update.exe"
            )

            response = requests.get(url, stream=True)

            with open(ruta_instalador, "wb") as archivo:

                for chunk in response.iter_content(chunk_size=8192):
                    archivo.write(chunk)

            subprocess.Popen([ruta_instalador])

            resultado = True

        except Exception:
            resultado = False

    return resultado