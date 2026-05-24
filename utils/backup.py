import os
import shutil
from datetime import datetime

from utils.rutas import resource_path


CARPETA_BACKUPS = os.path.join(os.path.expanduser("~"), "ClubSigloXXI_Backups")
DB_ORIGEN       = resource_path("data/club_template.db")
MAX_BACKUPS     = 10


def hacer_backup(manual=False):
    resultado = False
    try:
        os.makedirs(CARPETA_BACKUPS, exist_ok=True)
        prefijo   = "manual" if manual else "auto"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre    = f"{prefijo}_backup_{timestamp}.db"
        destino   = os.path.join(CARPETA_BACKUPS, nombre)
        shutil.copy2(DB_ORIGEN, destino)
        if not manual:
            _limpiar_backups_automaticos()
        resultado = True
    except Exception:
        resultado = False
    return resultado


def _limpiar_backups_automaticos():
    archivos = sorted([
        f for f in os.listdir(CARPETA_BACKUPS)
        if f.startswith("auto_backup_")
    ])
    while len(archivos) > MAX_BACKUPS:
        os.remove(os.path.join(CARPETA_BACKUPS, archivos.pop(0)))


def restaurar_backup(nombre_archivo):
    resultado = False
    try:
        origen  = os.path.join(CARPETA_BACKUPS, nombre_archivo)
        shutil.copy2(origen, DB_ORIGEN)
        resultado = True
    except Exception:
        resultado = False
    return resultado


def listar_backups():
    resultado = []
    try:
        os.makedirs(CARPETA_BACKUPS, exist_ok=True)
        archivos = sorted([
            f for f in os.listdir(CARPETA_BACKUPS)
            if f.endswith(".db")
        ], reverse=True)
        resultado = archivos
    except Exception:
        resultado = []
    return resultado


def abrir_carpeta_backups():
    os.makedirs(CARPETA_BACKUPS, exist_ok=True)
    os.startfile(CARPETA_BACKUPS)


def formatear_nombre_backup(nombre):
    resultado = nombre
    try:
        partes    = nombre.replace(".db", "").split("_backup_")
        tipo      = "Manual" if partes[0] == "manual" else "Automático"
        fecha_raw = partes[1]
        fecha     = datetime.strptime(fecha_raw, "%Y%m%d_%H%M%S")
        resultado = f"{tipo} — {fecha.strftime('%d/%m/%Y %H:%M:%S')}"
    except Exception:
        resultado = nombre
    return resultado